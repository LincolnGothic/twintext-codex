# TwinText 0.3.0 architecture

TwinText combines a local translation runtime, a Codex integration plugin and an
optional Qt floating reader. Chat and Desktop share preferences, language models,
the Markdown parser and translation cache; `workflow` selects the automatic path.

## Shared runtime

The installer creates a private Python environment with Argos Translate,
CPU CTranslate2/PyTorch and PySide6. Models are downloaded only on request. Eight
starter packages connect English with Chinese, Japanese, French and Spanish;
non-English pairs can pivot through English.

The service identifies translatable Markdown fragments, protects code/paths and
structural syntax, translates the fragments and reconstructs the display. It
supports original, bilingual and translated-only views. Both automatic workflows,
the CLI, settings previews and MCP use this service.

A bounded SQLite cache keys fragments by their digest, source/target language and
model fingerprint. Connections reserve the writer before read/write operations,
commit or roll back their transaction, and close explicitly on exit. Preferences
use atomic replacement under a native advisory lock: `fcntl` on Linux and
`msvcrt` on Windows. Model installation uses the same portable locking layer.

## Chat workflow

1. SessionStart/UserPromptSubmit runs the local context hook, which loads the
   current preferences without reading conversation history.
2. For an enabled Chat workflow, the hook asks Codex to compose its normal reply,
   call `twintext_translate` and display the returned text in the selected mode.
   Paused/original mode emits instructions to stop automatic translation.
3. The MCP tool translates locally and returns its result to Codex. The displayed
   translation is part of the final reply inside the existing chat.
4. The Stop capture path exits immediately in Chat mode, preventing a second
   automatic Desktop capture.

Local inference does not call a translation LLM, but instructions, tool arguments,
tool results and displayed output consume normal Codex context/output tokens.
Automatic translation depends on Codex following the tool instructions; this
plugin does not patch the native chat renderer or rewrite earlier messages.

## Desktop workflow

1. SessionStart/UserPromptSubmit returns no translation instructions in Desktop mode.
2. The Stop hook receives a bounded completed-reply payload and forwards it to the
   private runtime. It returns `{}` without translated text, additional context
   or a request for another model turn. Errors fail open.
3. The runtime validates `last_assistant_message` and stores its original Markdown
   in a local inbox: one latest reply per session, at most 24 sessions. Exact
   session/turn/text duplicates are ignored; Codex transcripts are not edited.
4. If auto-start is enabled and no reader is running, capture opens the Qt reader
   as a compact button. A native lock ensures one reader; explicit repeated
   launches activate the existing window through the inbox control table.
5. A Qt timer reads inbox updates. One background worker translates the latest
   selected request. Revisions prevent stale results from replacing a newer reply
   or language selection; errors leave the original visible.
6. The reader displays translated-only or bilingual Markdown outside Codex and
   copies the same Markdown on request. Display-mode changes reuse a completed
   translation rather than requesting inference again.

This automatic path makes no additional LLM requests and returns no translation
text to Codex. MCP remains available for manual translation, opening the reader
and changing settings; those conversational actions use normal Codex tokens.

## Integration and platform boundaries

The compatibility plugin exposes all three hooks and its MCP server. The installer
removes the obsolete portable root manifest that hid hooks in the tested loader.
Hook review/trust remains a host/user decision. Switching workflows needs a new
Codex chat to discard prior translation instructions already in context.

Linux uses XDG data/config paths and an application-menu launcher. Windows uses
LOCALAPPDATA/APPDATA, native file locks and a Start shortcut. Windows hook/MCP
launchers wait for their child runtime rather than relying on POSIX `execv`
semantics. The adapter resolves the private interpreter across Codex cache copies.
macOS and Claude Code integration are not shipped in 0.3.0.

The Stop payload provides completed text when available, not partial streams,
Codex's UI locale or native menu text. An embedded settings panel can record the
host locale; Desktop otherwise falls back to the system locale. No accessibility
capture, OCR, screen scraping or Codex-window tracking is implemented.

Desktop's bridge has no network listener. The optional web settings server binds
only to loopback and checks its session token, Origin and Host. Inference uses
installed local models; setup/model installation uses upstream network downloads.
Chat integration still runs within the user's ordinary Codex service/session.
