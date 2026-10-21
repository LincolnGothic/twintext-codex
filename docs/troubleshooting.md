# TwinText troubleshooting

TwinText 0.11.0 uses only per-reply Translate / Original and a separate reader.
Manual Paste remains the fallback. Inline and automatic Desktop modes are retired.

## Text stays in its original language

Set the correct source and target: English → English stays unchanged. Test with
English → Chinese and Bilingual using a public sentence and Paste → Translate.
Code, numbers, paths and protected blocks remain original. **Original** in the
reader hides translation; click **Translate** to show it again. No new reply or
scroll gesture triggers translation.

Offline needs installed models. Read `twintext status` or `twintext models list`;
install only when requested with `twintext models install --source en --target zh`
or the language-pack settings button. Non-English pairs need both English legs.
Windows uses the runtime's TwinText.cmd for CLI commands. Model downloads are opt-in.

## The Translate button disappeared

The old display selector could close the reader when switching to inline mode.
Version 0.10.0 removes that selector and the workflow-triggered close path. Older
profiles migrate to the manual reader; changing provider/language/display/cache
no longer switches integration methods.

1. Check **Enable Translate buttons** in settings. A disabled integration does not
   show message buttons. Keep the TwinText reader running, even when collapsed.
2. If Codex was already opened through the dedicated launcher, reopen TwinText with
   **Open TwinText.cmd** or `twintext desktop` on Linux. Its adapter retries the connection.
3. Otherwise use **Open Codex with TwinText.cmd** on Windows, or **Codex with TwinText**
   from the Linux applications menu (`twintext codex-launch --wait`). A normally launched
   Codex instance does not automatically have its debugging connection.
4. Open a completed assistant reply. Unsupported layouts, hidden reasoning, tool
   results and question cards receive no button. Do not translate another reply
   as a substitute. Use the reader's manual Paste fallback.

The Windows/Linux adapter is experimental and depends on private Codex renderer details.
Keep one main Codex window open. A host update can require an adapter update.
Manual Paste remains available on both platforms.

## The Codex launcher stops at "Press any key"

Pressing a key only dismisses an error. Read the **Startup failed** line before it.
Open the runtime's `desktop/launcher.log` after the terminal closes. Logs contain
startup metadata, interpreter, exact settings path and manual flags, without chat
text or translation credentials.

Generated CMD files pin the installed data/settings directories. If the path is
unexpected, rerun the current installer for that installation. Portable `TWINTEXT_HOME`
still takes priority for ordinary CLI use; the dedicated Codex launcher uses its
installed profile. Separate `TWINTEXT_DATA_DIR`/`TWINTEXT_CONFIG_DIR` overrides are
process-local and do not change Windows AppData globally. Preferences are not reset.

**Waiting** is different: leave that terminal open, then quit Codex and its shared
ChatGPT app normally, including tray/background instances. The launcher continues
only after a normal exit. Ctrl+C cancels; TwinText never kills a conversation.
Closing a single chat window may leave the shared app running.

The Windows launcher selects the installed shared ChatGPT.exe, falling back to legacy
Codex.exe. Linux selects the native desktop executable beside `resources/app.asar`,
including `/usr/lib/chatgpt/ChatGPT`. It never selects the unrelated Codex CLI.
Both wait up to 20 seconds for debugging on 127.0.0.1:9223 before starting
the reader. Port conflicts, early exit or host rejection produce errors. Do not
forward the port to a network or add broad remote-origin flags. Proxy settings are
bypassed for this loopback connection. No Codex files are patched. Native startup
and message interaction must still be checked on the actual host version.

## Reader, settings, clipboard and window behavior

Use **Open TwinText.cmd**, `twintext desktop` or the settings panel's Open reader.
Settings replaces the reading area; Back restores it. Dropdown wheels scroll the
settings rather than changing selection. Use clicks or keyboard keys.

The compact button toggles the reader; drag **T** deliberately to move it. **−** collapses;
**×** on either window quits TwinText. Follow/always-on-top depend on the window
manager. Follow supports Windows and X11/XWayland; native Wayland may require
manual positioning. When inactive/minimized, an attached window can be hidden.
Turn off **Follow Codex window** to keep the reader stationary while moving Codex;
message buttons continue working independently of window following.

Paste reads the clipboard only on click. Edit and press Translate. Copy original
always copies source Markdown, including when bilingual or translated text is shown.
Original cancels pending translation and keeps source visible. Failed requests
also keep source visible; no paid or other provider is selected as a fallback.

## Interface language

Translation and interface languages are independent. Automatic uses available
host/system locale; choose a language explicitly if it does not match Codex.
All five interface languages retain English Translate / Original message actions
and localized explanatory text. No setting changes the Codex app's own language.

## Tokens, history and caches

Per-reply buttons and the reader make no LLM calls or translated-context additions.
Asking Codex to configure/open/explicitly translate text uses normal Codex tokens.
Existing inline translations in old chats remain there; no transcripts are edited.

Selected originals persist locally in desktop/inbox.sqlite3. Older Desktop retained
originals are imported without deleting records, preserving timestamps and chronology.
Cache clearing retains originals/models/settings. **Clear received replies** removes
received history only when explicitly requested.

Session cache keeps fragments and complete reader translations in process memory
until TwinText exits, including shutdown. Existing disk translations are ignored;
no shutdown script is needed. Disk caching has no timed expiry. Turning caching off
disables reads/writes while preserving existing data. See README for default paths.

## Google Free (experimental)

This is an unofficial keyless interface, not Google Cloud Translation. It may
rate-limit, fail or change; no availability, quality or free quota is guaranteed.
Source text is sent to Google. System proxies apply to provider requests. A local
loopback adapter connection bypasses proxies. For network/429 errors, wait and retry
or explicitly choose another configured provider. Never silently switch providers.
Google-only Traditional Chinese requires zh-TW; choose zh before Offline/Azure.

## Azure provider

Select Azure explicitly after configuring your own credentials with
`twintext azure-configure` or native desktop settings. The embedded panel only
reports configured status and never accepts or reveals a key. For 401 check key
and region; for 403 check access/region/quota; for 429 wait and check Microsoft
quota/pricing. For timeout/network errors check connectivity and try shorter text.
No automatic provider fallback occurs. Offline remains local; screenshots are
never sent to Azure. Linux credentials need owner-only directory/file permissions
700/600; protect this unencrypted file and backups. See README for setup/privacy.

## Report a problem

Include OS/architecture and Python/Codex/TwinText versions, sanitized startup error,
language pair and whether Paste works. Do not post keys, private chat text or local
databases. Tests use controlled DOM/protocol/Qt fixtures and cannot certify every
Codex renderer or window manager.
