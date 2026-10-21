# TwinText 0.9.0 — experimental per-reply buttons and session caching

- Optional Translate / Original buttons for recognized completed Codex messages,
  including older replies. Explicit clicks select that exact original Markdown
  in the separate reader. Scrolling does not translate; Codex Copy is unchanged.
- Existing automatic Desktop, floating Chat and inline Chat remain available.
- Session-only caching covers fragments and full reader results. Exiting TwinText
  releases new translations, preserving settings, language models and originals.
  Clear cache clears both translation stores without removing original history.
- Native and web settings expose both options in five languages. They preserve
  the selected provider; Offline remains the default for new installations.
- Windows installs include Open Codex with TwinText.cmd. It refuses to close a
  running app and opens optional loopback debugging on port 9223.
- Preserves 0.8.0 window following and all previous presentation choices.

The per-message adapter is experimental, Windows-only and disabled by default.
It uses private React props through a runtime adapter and does not patch Codex.
Use one supported Codex main window. Other local programs may access the debugging
endpoint; never forward it to a network. Launch Codex normally to stop debugging.

Windows `26.1013.4894.0` renderer structure was inspected statically. Tests use
owned DOM/CDP fixtures; a user restart and real message click are still needed to
confirm native compatibility. The reader and Paste remain available if it fails.

Validation includes Python unittests, Ruff, `pnpm test`, JS syntax and both release
builders. CI also validates installations and real offline translation on Windows
and Linux; those checks do not certify native per-message UI compatibility.
