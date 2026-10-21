# TwinText 0.9.3 — use the installed Windows settings paths

- Windows CMD launchers retain the data and settings paths resolved during
  installation, instead of reselecting AppData folders from the launching shell.
  The dedicated Codex launcher also clears an inherited portable-profile override
  within its own process, so it uses that installation's selected profile.
- Runtime directory overrides support separate settings and data locations.
  Existing `TWINTEXT_HOME` portable behavior retains priority for ordinary CLI
  use. Windows APPDATA/LOCALAPPDATA and system-wide environment variables are
  unchanged. Child readers inherit the same TwinText paths.
- Startup logs show the interpreter, settings file and the four manual-mode
  flags, helping distinguish a different profile from a disabled option. No
  conversation text or translation credentials are logged.
- Retain English Translate / Original labels, normal-exit waiting and all
  translation providers, settings, original history, models and cache behavior.

A controlled CMD test reproduces the manual-mode guard with alternate shell
AppData folders. Pinned installation paths keep the selected preferences under
that condition. The exact environment of the user's earlier failing terminal was
not captured. This improves deterministic path selection; it does not certify
native Codex startup or per-message button interaction, which remain experimental.
