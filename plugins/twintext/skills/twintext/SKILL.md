---
name: twintext
description: Open or configure TwinText Desktop, the offline floating translation companion for Codex on Linux.
---

Use the local tools for opening the companion and changing its preferences.

- Open the floating reader with `twintext_open_desktop`. Open its settings panel with `twintext_settings_ui`. CLI fallbacks are `twintext desktop` and `twintext ui --open`.
- Read `twintext_status` before changing persistent settings. Translation language, display mode, and interface language are independent. The desktop's automatic interface language follows the last host locale supplied by the embedded settings panel, falling back to the system locale.
- Automatic translation happens outside this conversation: the trusted `Stop` hook forwards the completed reply to the local desktop inbox. The companion runs Argos and displays bilingual or translated-only text itself.
- Do not call `twintext_translate` for ordinary replies, repeat the reply in a tool argument, or append its translation to the chat merely because TwinText is enabled. Those actions add model tokens and defeat the display-only workflow.
- Use `twintext_translate` only when the user explicitly requests a translation result inside the conversation. That manual workflow adds normal tool/context/output tokens. Otherwise let the companion display translations.
- Model installation downloads official Argos assets; run it only when requested. Inference is local. Do not substitute a cloud service.

The companion is a separate Linux window. It does not rewrite native chat messages, translate menus, or stream partial responses. Automatic capture requires the installed plugin's `Stop` hook to be enabled and trusted; paste works independently.
