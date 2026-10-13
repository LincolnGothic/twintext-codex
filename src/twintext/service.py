"""One translation workflow used by the CLI, MCP and settings page."""

import re
import threading
from dataclasses import replace

from twintext import providers
from twintext.cache import Cache
from twintext.config import LANGUAGES, TwinTextError, load_settings
from twintext.engine import detect_language
from twintext.markdown import blocks, prose, reference_ids, translate_block
from twintext.usage import CloudUsage, usage_label

MAX_TEXT_LENGTH = 100_000
QUANTITY_HEADER = {"en": "Quantity", "zh": "数量", "ja": "数量", "fr": "Quantité", "es": "Cantidad"}


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
                source = self.detector(content) if source == "auto" else source
                if source not in LANGUAGES:
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
        cache = Cache() if settings.cache and needs_translation else None

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
            "languages": LANGUAGES,
            "installed_models": routes,
            "engine_error": error,
            "provider": settings.provider,
            "engine": ("Argos Translate / CTranslate2 CPU" if settings.provider == "offline"
                       else "Microsoft Azure Translator REST v3"),
            "offline": settings.provider == "offline",
            "azure_configured": configured,
            "cloud_usage": usage,
            "cloud_usage_label": usage_label(usage),
        }


def context():
    settings = load_settings()
    if settings.workflow != "chat":
        return ""
    if not settings.enabled or settings.mode == "original":
        return (
            "TwinText Chat translation is paused. Stop applying earlier TwinText translation "
            "instructions; present new replies normally. Explicit user requests take precedence."
        )
    responses = (
        "Translate informational final answers. Leave progress updates untranslated. "
        if settings.response_scope == "final"
        else "Translate progress updates and final answers. "
    )
    questions = (
        "Translate user-directed questions in conversation and question cards, even before "
        "the final answer. Before calling request_user_input or request_user_input_async, "
        "use twintext_translate for human-readable question text, titles, headers, "
        "option labels and descriptions; do not translate the tool's JSON as a whole. "
        "Preserve field names, question IDs, hidden machine values, option order and required "
        "suffixes. Respect the question tool's schema and length/count limits. If bilingual "
        "text cannot fit a short field, use a concise translated label and keep bilingual "
        "text in the question/title or description where allowed. "
        if settings.translate_questions
        else "Do not translate user-directed questions in conversation or question cards, "
        "even in a final answer or when all responses are selected. "
    )
    return (
        f"TwinText Chat is enabled. Translate selected assistant text into "
        f"{LANGUAGES[settings.target]} ({settings.target}), using {settings.mode} display. "
        + responses + "Questions follow their own setting, independently of response scope. "
        + questions + "For each selected response or question, compose its text "
        "in the conversation's normal source language, "
        "call the local twintext_translate tool with that Markdown, and present its display "
        f"verbatim. Active provider: {settings.provider}. "
        + ("Azure sends source text to Microsoft Azure Translator. "
           if settings.provider == "azure" else "Offline translation stays on this computer. ")
        + "This translation workflow uses ordinary Codex tool/context/output "
        "tokens. Preserve code, paths and links. "
        "Do not translate tool results or hidden reasoning. "
        "If translation fails, show the original reply and explain briefly. Do not substitute "
        "another translation provider. These settings apply to new assistant messages only. "
        "Explicit language or display instructions from the user take precedence."
    )
