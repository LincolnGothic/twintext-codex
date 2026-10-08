---
name: twintext
description: Configure TwinText or translate replies with its offline Chat and Desktop workflows on Windows and Linux.
---

Use TwinText's local tools and follow the selected workflow.

- Open the floating reader with `twintext_open_desktop`. Open its settings panel with `twintext_settings_ui`. CLI fallbacks are `twintext desktop` and `twintext ui --open`.
- Read `twintext_status` before changing persistent settings. Translation language, display mode, and interface language are independent. The desktop's automatic interface language follows the last host locale supplied by the embedded settings panel, falling back to the system locale.
- The default `workflow: desktop` translates completed replies outside this conversation. The trusted `Stop` hook forwards original text to the local inbox. Do not call `twintext_translate` for ordinary replies in this mode; use it only for an explicit in-chat translation request.
- In `workflow: chat`, when translation is enabled and mode is not `original`, compose the complete final reply, call `twintext_translate` with its Markdown, and present the returned `display` verbatim. The trusted instruction hooks supply current preferences. This workflow uses ordinary Codex tool/context/output tokens even though translation inference is offline.
- User instructions and current preferences take precedence over earlier translation instructions. When Chat mode is disabled or set to `original`, present new replies normally. Start a new chat after switching workflows to discard previous session instructions.
- Save `workflow: chat` or `workflow: desktop` only when the user requests that persistent change. Translation location, display mode, target language, and interface language are separate settings. Both workflows use the same Markdown engine, cache, and language models.
- Model installation downloads official Argos assets; run it only when requested. Inference is local. Do not substitute a cloud service.

The companion is a separate Windows/Linux window. Neither workflow rewrites previous messages or translates Codex menus. Desktop displays completed replies, not partial streams. Automatic capture or Chat instructions require their bundled hooks to be enabled and trusted; installation does not grant trust. Paste works independently. No macOS release is provided.
