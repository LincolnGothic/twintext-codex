# TwinText 0.12.1 — Reopen the reader without restarting Codex

- Closing either TwinText window with **×** or the window manager now hides its UI
  while leaving Codex's per-reply Translate / Original buttons connected. Click a
  reply action or open TwinText again to restore the reader. **−** still collapses
  to the floating T button; the reader's separate **Quit** action exits TwinText.
- Cancel unfinished translation when closing the window and reject late progress
  and completion. Preserve exact original copying, completed translations, paste
  drafts, original history, preferences and the current session cache.
- Keep dismissed windows hidden when Codex regains focus or follow settings change.
  Reopening alone never starts translation.
- Reuse an existing supported Codex debugging connection when opening the dedicated
  launcher again, including its normal wait mode. The launcher does not restart
  Codex. Instances started without debugging still require normal exit before the
  launcher can enable the connection. Unsupported or ambiguous targets stay rejected.
- Update close tooltips and accessibility labels in all five interface languages.

The same implementation serves Windows and Linux. Regressions cover window-close
and explicit Quit behavior, manual/message cancellation, stale results, cache/draft
preservation, focus/follow behavior, reconnecting the renderer adapter, and launcher
reuse on both platforms. Release publication retains the Windows/Linux tests and
fresh archive installation/upgrade gates. Native Codex renderer/compositor behavior
still depends on the installed host version.
