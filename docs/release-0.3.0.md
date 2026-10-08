# TwinText 0.3.0 — free Windows and Linux preview

**Bilingual or translated-only Codex replies, in chat or a floating window.**
TwinText is a free, open-source companion using Argos Translate and CTranslate2
locally after setup. English, Chinese, Japanese, French and Spanish are supported
for translation and the TwinText interface, with independent language settings.

## Choose your style

| Style | Where translations appear | Codex token use |
| --- | --- | --- |
| **Chat** — continues the 0.1 experience | New final replies inside your existing Codex chat | Normal instruction/tool/context/output usage; long bilingual replies add more tokens |
| **Desktop** — continues the 0.2.2 experience | Completed replies in a separate floating reader | Automatic translation makes no additional LLM requests and adds no translated text to Codex context |

Both styles share the corrected Markdown translator, models, cache and preferences.
Install one ZIP and select **Translation location** in settings. Start a new Codex
chat after switching styles. Translation language, display mode and TwinText
interface language can be chosen independently.

## Downloads

| Operating system | Chat first-install default | Floating first-install default | Checksums |
| --- | --- | --- | --- |
| Linux | [Chat ZIP](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/TwinText-0.3.0-linux-chat.zip) | [Desktop ZIP](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/TwinText-0.3.0-linux-desktop.zip) | [SHA256SUMS](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/SHA256SUMS-linux.txt) |
| Windows | [Chat ZIP](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/TwinText-0.3.0-windows-chat.zip) | [Desktop ZIP](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/TwinText-0.3.0-windows-desktop.zip) | [SHA256SUMS](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/SHA256SUMS-windows.txt) |

Every ZIP supports both styles. The filename chooses the default on a first
installation; upgrades preserve the user's selected style. Verify the ZIP's
SHA-256 hash against the matching checksum file.

These are **source-and-installer packages requiring Python**, not self-contained
executable apps. Requirements: 64-bit Python 3.10–3.13 with pip/venv (3.12 recommended),
internet during setup and several GB of disk space. Desktop needs a graphical
session. Native validation covers Windows x86-64 and Ubuntu Linux x86-64. Other
Linux distributions/window managers and ARM hosts need further testing.
**macOS and Claude Code integration are not included.** Windows downloads are unsigned.

## Install and enable

Extract your ZIP and open a terminal/PowerShell in its folder.

**Linux:**

```bash
bash scripts/install-linux.sh
```

**Windows:** install 64-bit Python 3.12 from [python.org](https://www.python.org/downloads/windows/), then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

The Windows execution-policy option is process-scoped. The installer creates a
private runtime and an application-menu/Start shortcut without changing global
Python, PATH or Codex application files. Some Linux Qt system libraries may need
installation through the distribution's package manager.

1. **Download models.** Existing models survive upgrades, but new ones are not
   downloaded by default. Open web settings with `twintext ui --open` on Linux, or
   `& "$env:LOCALAPPDATA\TwinText\TwinText.cmd" ui --open` in Windows PowerShell,
   and request the language pack. Alternatively append `--download-models` to the
   Linux installer or `-DownloadModels` to the Windows command.
2. **Choose settings.** The default translation target is English. For a first
   English→Chinese test, choose source English, target Chinese and Bilingual display,
   then paste a sentence into TwinText and press Translate.
3. **Enable the plugin.** Install/update TwinText from your personal Codex marketplace,
   restart Codex and review/trust its hooks. Installation does not automatically
   grant trust. Chat uses SessionStart/UserPromptSubmit; Desktop uses Stop.
4. **Start a new chat.** Verify a completed reply or table in your chosen style.

[Full installation guide](https://github.com/LincolnGothic/twintext-codex#install-or-upgrade) ·
[Troubleshooting](https://github.com/LincolnGothic/twintext-codex/blob/main/docs/troubleshooting.md)

## Included improvements

- One maintained implementation for both historical styles, with Windows/Linux
  paths, file locks, private-runtime launchers and upgrade preservation.
- Table headers/cells, nested lists, task labels, headings, link labels, quotes and
  supported footnotes translate while code, paths, numeric cells and math remain intact.
- Bilingual tables show the complete original table followed by its translation;
  translated-only shows one translated table.
- A compact floating button with a visible drag grip, resizable reader and scrolling
  settings. Copy returns Markdown; clipboard text is read only on request.
- Separate controls for received replies and cached translations. There is no timed
  expiry: cache capacity is 10,000 fragments; inbox capacity is the latest reply
  from 24 chats. Disabling cache preserves old entries; the clear controls remove
  each store independently.
- Explicit database connection closure, reliable concurrent inbox transactions and
  Windows hook process lifetime/UTF-8 handling.

## Costs, privacy and scope

TwinText has no purchase price, subscription, license activation, translation API
key or API fee. Inference uses local CPU/RAM. Ordinary Codex access/usage is separate.
Chat's tool/context/output overhead is not claimed negligible. Asking Codex to open,
configure or manually translate with TwinText uses normal Codex tokens in either style.

Desktop stores captured original replies locally. Chat translations enter the
Codex conversation; offline inference does not make Codex itself offline. There is
no TwinText telemetry, background clipboard monitoring or cloud translation fallback.
The floating reader does not automatically track Codex. Native menus, old messages,
partial streams, screenshot text, PDFs and videos are outside the automatic translation
scope. Automatic Chat translation depends on Codex following the tool instructions.

TwinText's own source is MIT licensed. Models and runtime dependencies are downloaded
from upstream and retain their own licenses. Some legacy Spanish/Japanese model-weight
licenses remain unclear; free pricing or separate downloads do not establish permission
for commercial use or redistribution. These ZIPs contain no third-party model weights
or runtime binaries. [Third-party/model notices](https://github.com/LincolnGothic/twintext-codex/blob/main/THIRD_PARTY_NOTICES.md).

## Validation and preview status

**72 regression tests passed** on Windows and Linux with Python 3.10, 3.12 and 3.13.
Both native package checks passed fresh installation, hook execution, real
English→Chinese table translation in both display modes, Qt rendering and settings/
model preservation on upgrade. [Validation evidence](https://github.com/LincolnGothic/twintext-codex/blob/main/docs/validation.md).

This remains a **public preview**: actual Codex sessions, hook trust prompts and
window movement/pinning need wider host testing. It is a GitHub/manual-install
release rather than an OpenAI public plugin-directory listing. Report issues with
your versions, style, language pair and a sanitized Markdown example.
