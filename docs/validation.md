# v0.2.0 validation

Validated on Linux x86-64 with Python 3.12 on October 7, 2026.

- **40 unit/integration checks passed**, including the existing engine/Markdown/MCP tests and new hook, concurrent inbox, singleton lock, stale worker output, display-mode, five-language UI, and unchanged original-reply checks. Qt UI tests use the offscreen platform.
- **Real-model desktop flow passed:** the bundled Stop hook received a synthetic French Markdown reply, returned only `{}`, and the companion displayed local French-to-English bilingual output. Switching to translation-only kept the English output. Code appeared once and the inbox original stayed unchanged. [Screenshot](desktop.png).
- Ruff, JavaScript syntax, and installer shell syntax checks passed.

The eight starter models and float32 CTranslate2 engine are retained from v0.1. All 20 language directions previously passed offline smoke checks; [sample results](model-smoke.json) remain available. These checks are not a human quality assessment.

Hook stdin delivery and desktop rendering were tested as separate local processes. Live automatic capture in the installed Codex application requires the updated Stop hook to be reviewed and trusted by the user; it is not granted by installation. Qt tests do not prove always-on-top behavior on every compositor. GNOME/Wayland controls placement and may ignore window hints. ARM Linux was not tested.
