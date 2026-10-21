---
name: twintext
description: Configure TwinText's manual per-reply reader or explicitly translate pasted text on Windows and Linux with Offline, Azure or experimental Google Free.
---

TwinText has one Codex translation method: per-reply **Translate / Original**
buttons select exact completed replies in a separate reader. Manual Paste is the
fallback. Inline-chat translation and automatic Desktop capture/forwarding are retired.

- Keep ordinary assistant replies, progress and questions in their original language.
  Do not call TwinText translation or forwarding tools for them. Scrolling and new
  replies never translate automatically. The user clicks a per-reply button; no
  translation enters model context. Explicit translation requests take precedence.
- Open the reader with `twintext_open_desktop` or `twintext desktop`; open settings
  with `twintext_settings_ui` or `twintext ui --open`. Windows CLI uses the installed
  TwinText.cmd or private interpreter. Read `twintext_status` before changing settings.
- Translation provider, source/target language, reader display, interface language,
  enabled state, pin/follow and cache policy are independent. Save only requested
  preferences. Do not request retired workflow, scope, question, message-mode or
  automatic-start settings; the public settings tool/CLI no longer accept them.
- Per-reply buttons require the dedicated Open Codex with TwinText.cmd launcher on
  Windows, or the Codex with TwinText application-menu entry on Linux
  (`twintext codex-launch --wait`). If it reports Waiting, the user leaves its terminal open and quits Codex
  and its shared ChatGPT app normally, including tray instances. Never close/restart
  an active Codex session for the user. The launcher pins installation paths and logs
  settings provenance. It never patches Codex application files.
- The adapter is experimental and depends on private Codex message props. Unsupported
  messages have no button; never substitute the latest reply or clipboard. Existing
  buttons may reconnect by opening TwinText again if Codex already has its local
  debugging connection. Otherwise the user uses the dedicated launcher. Linux native
  packages use the same adapter through their desktop executable, never the Codex CLI.
  Manual Paste remains available on both platforms.
- The reader's Original action cancels pending translation; Translate shows it again.
  Copy original preserves exact source Markdown. Selecting history shows original
  text first and waits for a click. Old valid profiles migrate to this method;
  originals, timestamps, languages, providers and unrelated preferences are retained.
- `cache_lifetime: session` keeps fragment and reader-result translations only in
  process memory, released when TwinText exits/shuts down. Existing disk translations
  are ignored. `cache: false` disables both cache reads/writes. Clear cache clears
  translations, retaining original history, settings and models. Default disk caching
  preserves the existing persistent policy. Do not clear user data unless requested.
- Offline is the default and stays local after model downloads. Install models only
  when requested with Offline selected. No ordinary reply requires a tool invocation.
- Azure sends source text to Microsoft using the user's credentials. Select only
  on explicit request, never as a fallback. Credentials must be entered through
  `twintext azure-configure` or native settings, never through chat/MCP/web fields.
  Never reveal keys; status reports configured/not configured. Windows uses Credential
  Manager; Linux uses an owner-only unencrypted private file. Microsoft pricing and
  quotas apply; no shared key or guaranteed free service is bundled.
- Google Free (`google-free`) is optional, keyless and unofficial, not supported by
  Google Cloud. It may fail, change or rate-limit and guarantees no availability,
  quality or free quota. Text is sent to Google. Select only on explicit request;
  never as a fallback. `zh` is Simplified Chinese; Google-only `zh-TW` is Traditional.
  Choose `zh` before switching from a Traditional profile to Offline or Azure.

The reader is a separate Windows/Linux window. It does not edit prior messages or
translate Codex menus, hidden reasoning, tool results or question-card controls.
The plugin's context hooks explain manual behavior; Stop no longer captures replies.
Start a new chat after upgrading from retired modes to replace stale instructions.
No macOS release is provided. User instructions override defaults.
