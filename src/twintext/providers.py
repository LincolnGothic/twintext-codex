"""Translation engines share route/fingerprint/translate; providers own transport."""

import json
from http.client import HTTPException
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from twintext.config import TwinTextError
from twintext.credentials import load_credentials
from twintext.engine import ArgosEngine
from twintext.usage import CloudUsage

AZURE_LANGUAGES = {"en": "en", "zh": "zh-Hans", "ja": "ja", "fr": "fr", "es": "es"}
AZURE_ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate"


def azure_language(code):
    try:
        return AZURE_LANGUAGES[code]
    except KeyError:
        raise TwinTextError(
            "Azure does not support this language. Choose a supported language."
        ) from None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward subscription headers to another endpoint.


def azure_chunks(text, maximum=45000):
    while len(text) > maximum:
        cut = text.rfind(" ", maximum // 2, maximum + 1)
        if cut < 0:
            cut = maximum
        yield text[:cut]
        text = text[cut:]
    if text:
        yield text


class AzureEngine:
    provider = "azure"

    def __init__(self, opener=None, credentials=None, usage=None, timeout=15):
        self.opener = opener or build_opener(NoRedirect()).open
        self.credentials = credentials or load_credentials
        self.usage = usage or CloudUsage()
        self.timeout = timeout

    def route(self, source, target):
        azure_language(source)
        azure_language(target)
        return [SimpleNamespace(to_code=target)] if source != target else []

    def routes(self):
        return []  # No local models or downloads required.

    def fingerprint(self, source, target):
        return f"azure-rest-v3:{azure_language(source)}:{azure_language(target)}"

    def translate(self, text, source, target, cancel=None):
        source_code, target_code = azure_language(source), azure_language(target)
        if cancel is not None and cancel.is_set():
            raise TwinTextError("Azure translation cancelled.")
        if source == target:
            return text
        credentials = self.credentials()
        key, region = credentials.get("key", ""), credentials.get("region", "")
        if not key:
            raise TwinTextError("Configure your Azure credentials with twintext azure-configure.")
        if not text.strip():
            raise TwinTextError("Azure needs non-empty source text.")
        if len(text) > 45000:
            return " ".join(
                self.translate(chunk, source, target, cancel)
                for chunk in azure_chunks(text)
            )
        query = urlencode({"api-version": "3.0", "from": source_code, "to": target_code})
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Ocp-Apim-Subscription-Key": key,
        }
        if region:
            headers["Ocp-Apim-Subscription-Region"] = region
        request = Request(
            AZURE_ENDPOINT + "?" + query,
            data=json.dumps([{"Text": text}], ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            self.usage.record(len(text))
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
        except HTTPError as exc:
            code = exc.code
            exc.close()
            messages = {
                400: ("Azure rejected the language combination or text. "
                      "Check source and target languages."),
                401: "Azure authentication failed. Check your credentials and resource region.",
                403: "Azure access denied. Check credentials, region and resource quota.",
                408: "Azure translation timed out. Try shorter text or retry later.",
                429: "Azure quota or rate limit reached. Check your quota and retry later.",
            }
            message = (
                "Azure redirect refused. Check the Translator endpoint."
                if 300 <= code < 400
                else messages.get(
                    code, "Azure is unavailable. Retry later and check the service status."
                )
            )
            raise TwinTextError(message) from None
        except TimeoutError:
            raise TwinTextError(
                "Azure translation timed out. Try shorter text or retry later."
            ) from None
        except URLError as exc:
            message = ("Azure translation timed out. Try shorter text or retry later."
                       if isinstance(exc.reason, TimeoutError)
                       else "Azure network request failed. Check your connection and credentials.")
            raise TwinTextError(message) from None
        except (OSError, ValueError, HTTPException):
            raise TwinTextError(
                "Azure network request failed. Check your connection and credentials."
            ) from None
        if cancel is not None and cancel.is_set():
            raise TwinTextError("Azure translation cancelled.")
        return parse_azure_response(raw, target_code)


def parse_azure_response(raw, target):
    try:
        if len(raw) > 2_000_000:
            raise ValueError
        result = json.loads(raw)
        if not isinstance(result, list):
            raise ValueError
        if not result:
            raise TwinTextError("Azure returned an empty translation. Try different text.")
        if len(result) != 1 or not isinstance(result[0], dict):
            raise ValueError
        translations = result[0]["translations"]
        if not isinstance(translations, list):
            raise ValueError
        if not translations:
            raise TwinTextError("Azure returned an empty translation. Try different text.")
        if len(translations) != 1 or not isinstance(translations[0], dict):
            raise ValueError
        value = translations[0]["text"]
        if not isinstance(value, str) or translations[0].get("to", target) != target:
            raise ValueError
        if not value.strip():
            raise TwinTextError("Azure returned an empty translation. Try different text.")
        return value.strip()
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise TwinTextError("Azure returned an invalid response. Retry later.") from None


PROVIDERS = {"offline": ArgosEngine, "azure": AzureEngine}


def create_engine(provider):
    return PROVIDERS[provider]()
