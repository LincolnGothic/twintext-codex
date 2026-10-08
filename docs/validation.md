# Windows/Linux 0.3.0 preview validation

- Linux: 72 regression tests pass, including Chat/Stop separation, legacy/future settings preservation, native cross-process locks, UTF-8 pipes and the two display modes.
- Native CI exposed and repaired concurrent inbox read/write lock upgrades, unclosed cache connections, Windows hook process lifetime, canonical Windows home paths and newline handling. Cache connection closure and transaction rollback have explicit regression coverage.
- Actual Codex 0.162.0-alpha.2 `plugin/read` discovers SessionStart, UserPromptSubmit and Stop from the compatibility package, plus its MCP server. This read-only probe did not change hook trust or run a model turn.
- Existing offline models translate the shopping-table fixture into Chinese, Japanese, French and Spanish; table shape and numeric cells remain intact. The Qt reader renders bilingual and translated-only results. These tests are not a human translation-quality assessment.
- Ruff, JavaScript syntax, Linux installer syntax and skill validation pass. Source-installer archives are checked for private runtime/data/model files and have SHA-256 checksums.
- Native Windows and Linux package installation, hook invocation, real English→Chinese table translation, Qt rendering and upgrade preservation are gated by the release workflow. Inspect the associated Actions run for current results; no Windows result is assumed before the job passes.
- No runtime binaries or model weights are included in release ZIPs. Upstream legacy Spanish/Japanese model-license ambiguity is documented in THIRD_PARTY_NOTICES.md, not claimed resolved.
- Native interactive Codex conversations, hook trust prompts and compositor window movement require host testing. The first Windows/Linux release is marked as a public preview.

# Desktop v0.2.2 validation

Validated on Linux x86-64 with Python 3.12 on October 7, 2026:

- **60 unit/integration tests passed.** New coverage includes table structure in both display modes, nested lists, heading styles, checkboxes, quotes, reference/inline link labels, code brackets in labels, footnotes, currencies, file links, math, HTML/code/diagram preservation, malformed Markdown, cache limits and independent clearing, and floating-button drag versus click.
- **Real models passed in four translation directions:** English → Chinese, Japanese, French and Spanish on the same mixed table/list/link/quote/code sample. Headers and cell text translated; numeric cells, table shape, URL and code remained intact. [Raw synthetic results](format-smoke.json).
- Qt rendered the Chinese bilingual and translation-only outputs correctly; [table screenshot](tables.png). The [collapsed control](floating-button.png) has a visible grip; tests verify that both the grip and a deliberate button drag request a window move, while only a click expands. Actual desktop movement depends on compositor support for Qt's system-move request.
- Clearing 10,000 synthetic cache entries took approximately **0.5 ms** in the isolated local test; no user records were deleted. Turning caching off preserves existing entries. Clearing translations does not remove received replies or change preferences.
- Ruff, JavaScript syntax, installer syntax and whitespace checks passed. The bridge plugin stays at 0.2.1 with an unchanged capture command, preserving existing trust; the app/runtime is 0.2.2.

## Bridge v0.2.1 validation

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
