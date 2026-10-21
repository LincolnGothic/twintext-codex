"""One translation workflow used by the CLI, MCP and settings page."""

import re
import threading
from dataclasses import replace

from twintext import providers
from twintext.cache import Cache
from twintext.config import TRANSLATION_LANGUAGES, TwinTextError, load_settings
from twintext.engine import detect_language
from twintext.markdown import blocks, prose, reference_ids, translate_block
from twintext.usage import CloudUsage, usage_label

MAX_TEXT_LENGTH = 100_000
QUANTITY_HEADER = {"en": "Quantity", "zh": "数量", "zh-TW": "數量", "ja": "数量",
                   "fr": "Quantité", "es": "Cantidad"}


class Service:
    def __init__(self, engine=None, detector=None):
        self._injected_engine = engine
        self._engine = None
        self._provider = None
        self._engine_lock = threading.RLock()
        self.detector = detector or detect_language

    @property
    def engine(self):
        return self.engine_for(load_settings().provider)

    def engine_for(self, provider):
        if self._injected_engine is not None:
            return self._injected_engine
        with self._engine_lock:
            if self._provider != provider:
                self._engine = providers.create_engine(provider)
                self._provider = provider
            return self._engine

    def translate(self, text, source=None, target=None, mode=None, cancel=None):
        def check_cancel():
            if cancel is not None and cancel.is_set():
                raise TwinTextError("Translation cancelled.")

        check_cancel()
        if not isinstance(text, str):
            raise TwinTextError("Text must be a string.")
        if len(text) > MAX_TEXT_LENGTH:
            raise TwinTextError("Translate at most 100,000 characters at a time.")
        settings = load_settings()
        overrides = {
            k: v
            for k, v in {"source": source, "target": target, "mode": mode}.items()
            if v is not None
        }
        settings = replace(settings, **overrides).validate()
        engine = self.engine_for(settings.provider)
        source = settings.source
        pairs = []
        translated = []
        rendered = []
        cache_hits = 0
        route = []
        if text.strip() and settings.mode != "original":
            content = prose(text)
            if re.search(r"[^\W\d_]", content, re.UNICODE):
                if source == "auto" and settings.provider != "google-free":
                    source = self.detector(content)
                if source not in TRANSLATION_LANGUAGES and not (
                    source == "auto" and settings.provider == "google-free"
                ):
                    raise TwinTextError(
                        "Detected language is unsupported. Choose a source language."
                    )
                if source != settings.target:
                    route = [p.to_code for p in engine.route(source, settings.target)]
        needs_translation = bool(route)
        fingerprint = (
            settings.provider + ":" + engine.fingerprint(source, settings.target)
            if needs_translation else ""
        )
        cache = (Cache(memory=settings.cache_lifetime == "session")
                 if settings.cache and needs_translation else None)

        def translate_fragment(fragment):
            nonlocal cache_hits
            check_cancel()
            key = Cache.key(fragment, source, settings.target, fingerprint)
            value = cache.get(key) if cache else None
            if value is not None:
                cache_hits += 1
                return value
            value = (
                engine.translate(fragment, source, settings.target, cancel=cancel)
                if cancel is not None and getattr(engine, "provider", "offline") != "offline"
                else engine.translate(fragment, source, settings.target)
            )
            check_cancel()
            if not isinstance(value, str) or not value.strip():
                raise TwinTextError("The local model returned an empty translation.")
            if cache:
                cache.put(key, value)
            return value

        def translate_header(fragment):
            # This very short field is ambiguous to the local model (e.g. it
            # returned “termination reason” for English Quantity → Chinese).
            # Apply the glossary only to table headers, never to ordinary prose.
            if fragment.casefold() == QUANTITY_HEADER.get(source, "").casefold():
                return QUANTITY_HEADER[settings.target]
            return translate_fragment(fragment)

        references = reference_ids(text)
        for block in blocks(text):
            check_cancel()
            value = (
                translate_block(
                    block.original, translate_fragment, block.kind, references, translate_header
                )
                if needs_translation and block.translatable
                else block.original
            )
            translated.append(value)
            pairs.append(
                {
                    "original": block.original,
                    "translation": value,
                    "protected": not block.translatable,
                }
            )
            if settings.mode == "bilingual" and value != block.original:
                rendered.append(block.original.rstrip("\n") + "\n\n" + value)
            else:
                rendered.append(value)
        return {
            "source": source,
            "target": settings.target,
            "mode": settings.mode,
            "original": text,
            "translation": "".join(translated),
            "display": "".join(rendered),
            "blocks": pairs,
            "route": [source, *route] if route else [source],
            "cache_hits": cache_hits,
        }

    def status(self):
        settings = load_settings()
        try:
            routes = self.engine_for(settings.provider).routes()
            error = None
        except (TwinTextError, OSError) as exc:
            routes = []
            error = str(exc)
        configured = False
        if settings.provider == "azure":
            try:
                configured = bool(providers.load_credentials().get("key"))
                if not configured:
                    error = "Configure your Azure credentials with twintext azure-configure."
            except TwinTextError as exc:
                error = str(exc)
        usage = CloudUsage().snapshot()
        return {
            "settings": settings.as_dict(),
            "languages": TRANSLATION_LANGUAGES,
            "installed_models": routes,
            "engine_error": error,
            "provider": settings.provider,
            "engine": ("Argos Translate / CTranslate2 CPU" if settings.provider == "offline"
                       else "Google Free (experimental)" if settings.provider == "google-free"
                       else "Microsoft Azure Translator REST v3"),
            "offline": settings.provider == "offline",
            "azure_configured": configured,
            "cloud_usage": usage,
            "cloud_usage_label": usage_label(usage),
        }


def context(session_id=None, turn_id=None):
    return (
        "TwinText uses manual per-message translation buttons and a separate reader. "
        "Keep assistant messages in their original language. Do not call TwinText "
        "translation or forwarding tools for ordinary replies, progress or questions. "
        "The user clicks a message button to translate it outside model context. "
        "Explicit translation requests take precedence."
    )
