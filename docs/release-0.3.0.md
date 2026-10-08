# TwinText 0.3.0 — free Windows and Linux preview

TwinText now keeps both experiences: **Chat** translates new final replies inside
Codex, and **Desktop** displays completed replies in its floating window.
Choose the translation location in settings. Both share one offline engine and
the corrected Markdown parser: tables, nested lists, checkboxes, visible link
labels, footnotes and protected code/paths behave consistently.

Windows native paths and file locking are supported. The Windows installer
creates a private runtime, Start menu shortcut, and Codex plugin registration.
Linux keeps XDG directories and its application-menu launcher. macOS is not
released. Older preferences are preserved; unknown future settings survive updates.

## Downloads

Choose a `windows` or `linux` ZIP, then `chat` or `desktop` as your first-install
default. These are **source + installer packages**, not self-contained executable
apps. All packages support both styles; upgrades preserve your selected style.
Verify your ZIP against the matching `SHA256SUMS` file before running its installer.

Requirements: 64-bit Python 3.10–3.13 (3.12 recommended), pip/venv, a graphical
session for Desktop, internet during setup and several GB of free disk space.
Windows installers are unsigned. No administrator access, subscription, license
activation, API key, paid translation service or macOS signing service is used.

On Linux, extract the ZIP and run `bash scripts/install-linux.sh` from its folder.
On Windows, extract the ZIP, open PowerShell in its folder and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

The process-scoped execution-policy option does not change machine/user policy.
Install Python from python.org first if the installer cannot find it. No global
Python environment or PATH is modified.

Language models are preserved on upgrade and **not downloaded by default**.
Open the web settings page (`twintext ui --open`, or the Windows command launcher)
and request the language pack, or pass `--download-models` / `-DownloadModels`.
See `THIRD_PARTY_NOTICES.md`: several legacy model licenses remain unclear;
weights and third-party runtime binaries are not redistributed in these ZIPs.

After setup, install/update **TwinText** from your personal Codex marketplace,
restart Codex, and review its hooks. Installing a plugin does not grant trust.
Chat uses SessionStart/UserPromptSubmit; Desktop uses Stop. Start a new Codex chat
after switching styles. The plugin does not patch Codex or rewrite previous replies.

Offline inference has no translation API fee. Chat adds normal Codex tool/context/
output token usage. Automatic Desktop translation returns no translated text to
Codex and makes no additional LLM requests. Ordinary Codex usage is separate.

## Preview status

This is the first Windows/Linux dual-style public preview. Automated Linux and
Windows tests validate settings, locking, hook scripts, the installer and Markdown
rendering. Codex hook trust and native window movement depend on the user's host
and still need desktop testing on each supported environment. This is a GitHub
release, not an OpenAI public-directory listing. No payment system is included.
