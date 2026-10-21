# TwinText 0.9.2 — clearer startup and English message actions

- The Windows launcher waits while an existing Codex/shared ChatGPT app is running.
  Leave the terminal open and quit that app normally; startup continues after it
  exits. Ctrl+C cancels waiting. TwinText never closes or kills an active app.
- Save startup stages and errors to `desktop/launcher.log` in TwinText's data folder.
  Dismissed terminal errors remain available without copying an error line. The
  log contains startup metadata, not conversation text or translation credentials.
- Per-message action labels are always **Translate / Original**, including with
  a Chinese interface. Tooltips and the rest of the interface remain localized.
- Preserve all engines, settings, user data and existing presentation modes.

The dedicated launcher is still required: debugging options cannot be added to
an app that is already running. CLI users opt into waiting with `codex-launch
--wait`; the plain command still reports an existing-app error. The per-message
adapter remains experimental, and native startup/button interaction still needs
a user-run check. Mock startup and owned DOM tests cannot certify it.
