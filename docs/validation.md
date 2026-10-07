# v0.1.0 validation

Validated on Linux x86-64 with Python 3.12, Argos Translate 1.11.0 and CPU CTranslate2 on October 7, 2026.

- **27 unit and integration checks passed:** Markdown protection, settings, cache invalidation, model routing, runaway decoding, MCP stdio framing and error handling, loopback access controls, hook launcher output, and preservation of existing marketplace entries.
- **All 20 directed language pairs passed real-model smoke checks** using the eight starter models. Python socket connection and DNS functions were disabled during inference. The checks require nonempty translated output and preservation of inline code and code fences. [Sample results](model-smoke.json) are included for inspection.
- **Browser checks passed:** French-to-English preview, bilingual and translated-only modes, all five interface languages, and an English target remaining unchanged while the UI language changes. [Screenshot](settings.jpg).
- Portable `plugin.json` and `mcp.json` validated against their official Agent Plugins 1.0.0 JSON schemas. The skill validator, Ruff, JavaScript syntax and installer shell syntax checks passed.
- Built a Python wheel and confirmed that it contains the HTML, CSS and JavaScript settings assets. Installed Python dependencies passed `pip check`.

The Spanish-to-English BPE model produced repetitive output with int8 and automatic CPU computation in this environment. Explicit float32 computation produced normal output. TwinText uses float32 and rejects decoding that reaches its input-dependent token limit rather than returning a potentially incomplete or repeated translation. This policy also participates in cache keys.

These checks do not establish human translation quality or test every passage. Non-English pairs pivot through English. Live installation, hook trust and embedded MCP App rendering inside a specific Codex desktop build still need verification after the user enables the plugin. The standalone UI and hook process were tested; native chat behavior remains instruction-driven. ARM Linux was not tested here.
