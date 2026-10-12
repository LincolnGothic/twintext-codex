---
name: twintext
description: Configure TwinText or translate replies with its Chat and Desktop workflows on Windows and Linux, using the selected Offline or Azure provider.
---

Use TwinText's local tools and follow the selected workflow.

- Open the floating reader with `twintext_open_desktop`. Open its settings panel with `twintext_settings_ui`. CLI fallbacks are `twintext desktop` and `twintext ui --open`.
- Read `twintext_status` before changing persistent settings. Translation language, display mode, and interface language are independent. The desktop's automatic interface language follows the last host locale supplied by the embedded settings panel, falling back to the system locale.
- The default `workflow: desktop` translates completed replies outside this conversation. The trusted `Stop` hook forwards original text to the local inbox. Do not call `twintext_translate` for ordinary replies in this mode; use it only for an explicit in-chat translation request.
- In `workflow: chat`, when translation is enabled and mode is not `original`, compose the complete final reply, call `twintext_translate` with its Markdown, and present the returned `display` verbatim. The trusted instruction hooks supply current preferences. This workflow uses ordinary Codex tool/context/output tokens with either provider.
- User instructions and current preferences take precedence over earlier translation instructions. When Chat mode is disabled or set to `original`, present new replies normally. Start a new chat after switching workflows to discard previous session instructions.
- Save `workflow: chat` or `workflow: desktop` only when the user requests that persistent change. Both workflows use the same Markdown engine and cache.
- Offline is the default and keeps translation local. Azure sends source text to Microsoft Azure Translator, never screenshots. Only select Azure on explicit user request; never switch providers as a fallback. Azure requires the user's own credentials, subject to Microsoft's current quotas/pricing; no shared developer key is bundled and Azure is not guaranteed free.
- Credentials must be entered through `twintext azure-configure` or native desktop settings. Never ask for, accept, transmit or reveal keys through Chat, MCP or the embedded UI. Status exposes only configured/not configured. Windows uses Credential Manager; Linux uses an owner-only unencrypted private file outside normal settings. Monthly usage contains metadata only and sends no telemetry.
- Model installation downloads official Argos assets; run only when requested and Offline is selected.

The companion is a separate Windows/Linux window. Neither workflow rewrites previous messages or translates Codex menus. Desktop displays completed replies, not partial streams. Automatic capture or Chat instructions require their bundled hooks to be enabled and trusted; installation does not grant trust. Paste works independently. No macOS release is provided.
