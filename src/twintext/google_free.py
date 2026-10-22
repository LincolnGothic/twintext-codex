"""Experimental, keyless Google transport, not the Google Cloud Translation API."""

import json
import math
import re
import secrets
import ssl
import threading
import time
from datetime import timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

from twintext.config import TwinTextError, data_dir, private_dir
from twintext.locking import acquire_lock

ENDPOINT = "https://translate.googleapis.com/translate_a/single"
LANGUAGES = {"auto": "auto", "en": "en", "zh": "zh-CN", "zh-CN": "zh-CN",
             "zh-Hans": "zh-CN", "zh-TW": "zh-TW", "zh-Hant": "zh-TW",
             "ja": "ja", "fr": "fr", "es": "es"}
# Conservative local URL budget (including percent encoding), not a Google quota.
MAX_URL_LENGTH = 1800
MAX_BATCH_FRAGMENTS = 32


def pack_fragments(texts, nonce):
    markers = [f"__TT{nonce}_{index}__" for index in range(len(texts) + 1)]
    value = "\n".join(part for pair in zip(markers[:-1], texts, strict=True) for part in pair)
    return value + "\n" + markers[-1], markers


def unpack_fragments(value, markers):
    """Reject changed, missing, repeated or reordered boundaries before mapping text."""
    value = value.strip()
    pattern = re.compile(r"__TT" + re.escape(markers[0][4:].split("_")[0]) + r"_\d+__")
    matches = list(pattern.finditer(value))
    if ([match[0] for match in matches] != markers or not matches
            or matches[0].start() != 0 or matches[-1].end() != len(value)):
        return None
    output = [value[left.end():right.start()].strip()
              for left, right in zip(matches[:-1], matches[1:], strict=True)]
    return output if all(output) else None


def google_language(code):
    try:
        return LANGUAGES[code]
    except KeyError:
        raise TwinTextError("Google Free does not support this language.") from None


def google_url(text, source, target):
    return ENDPOINT + "?" + urlencode({
        "client": "gtx", "sl": google_language(source), "tl": google_language(target),
        "dt": "t", "q": text,
    })


def google_chunks(text, source, target):
    while text:
        low, high = 1, min(len(text), MAX_URL_LENGTH)
        while low <= high:
            middle = (low + high) // 2
            if len(google_url(text[:middle], source, target)) <= MAX_URL_LENGTH:
                low = middle + 1
            else:
                high = middle - 1
        cut = high
        if cut < len(text):
            boundaries = list(re.finditer(r"\s+|[。！？.!?]", text[cut // 2:cut]))
            if boundaries:
                cut = cut // 2 + boundaries[-1].end()
        yield text[:cut]
        text = text[cut:]


def parse_google_response(raw):
    try:
        if len(raw) > 2_000_000:
            raise ValueError
        result = json.loads(raw)
        if not isinstance(result, list) or not result or not isinstance(result[0], list):
            raise ValueError
        segments = result[0]
        if not segments or any(not isinstance(row, list) or not row
                               or not isinstance(row[0], str) for row in segments):
            raise ValueError
        value = "".join(row[0] for row in segments)
        if not value.strip():
            raise ValueError
        return value
    except (ValueError, TypeError, UnicodeError):
        raise TwinTextError(
            "Google Free returned an invalid or empty response. Retry later."
        ) from None


def retry_after(value):
    try:
        delay = float(value)
    except (ValueError, TypeError):
        try:
            date = parsedate_to_datetime(value)
            delay = date.replace(tzinfo=date.tzinfo or timezone.utc).timestamp() - time.time()
        except (ValueError, TypeError, OverflowError):
            return 0
    return max(0, delay) if math.isfinite(delay) else 0


class GoogleFreeEngine:
    provider = "google-free"

    def __init__(self, opener=None, timeout=15):
        from twintext.google_transport import GoogleTransport

        self.transport = None if opener is not None else GoogleTransport()
        self.opener = opener if opener is not None else self.transport.open
        self.timeout = timeout
        self.batching = True

    def close(self):
        if self.transport is not None:
            self.transport.close()

    def iter_translations(self, texts, source, target, cancel=None):
        """Yield indexed, complete fragments after each bounded request batch."""
        cancel = cancel or threading.Event()
        self.check_cancel(cancel)
        nonce = secrets.token_hex(6)
        while any(nonce in text for text in texts):
            nonce = secrets.token_hex(6)
        batches, batch = [], []
        for index, text in enumerate(texts):
            candidate = [value for _, value in batch] + [text]
            packed, _ = pack_fragments(candidate, nonce)
            if batch and (len(candidate) > MAX_BATCH_FRAGMENTS
                          or len(google_url(packed, source, target)) > MAX_URL_LENGTH):
                batches.append(batch)
                batch = []
            batch.append((index, text))
        if batch:
            batches.append(batch)
        for batch in batches:
            self.check_cancel(cancel)
            values = None
            if self.batching and len(batch) > 1:
                packed, markers = pack_fragments([text for _, text in batch], nonce)
                values = unpack_fragments(self.translate(packed, source, target, cancel), markers)
                if values is None:
                    self.batching = False  # Avoid repeated failed batch probes this run.
            if values is None:
                for index, text in batch:
                    yield index, self.translate(text, source, target, cancel)
            else:
                for (index, text), value in zip(batch, values, strict=True):
                    self.check_cancel(cancel)
                    leading = text[:len(text) - len(text.lstrip())]
                    trailing = text[len(text.rstrip()):]
                    yield index, leading + value + trailing

    def route(self, source, target):
        source, target_code = google_language(source), google_language(target)
        if target_code == "auto":
            raise TwinTextError("Choose a target language for Google Free.")
        return [SimpleNamespace(to_code=target)] if source != target_code else []

    def routes(self):
        return []

    def fingerprint(self, source, target):
        return f"google-free-gtx-v1:{google_language(source)}:{google_language(target)}"

    @staticmethod
    def check_cancel(cancel):
        if cancel.is_set():
            raise TwinTextError("Google Free translation cancelled.")

    @staticmethod
    def pause(seconds, cancel):
        if cancel.wait(seconds):
            raise TwinTextError("Google Free translation cancelled.")

    def translate(self, text, source, target, cancel=None):
        cancel = cancel or threading.Event()
        self.check_cancel(cancel)
        if not text.strip() or not self.route(source, target):
            return text
        # Reuse the existing OS lock across Desktop, MCP and local web processes.
        path = private_dir(data_dir() / "google-free") / "request.lock"
        lock = None
        try:
            while lock is None:
                self.check_cancel(cancel)
                lock = acquire_lock(path, blocking=False)
                if lock is None:
                    cancel.wait(0.05)
            output = []
            for chunk in google_chunks(text, source, target):
                self.check_cancel(cancel)
                if not chunk.strip():
                    output.append(chunk)
                    continue
                leading = chunk[:len(chunk) - len(chunk.lstrip())]
                trailing = chunk[len(chunk.rstrip()):]
                value = self.request(chunk, source, target, cancel)
                output.append(leading + value.strip() + trailing)
            return "".join(output)
        finally:
            if lock is not None:
                lock.close()

    def request(self, text, source, target, cancel):
        request = Request(google_url(text, source, target), method="GET")
        for attempt in range(3):
            self.check_cancel(cancel)
            delay = 0
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    raw = response.read(2_000_001)
                self.check_cancel(cancel)
                return parse_google_response(raw)
            except HTTPError as exc:
                code = exc.code
                delay = retry_after(exc.headers.get("Retry-After")) if exc.headers else 0
                exc.close()
                recoverable = code in (429, 500, 502, 503, 504)
                message = ("Google Free rate limit reached. Retry later." if code == 429 else
                           "Google Free is unavailable. Retry later." if recoverable else
                           "Google Free rejected the request or access. "
                           "Check languages; retry later.")
            except (TimeoutError, URLError, OSError, HTTPException) as exc:
                reason = exc.reason if isinstance(exc, URLError) else exc
                recoverable = not isinstance(reason, ssl.SSLCertVerificationError)
                message = ("Google Free translation timed out. Retry later."
                           if isinstance(reason, TimeoutError) else
                           "Google Free network request failed. Check your connection.")
            if not recoverable or attempt == 2:
                raise TwinTextError(message) from None
            self.pause(max(2 ** attempt, delay), cancel)
