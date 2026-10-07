# Desktop companion architecture

TwinText v0.2 keeps translations outside Codex's model loop.

1. The bundled `Stop` command hook receives Codex's completed-reply payload. `capture.py` forwards bounded stdin to the installed private runtime and returns `{}`. It does not emit `additionalContext`, translated text, or a continuation decision.
2. The runtime validates `last_assistant_message` and stores its original Markdown in a private SQLite inbox. It retains one latest reply per session, at most 24 sessions. Identical session/turn/text events are ignored. No transcript is rewritten.
3. If permitted in settings and no reader is running, capture starts the native Qt reader as a compact button. A Linux file lock ensures one reader; explicit launches activate the existing window through the inbox control table.
4. A Qt timer receives updates. A single background worker runs the existing Argos/CTranslate2 service. Work revisions prevent outdated translations from replacing the selected reply. Pending work is bounded to the latest request. Translation errors leave the original visible.
5. Display modes and interface language are local presentation settings. Translations are rendered in a separate window and never returned to Codex as automatic tool results.

The engine and CLI are reusable without Codex. MCP remains an optional control adapter and settings UI, not the per-reply translation path. Manual in-chat translation is still available on explicit request and has normal token overhead.

The Stop payload supplies completed reply text when available, not the host's locale, partial streaming messages, native menu text, or other applications' visible text. The settings panel records the host locale when available; the reader otherwise falls back to the system locale. Linux accessibility/OCR capture and exact window tracking are future integrations, not claimed by this release.
