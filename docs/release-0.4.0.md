# TwinText 0.4.0 — Offline and optional Azure translation (preview)

TwinText now supports Microsoft Azure Translator while retaining the existing
Offline Argos/CTranslate2 engine, Chat/Desktop workflows, Markdown protection,
bilingual rendering and local translation cache. Existing users remain Offline;
Azure must be selected explicitly. English, Chinese, Japanese, French and Spanish
are supported, with Chinese mapped to Azure's `zh-Hans`.

## Downloads and installation

Four source-and-installer ZIPs support both workflows; their names select the
first-install default. Upgrades preserve existing settings and models.

- `TwinText-0.4.0-windows-chat.zip` and `TwinText-0.4.0-windows-desktop.zip`
- `TwinText-0.4.0-linux-chat.zip` and `TwinText-0.4.0-linux-desktop.zip`
- `SHA256SUMS-windows.txt` and `SHA256SUMS-linux.txt`

Verify the matching checksum, extract the ZIP, quit the old floating reader, then
run `scripts/install-windows.ps1` or `scripts/install-linux.sh` from the extracted
folder. These require 64-bit Python 3.10–3.13 (3.12 recommended), pip/venv and internet
during setup. They are not self-contained executable apps; models and runtimes are
not bundled. Desktop requires a graphical session. Windows packages are unsigned.
No macOS or Claude Code integration is included. See README for detailed installation.

## Azure configuration and privacy

Create your own Microsoft Azure Translator resource. Configure its key and region
through the native floating reader's **Configure Azure credentials** button or the
masked local terminal prompt `twintext azure-configure`. Select Azure in settings
and save, or run `twintext settings --provider azure`. The embedded Codex/MCP/web
panel receives only configured/not configured status; never paste a key into chat.
Windows uses the current user's Credential Manager. Linux uses a separate owner-only
credentials file, directory/file permissions 700/600, outside `settings.json`.
Linux credentials are unencrypted at rest; protect the account, disk and backups.

Offline mode keeps translation local. Azure sends source text to Microsoft Azure
Translator, never screenshots. The REST v3 API is used directly, without an Azure
SDK. No developer-owned shared key is bundled. Microsoft's current quotas/pricing
apply; Azure is not guaranteed permanently free. Azure errors never silently fall
back to another provider. Local usage stores only month, request count and source
character count, excludes cache hits, and sends no telemetry. Optional translation
text caching remains separate and provider-specific.

## Validation and limits

The release workflow runs the complete 93-test suite, Ruff and JavaScript checks,
builds all four ZIPs, then installs/smoke-tests the release archives on Windows and
Linux before publication. Azure is mocked; no real credentials or live Azure calls
are required. Regression tests cover provider migration, cache separation, sanitized
errors, cancellation, counters, concurrent selection and asynchronous UI privacy.

Only the global HTTPS resource-key endpoint is supported; custom/VNet endpoints
and Entra ID are not included. Python cancellation is cooperative, with a 15-second
timeout per in-flight request. OCR/menu/screenshot translation is outside TwinText's
scope. Physical desktop/window-manager limitations and translation quality still
apply. Chat uses ordinary Codex tokens; Desktop automatic translation adds no LLM
calls, but Azure charges may apply when selected. See README and architecture docs.
