"""One translation workflow used by the CLI, MCP and settings page."""

import re
from dataclasses import replace

from twintext.cache import Cache
from twintext.config import LANGUAGES, TwinTextError, load_settings
from twintext.engine import ArgosEngine, detect_language
from twintext.markdown import blocks, prose, translate_block

MAX_TEXT_LENGTH = 100_000


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

        for block in blocks(text):
            value = (
                translate_block(block.original, translate_fragment)
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
    settings = load_settings()
    if not settings.enabled or settings.mode == "original":
        return ""
    target = LANGUAGES[settings.target]
    presentation = (
        "each prose paragraph followed by its translation"
        if settings.mode == "bilingual"
        else "only the translated prose"
    )
    return (
        f"TwinText is enabled for this chat. Its target language is {target} "
        f"({settings.target}) and its mode is {settings.mode}. "
        "For new final replies, compose your normal complete reply, then pass that Markdown "
        "to the local TwinText translate tool before sending the final answer. "
        f"Present the returned display verbatim: {presentation}. "
        "If TwinText MCP tools are unavailable, run the installed `twintext translate` CLI "
        "with the reply passed on stdin (do not put reply text into shell arguments). "
        "Keep short progress updates in the target language. "
        "If source and target are the same, show the reply once. "
        "Code, commands, paths and link targets must remain unchanged. "
        "If the tool fails, show the original reply and briefly explain the translation failure; "
        "do not substitute a cloud engine or claim the text was translated. "
        "These preferences affect new replies and do not alter existing messages or Codex menus. "
        "An explicit language or display request from the user takes precedence."
    )
