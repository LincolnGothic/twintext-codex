# TwinText 0.5.1 — Floating reader close and safe dropdown scrolling (preview)

- The compact floating button and expanded reader now have visible **×** controls.
  **×**, the existing Quit button, or closing either window exits the reader.
  **−** still collapses it. Shutdown cancels pending translation and hides both
  widgets before releasing the reader's single-instance lock.
- Switching from Desktop to **Codex chat** closes an already-running floating
  reader, including when the setting changes through the embedded/web panel or
  CLI. Pending activation events cannot reopen it during shutdown. A background
  launch that races with a switch to Chat exits without showing a floating button.
  Explicitly opening the reader for manual preview/settings remains available.
- Mouse-wheel scrolling no longer changes native dropdown selections, including
  response scope, provider, languages, display mode and the chat selector. Wheel
  events can still scroll the surrounding preferences panel. Clicks and keyboard
  selection continue to work.

The response-scope default remains **Final answers only**. **All responses** means
visible assistant progress messages and final answers; hidden internal reasoning
and raw tool results are excluded. **Translate questions in chat** remains enabled
by default and independent of response scope. Existing preferences, language models,
providers and cached translations are preserved.

Closing the reader preserves its auto-start setting. In Desktop mode, a later
completed reply can reopen it when auto-start is enabled. Chat mode never starts
the floating reader automatically. Restart Codex and open a new chat after updating.

Validation includes 112 regression tests, native Qt wheel routing, shutdown and
Chat-switch checks, plus the Windows/Linux release installation smoke checks.
