"""One translation workflow used by the CLI, MCP and settings page."""

import re
import threading
import time
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

    def translate(self, text, source=None, target=None, mode=None, cancel=None, progress=None):
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

        source_blocks = blocks(text)
        dependencies = []
        keys, values = {}, {}
        cached = set()
        pending = []

        def collect(fragment):
            nonlocal cache_hits
            check_cancel()
            if fragment not in keys:
                key = Cache.key(fragment, source, settings.target, fingerprint)
                keys[fragment] = key
                value = cache.get(key) if cache else None
                if value is not None:
                    values[fragment] = value
                    cached.add(fragment)
                else:
                    pending.append(fragment)
            if fragment in cached:
                cache_hits += 1
            dependencies[-1].add(fragment)
            return fragment

        def header(fragment, translate):
            if fragment.casefold() == QUANTITY_HEADER.get(source, "").casefold():
                return QUANTITY_HEADER[settings.target]
            return translate(fragment)

        references = reference_ids(text)
        # Collect exactly the spans used by the existing Markdown renderer. Opaque
        # code, destinations, paths, numbers and structural tokens never enter a batch.
        for block in source_blocks:
            dependencies.append(set())
            if needs_translation and block.translatable:
                translate_block(block.original, collect, block.kind, references,
                                lambda fragment: header(fragment, collect))

        cursor = completed = 0
        last_preview = None
        total = sum(len(block.original) for block in source_blocks if block.translatable)

        def result(complete):
            remaining = source_blocks[cursor:]
            tail = "".join(block.original for block in remaining)
            return {
                "source": source, "target": settings.target, "mode": settings.mode,
                "original": text, "translation": "".join(translated) + tail,
                "display": "".join(rendered) + tail,
                "blocks": pairs + [{"original": block.original, "translation": block.original,
                                     "protected": not block.translatable} for block in remaining],
                "route": [source, *route] if route else [source], "cache_hits": cache_hits,
                "complete": complete,
                "progress": {"completed": completed, "total": total},
            }

        def render_ready():
            nonlocal cursor, completed, last_preview
            previous = cursor
            while cursor < len(source_blocks) and dependencies[cursor].issubset(values):
                check_cancel()
                block = source_blocks[cursor]
                value = (translate_block(
                    block.original, values.__getitem__, block.kind, references,
                    lambda fragment: header(fragment, values.__getitem__),
                ) if needs_translation and block.translatable else block.original)
                translated.append(value)
                pairs.append({"original": block.original, "translation": value,
                              "protected": not block.translatable})
                rendered.append(
                    block.original.rstrip("\n") + "\n\n" + value
                    if settings.mode == "bilingual" and value != block.original else value)
                completed += len(block.original) if block.translatable else 0
                cursor += 1
            if (progress is not None and completed and cursor != previous
                    and cursor < len(source_blocks)
                    and (last_preview is None or time.monotonic() - last_preview >= 0.1)):
                check_cancel()
                last_preview = time.monotonic()
                progress(result(False))

        def sequential():
            for index, fragment in enumerate(pending):
                check_cancel()
                value = (engine.translate(fragment, source, settings.target, cancel=cancel)
                         if cancel is not None
                         and getattr(engine, "provider", "offline") != "offline"
                         else engine.translate(fragment, source, settings.target))
                yield index, value

        render_ready()
        iterator = getattr(engine, "iter_translations", None)
        updates = (iterator(pending, source, settings.target, cancel=cancel)
                   if pending and iterator is not None else sequential())
        seen = set()
        for index, value in updates:
            check_cancel()
            if (type(index) is not int or not 0 <= index < len(pending) or index in seen
                    or not isinstance(value, str) or not value.strip()):
                raise TwinTextError("The translation provider returned an invalid fragment.")
            seen.add(index)
            fragment = pending[index]
            values[fragment] = value
            if cache:
                cache.put(keys[fragment], value)
            render_ready()
        check_cancel()
        if cursor != len(source_blocks):
            raise TwinTextError("The translation provider returned an incomplete result.")
        return result(True)

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
