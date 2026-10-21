# TwinText 0.11.0 — Translate buttons on Windows and Linux

Linux can now use the same manual **Translate / Original** buttons beneath completed
Codex replies as Windows, with translations displayed in the separate TwinText reader.

- Add **Codex with TwinText** to the Linux applications menu, plus
  `twintext codex-launch --wait` for terminal use. The launcher waits for the user
  to quit Codex/ChatGPT normally, then opens the app and reader. It never closes
  an active conversation or patches Codex application files.
- Locate the native Linux desktop package, including `/usr/lib/chatgpt/ChatGPT`,
  and detect this user's running GUI by executable path. The unrelated Codex CLI
  is never selected. `TWINTEXT_CODEX_EXECUTABLE` supports another native desktop
  installation beside `resources/app.asar`.
- Reuse the existing loopback-only adapter on `127.0.0.1:9223`. Scrolling, new
  replies and settings never start translation. Original Markdown, exact historical
  message selection, cancellation and the manual Paste fallback remain intact.
- Pin the Linux launcher's settings/data directories and quote paths containing
  spaces and shell-sensitive characters. Preserve providers, languages, display,
  caches, models, credentials, original history and window preferences on upgrade.
- Keep **Follow Codex window** independent of the buttons. Turn it off to keep
  the reader stationary instead of moving alongside Codex.
- Update native/web settings guidance, installation documentation, discovery and
  launcher tests, and fresh-install/upgrade smoke checks for the Linux menu entry.

The adapter remains experimental and depends on private Codex renderer details.
Buttons were confirmed visible on the current native Linux host; this does not
certify every Codex version or package. AppImage, Snap and Flatpak have not been
validated. Existing Windows launch behavior is retained. Both platforms use manual
Paste when a message layout is unsupported.

The release workflow publishes Windows/Linux archives and SHA-256 checksums only
after platform regressions, DOM/protocol/UI tests, fresh installation, real Offline
table translation, hook discovery, native Qt rendering and upgrade checks pass.
