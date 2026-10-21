# TwinText 0.10.0 — one manual reader

Click **Translate / Original** below a completed Codex reply and read it in the
separate TwinText window. This is now the only Codex translation method. Manual
**Paste text** remains available, including on Linux.

- Remove inline-chat translation, automatic Desktop capture/forwarding, and the
  location/scope/question/automatic-start/message-mode selectors. Retire their
  public CLI/MCP options and Stop registration. Older Stop registrations become
  inert compatibility calls. Replies, scrolling and settings never translate
  automatically.
- Prevent settings from closing the reader through a workflow switch, which
  could remove the per-reply buttons. Keep English **Translate / Original** labels,
  localized tooltips, the reader toggle, and exact **Copy original** behavior.
- Migrate valid older profiles to the manual reader. Preserve provider, languages,
  display, enabled state, cache policy, credentials, models and unknown settings.
  Import retained old Desktop originals into history without deleting or replacing
  them; preserve timestamps, chronology and idempotence. Existing cache policies
  remain unchanged, including memory-only session caching.
- Keep Offline as the default, plus optional Azure and Google Free (experimental).
  Google still uses an unofficial keyless interface, may fail/change/rate-limit,
  has no guaranteed availability/quality/free quota, and sends source text to Google.
  Providers are never selected as a fallback.
- Publish one Windows archive and one Linux archive with SHA-256 checksums, as a
  regular GitHub release. Update README, settings guidance and installation smoke
  tests for the single method.

The per-reply adapter remains experimental and Windows-only. It uses Codex's
private renderer and a local debugging connection; this release does not make it
an official OpenAI integration. Linux retains manual Paste. The dedicated Windows
launcher still waits for a normal user exit and never closes an active Codex chat.
Owned DOM/protocol/Qt tests and fresh-install CI do not certify every native Codex
version. Existing chat transcripts and earlier inline translations are not edited.
