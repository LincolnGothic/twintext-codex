# TwinText for Codex

**Read Codex replies in two languages, or just your preferred language.** TwinText
is a free, open-source translation companion for **Windows and Linux**, powered
by Argos Translate and CTranslate2 on your computer.

Choose **English, Chinese, Japanese, French or Spanish** for translation. Set the
TwinText interface language independently, or let Automatic follow the available
host/system language. Translation runs offline after setup and model downloads.

[Download 0.3.0](https://github.com/LincolnGothic/twintext-codex/releases/tag/v0.3.0) ·
[Installation](#install-or-upgrade) · [Troubleshooting](docs/troubleshooting.md) ·
[Format coverage](docs/output-formats.md)

## Two styles, one installation

| Style | What you see | Codex token use |
| --- | --- | --- |
| **Chat** | New final replies with bilingual or translated-only text inside the existing Codex chat | Translation tool calls, their results and displayed translations use normal Codex tokens |
| **Desktop** | Completed replies in a separate floating window, with a compact draggable button | Automatic translation makes no additional LLM requests and returns no translations to model context |

Chat preserves the original **0.1** experience; Desktop preserves the **0.2.2**
experience. Version **0.3.0** maintains both through a shared translation engine,
Markdown parser, language packs and settings. The old releases are historical
versions; new fixes apply to both styles in the current version.

Select **Translation location** in TwinText settings. Start a **new Codex chat**
after switching styles so instructions from the previous style do not persist.
Desktop is the default for a repository install. A release ZIP chooses its named
style only on a first installation; upgrades preserve the existing choice.

![TwinText displaying an English–Chinese bilingual table](docs/tables.png)

**Public preview:** native Windows and Linux checks passed, but interactive Codex
sessions and window movement still need wider host testing. These downloads are
source-and-installer packages requiring Python; they are not self-contained apps.
macOS is not included. Claude Code integration is not included.

## Download

Choose your operating system and preferred first-install style:

| Operating system | Chat default | Floating-window default | Checksums |
| --- | --- | --- | --- |
| Linux | [Linux Chat ZIP](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/TwinText-0.3.0-linux-chat.zip) | [Linux Desktop ZIP](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/TwinText-0.3.0-linux-desktop.zip) | [SHA256SUMS](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/SHA256SUMS-linux.txt) |
| Windows | [Windows Chat ZIP](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/TwinText-0.3.0-windows-chat.zip) | [Windows Desktop ZIP](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/TwinText-0.3.0-windows-desktop.zip) | [SHA256SUMS](https://github.com/LincolnGothic/twintext-codex/releases/download/v0.3.0/SHA256SUMS-windows.txt) |

Each ZIP supports **both** styles. Install one package, then switch in settings.
Check its SHA-256 hash against the matching checksum file before installation.
Windows packages are unsigned. The release contains TwinText source and installers;
Python, dependency binaries and model weights are downloaded separately.

## Install or upgrade

Requirements: **64-bit Python 3.10–3.13** with pip and venv, internet during setup,
and several GB of free disk space. Python 3.12 is recommended; Python 3.14 is not
supported by the model dependencies. Desktop needs a graphical session.

Native CI validated **Windows x86-64 and Ubuntu Linux x86-64**, using Python 3.10,
3.12 and 3.13 for regression tests and 3.12 for full installation. Other Linux
distributions depend on their Qt libraries and window manager. ARM hosts have
not been validated.

### Linux

Extract your ZIP, open a terminal in its folder and run:

```bash
bash scripts/install-linux.sh
```

From a repository clone, the same command defaults to Desktop. Select Python
explicitly with `TWINTEXT_PYTHON=/usr/bin/python3.12` if needed. The installer
creates a private runtime and **TwinText Desktop** application-menu entry.
The CLI launcher is `~/.local/bin/twintext`.

If Qt reports missing system libraries on Ubuntu/Debian, install the needed packages:

```bash
sudo apt install libegl1 libopengl0 libxcb-cursor0 libxkbcommon-x11-0
```

### Windows

Install 64-bit Python 3.12 from [python.org](https://www.python.org/downloads/windows/)
with pip and venv. Extract your ZIP, open PowerShell in its folder and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

The execution-policy option applies only to that process. The installer does not
change machine/user policy or PATH. To choose an interpreter, append
`-Python 'C:\path\to\python.exe'` to that command.

Open **TwinText Desktop** from Start, or run
`%LOCALAPPDATA%\TwinText\Open TwinText.cmd`. For CLI commands in PowerShell:

```powershell
& "$env:LOCALAPPDATA\TwinText\TwinText.cmd" ui --open
& "$env:LOCALAPPDATA\TwinText\TwinText.cmd" settings --workflow chat --target zh
```

### Finish setup and try a translation

1. **Download a language pack.** Models are not downloaded by default. Open web
   settings with `twintext ui --open` on Linux, or the Windows command above, and
   request the five-language pack. Existing models are preserved on upgrade.
   Review [model notices](THIRD_PARTY_NOTICES.md) before downloading.
2. **Choose your preferences.** Set translation location, source/target language,
   display mode and interface language. The default target is English; choose
   another target to translate an English reply. For an initial test, choose
   source **English**, target **Chinese** and display **Bilingual**.
3. **Test locally.** Paste an English sentence or Markdown table into TwinText and
   press **Translate**. This checks the engine independently of Codex capture.
4. **Enable Codex integration.** Install/update **TwinText** from your personal
   Codex marketplace, restart Codex and review/trust its hooks. The plugin name
   is `twintext`; a new personal marketplace is `twintext-linux` or `twintext-windows`.
   Existing marketplace names and unrelated entries are preserved. Installation
   does not automatically grant hook trust.
5. **Start a new Codex chat.** Chat uses SessionStart/UserPromptSubmit to instruct
   Codex to call the translator. Desktop uses Stop to capture the completed reply.
   Ask for a short English reply or table and verify your chosen display style.

To download models during installation, use `--download-models` on Linux or
`-DownloadModels` on Windows. You can also install one pair with
`twintext models install --source en --target zh`, or all eight starter models
with `twintext models install --starter`. Use the Windows CLI launcher for the
same commands on Windows.

Upgrades preserve settings and installed models unless you explicitly select a
new workflow. The compatibility adapter replaces the old portable root manifest
so the tested Codex loader discovers its hooks; added hooks may require review.
The integration uses GitHub/manual installation rather than an OpenAI public
plugin-directory listing.

## Languages, formats and controls

All five languages are available for translation and the TwinText interface.
Eight starter models connect each supported language to English; other language
pairs pivot through English. Offline quality varies, especially for short or
mixed-language text. Select the source explicitly when automatic detection is uncertain.

**Translation language** and **interface language** are separate settings.
Automatic interface language uses the last supported Codex locale supplied by the
embedded settings panel, falling back to the system language in Desktop. A browser
settings page follows its available host/browser locale. Hooks do not supply Codex's
UI locale, so Automatic cannot always match it; select a language manually if needed.

The shared parser translates table headers/cells, headings, nested lists, task
labels, visible link labels, quotes and supported footnotes. It protects code,
paths, numbers, link destinations and math. Bilingual tables appear as two complete
tables, original followed by translation; translation-only displays one translated
table. See [format coverage and limits](docs/output-formats.md).

![Compact TwinText button with a visible drag grip](docs/floating-button.png)

- **Collapse** shows a compact TwinText button. Drag its six-dot grip or deliberately
  drag the button to move it; click the button to expand. A dot indicates a new reply.
- Drag the reader header to move it; use its bottom-right grip to resize. Settings
  scroll in smaller windows. **Keep above other windows** requests always-on-top behavior.
- The selector retains the latest reply from up to **24 chats**. Desktop receives
  completed replies rather than partial streams and does not import previous turns.
- **Paste text** reads the clipboard only when clicked. Edit the pasted text and press
  **Translate**. **Copy displayed text** copies Markdown, including table structure.
- **Receive Codex replies** controls automatic integration. Disable **Open floating
  button on new replies** if you prefer to launch Desktop yourself. Quit stops the
  window; disable auto-start as well if you want it to remain closed.

Window placement/pinning depends on the desktop. On GNOME/Wayland, hints may be
ignored; where XWayland is available, try `QT_QPA_PLATFORM=xcb twintext desktop`.
The floating reader does not track or overlay the Codex window automatically.

## Costs and privacy

TwinText has **no purchase price, subscription, translation API key or API fee**.
Argos/CTranslate2 inference runs on your CPU after models are installed. Setup and
model downloads use internet access and disk space; reading translations uses local
CPU/RAM. Ordinary Codex access and usage remain subject to your existing plan.

Chat translation adds normal tool/context/output token usage. Its overhead grows
with reply length and can be substantial for long bilingual replies; it is not
claimed negligible. Desktop's automatic capture and translation make no additional
LLM requests or translated-context additions. Asking Codex to open, configure or
manually translate with TwinText still uses normal Codex tokens in either style.

TwinText has no telemetry, background clipboard monitoring, OCR or cloud translation
fallback. Desktop keeps captured original replies on disk locally. In Chat mode,
original/translated text enters the Codex conversation; offline inference does not
make the Codex chat itself offline. Rendered Markdown images are not fetched and
links are not opened automatically. Codex menus, screenshots, PDFs and videos are
outside this release's translation scope.

### Local records

| Data | Linux default | Windows default |
| --- | --- | --- |
| Preferences | `~/.config/twintext/settings.json` | `%APPDATA%\TwinText\settings.json` |
| Translation cache | `~/.local/share/twintext/translations.sqlite3` | `%LOCALAPPDATA%\TwinText\translations.sqlite3` |
| Received Desktop replies | `~/.local/share/twintext/desktop/inbox.sqlite3` | `%LOCALAPPDATA%\TwinText\desktop\inbox.sqlite3` |
| Language models | `~/.local/share/twintext/argos/packages/` | `%LOCALAPPDATA%\TwinText\argos\packages\` |

Linux honors `XDG_CONFIG_HOME` and `XDG_DATA_HOME`. `TWINTEXT_HOME` overrides
settings/data locations for isolated tests.

There is **no timed expiry**. The cache retains at most **10,000 translation
fragments**, evicting least recently used entries as needed. **Remember translations
locally** off stops cache reads/writes but leaves existing entries. **Clear cache**
removes them. The Desktop inbox separately retains one latest original reply per
chat, up to 24 chats, even when translation caching is disabled. **Clear received
replies** clears the inbox without removing preferences, models or cached translations.
Clearing normally completes immediately; empty SQLite files can remain.

## Development and verification

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[desktop,dev]'
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check .
.venv/bin/python scripts/build-release.py --platform linux
.venv/bin/python scripts/build-release.py --platform windows
```

On Windows, use `.venv\Scripts\python.exe` and `.venv\Scripts\ruff.exe`; set
`$env:QT_QPA_PLATFORM = 'offscreen'` before the Qt tests. The development install
above omits the optional engine; add the `engine` extra for real-model work.

For 0.3.0, **72 regression tests passed** on Windows and Linux with Python 3.10,
3.12 and 3.13. Both operating systems also passed installation from a ZIP, native
hook execution, a real English→Chinese table translation in both modes, Qt rendering,
and preservation of settings/models on upgrade. [Validation evidence](docs/validation.md).
Interactive Codex sessions, hook trust and compositor behavior still require host testing.

Read [architecture](docs/architecture.md), [troubleshooting](docs/troubleshooting.md)
and [release notes](docs/release-0.3.0.md). Report bugs with your OS, Python/Codex/
TwinText versions, style, language pair and a sanitized Markdown example; avoid
posting private conversations or local databases.

## Remove TwinText

Disable/uninstall its Codex plugin and quit the reader. Remove only TwinText's
marketplace entry and launchers. On Linux, remove its owned `~/.local/bin/twintext`
link and application-menu entry; on Windows remove its TwinText Start shortcut
and command launchers.

To remove the runtime while keeping records/models, remove the `venv`, `source`
and `plugin` subdirectories under the data directory above. To remove all TwinText
local data, remove that whole data directory and its separate preferences directory.
Keep unrelated marketplace entries and applications intact.

## License

TwinText's own source is [MIT licensed](LICENSE). It is an independent project,
not affiliated with OpenAI or Immersive Translate. Runtime dependencies and language
models retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Several legacy model-weight licenses remain unclear. Free pricing and separate
model downloads do not establish permission for commercial use or redistribution.
The release ZIPs contain no third-party model weights or runtime binaries.
