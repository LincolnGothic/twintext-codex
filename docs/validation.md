# v0.2.1 validation

Validated on October 7, 2026 with installed Codex 0.162.0-alpha.2:

- The old portable package produced **zero hooks** in both `plugin/read` and `hooks/list`, while its skills and MCP server were visible. The runtime explicitly skips hooks for Agent Plugins manifests, matching [upstream source](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/loader.rs) and [issue #47925](https://github.com/openai/codex/issues/47925).
- The corrected Codex compatibility package exposed **one Stop hook** and the TwinText MCP server, both from the repository marketplace and after installation/cache refresh. `hooks/list` confirmed the command points to the installed 0.2.1 capture script, is enabled, and is **untrusted**. User review is still required before live automatic delivery can be confirmed.
- **41 unit/integration tests passed**, including a regression check that no portable manifest shadows the hook package. Ruff, JavaScript syntax, and installer shell syntax passed.
- `scripts/check-codex-plugin.py` checks real runtime package discovery without starting a model turn or changing hook trust. It is separate from synthetic stdin/translation tests.
- Saved Chinese/bilingual preferences and all eight installed models were preserved. The floating window remains running.

## v0.2.0 local translation validation

Validated on Linux x86-64 with Python 3.12 on October 7, 2026.

- **40 unit/integration checks passed**, including the existing engine/Markdown/MCP tests and new hook, concurrent inbox, singleton lock, stale worker output, display-mode, five-language UI, and unchanged original-reply checks. Qt UI tests use the offscreen platform.
- **Real-model desktop flow passed:** the bundled Stop hook received a synthetic French Markdown reply, returned only `{}`, and the companion displayed local French-to-English bilingual output. Switching to translation-only kept the English output. Code appeared once and the inbox original stayed unchanged. [Screenshot](desktop.png).
- Ruff, JavaScript syntax, and installer shell syntax checks passed.

The eight starter models and float32 CTranslate2 engine are retained from v0.1. All 20 language directions previously passed offline smoke checks; [sample results](model-smoke.json) remain available. These checks are not a human quality assessment.

Hook stdin delivery and desktop rendering were tested as separate local processes. Live automatic capture in the installed Codex application requires the updated Stop hook to be reviewed and trusted by the user; it is not granted by installation. Qt tests do not prove always-on-top behavior on every compositor. GNOME/Wayland controls placement and may ignore window hints. ARM Linux was not tested.
