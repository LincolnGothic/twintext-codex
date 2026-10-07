---
name: twintext
description: Configure TwinText or translate Codex replies with local Argos models when the user asks for offline translation, bilingual replies, or TwinText settings.
---

Use the local TwinText tools for offline translation and preferences.

- Open settings with `twintext_settings_ui` when that tool is available. Otherwise launch the installed `twintext ui --open` CLI to show the local settings page.
- Read current preferences with `twintext_status` before configuring a workflow. Translation language and plugin UI language are separate settings; `ui_language: auto` follows the host locale in the embedded UI and the browser locale on the standalone page.
- For a new reply, compose the complete answer in the conversation's source language, call `twintext_translate` with its Markdown, then present the returned `display` verbatim. Settings choose bilingual, translated-only, or original mode. If both languages are the same, show the reply once.
- If a user explicitly requests a different language or mode for a single reply, pass the corresponding tool arguments. Save preferences only when the user asks for a persistent change.
- Keep code, commands, paths, links, and protected Markdown intact. TwinText preserves code blocks and conservative inline spans; tables and reference definitions are copied unchanged.
- If the local model is unavailable, keep the original answer and explain the missing model. Model installation downloads official Argos assets and requires internet; translation after installation runs locally. Do not substitute a cloud service.
- If the MCP tools are unavailable, use the installed `twintext translate` CLI. Pass content through a UTF-8 file or stdin with proper shell quoting; do not interpolate user text into executable shell code.

The plugin formats new replies through Codex instructions. It does not modify existing message rendering or Codex's native menu labels. Automatic application requires enabled and trusted bundled hooks; without hooks, the user can invoke this skill explicitly.

