# TwinText 0.8.0

- Optional **Follow Codex window** attaches a compact **T** toggle to Codex on
  Windows and Linux X11/XWayland. It follows movement/resizing and hides when
  Codex is minimized or another app is active. Drag to adjust its position.
- Click once to show bilingual or translation-only text; click again to hide
  the reader and return to the original conversation. Completed translations
  are reused. Attached Desktop translates newly captured text on first open.
- Native settings, web settings, CLI (`--follow-codex true`) and MCP expose the
  setting. It is off by default, preserving existing installation behavior.
- Linux recognizes both Codex WM_CLASS and the legacy Chatgpt class when its
  instance explicitly identifies Codex's data directory. Windows validates the
  executable identity and uses pointer-safe Win32 API signatures.
- The companion overlay does not add a native answer-toolbar icon or change
  Codex's existing messages. Native Wayland Codex windows use manual placement.
  Reply selection remains explicit across chats; window following does not read
  Codex conversation state. Restart TwinText after enabling attachment on Linux
  so its XCB backend can be selected when needed.

Local verification includes the regression suite, settings UI checks, and a live
Linux Codex detection / real offline translation / repeated toggle smoke test.
Windows and Linux installer archives publish after the release CI matrix passes.
Offline remains the default provider; existing credentials, preferences and models
are preserved. Packages remain source installers requiring Python 3.10–3.13.
