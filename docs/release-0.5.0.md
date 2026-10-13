# TwinText 0.5.0 — Chat response and question controls (preview)

Chat settings now offer **Chat response scope**: **Final answers only** (default)
or **All responses (including progress updates)**. Final answers are the completed
answers below Codex's working/progress area. Tool results and hidden reasoning
are excluded in both scopes.

**Translate questions in chat** is enabled by default and independent of response
scope. It covers clarification/choice questions in the conversation and question
cards, including their answer choices. Turning it off leaves questions untranslated
even with All responses selected. Pausing translation overrides both controls.

Both settings are available in the embedded/standalone settings page, native
floating reader preferences, CLI and MCP. CLI examples:

```text
twintext settings --response-scope final --translate-questions true
twintext settings --response-scope all --translate-questions false
```

Upgrades preserve existing languages, display mode, provider, models and cache;
missing new settings use the defaults above. The controls apply to Chat only.
Desktop continues to display completed final replies in its separate window.

Automatic Chat translation works through Codex's hook/tool instructions, rather
than changing the native renderer. Question IDs and schemas remain intact. Short
question fields use concise translated labels when bilingual text cannot fit;
question titles/descriptions retain bilingual text where the host permits it.
Start a new Codex chat after updating. Chat translation uses ordinary Codex
tool/context/output tokens, including translated questions and progress updates
when selected. Offline translation remains local; Azure remains opt-in.

Four source-and-installer archives and SHA-256 checksums are published by the
existing Windows/Linux release workflow after regressions and installation smoke
checks pass. Download the Windows or Linux Chat/Desktop ZIP, verify its checksum,
extract it, and run the matching installer. Existing models are preserved.
Requirements remain 64-bit Python 3.10–3.13, with pip/venv and internet during setup.
