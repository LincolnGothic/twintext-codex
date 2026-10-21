# TwinText 0.9.1 — Windows launcher fix

- Launch the shared Windows app's `ChatGPT.exe` directly when present. Its small
  `Codex.exe` activation stub drops command-line debugging options. Older packages
  with only `Codex.exe` remain supported.
- Wait up to 20 seconds for the loopback debugging port before opening the reader
  and reporting startup success. Report an early app exit or missing port instead
  of silently treating it as a successful launch. No app processes are terminated.
- Explain that "Press any key" follows an error and only closes that error window.
  An existing Codex/shared ChatGPT background instance must be exited normally.

All translation settings, providers, presentation modes and session-cache behavior
are preserved. The per-message adapter remains experimental and opt-in. Windows
package-discovery tests execute the actual discovery script against controlled
packages; startup checks use mocks. These tests do not certify a real native
message click. Exit Codex/ChatGPT normally and open **Open Codex with TwinText.cmd**
from File Explorer to try the updated launcher.
