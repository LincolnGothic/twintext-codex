"""One translation workflow used by the CLI, MCP and settings page."""

import re
from dataclasses import replace

from twintext.cache import Cache
from twintext.config import LANGUAGES, TwinTextError, load_settings
from twintext.engine import ArgosEngine, detect_language
from twintext.markdown import blocks, prose, reference_ids, translate_block

MAX_TEXT_LENGTH = 100_000
QUANTITY_HEADER = {"en": "Quantity", "zh": "数量", "ja": "数量", "fr": "Quantité", "es": "Cantidad"}


class Service:
    def __init__(self, engine=None, detector=None):
        self.engine = engine if engine is not None else ArgosEngine()
        self.detector = detector or detect_language

    def translate(self, text, source=None, target=None, mode=None):
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
        source = settings.source
        pairs = []
        translated = []
        rendered = []
        cache_hits = 0
        route = []
        if text.strip() and settings.mode != "original":
            content = prose(text)
            if re.search(r"[^\W\d_]", content, re.UNICODE):
                source = self.detector(content) if source == "auto" else source
                if source not in LANGUAGES:
                    raise TwinTextError(
                        "Detected language is unsupported. Choose a source language."
                    )
                if source != settings.target:
                    route = [p.to_code for p in self.engine.route(source, settings.target)]
        needs_translation = bool(route)
        fingerprint = self.engine.fingerprint(source, settings.target) if needs_translation else ""
        cache = Cache() if settings.cache and needs_translation else None

        def translate_fragment(fragment):
            nonlocal cache_hits
            key = Cache.key(fragment, source, settings.target, fingerprint)
            value = cache.get(key) if cache else None
            if value is not None:
                cache_hits += 1
                return value
            value = self.engine.translate(fragment, source, settings.target)
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
        try:
            routes = self.engine.routes()
            error = None
        except (TwinTextError, OSError) as exc:
            routes = []
            error = str(exc)
        return {
            "settings": load_settings().as_dict(),
            "languages": LANGUAGES,
            "installed_models": routes,
            "engine_error": error,
            "engine": "Argos Translate / CTranslate2 CPU",
            "offline": True,
        }


def context():
    # Compatibility with v0.1 launchers; automatic translation now uses Stop + desktop.
    return ""
