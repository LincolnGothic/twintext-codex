# Output-format coverage in TwinText 0.3.0

Chat, Desktop, CLI and settings previews use the same Markdown translator. The
format fixes introduced in 0.2.2 are shared by both styles in 0.3.0. Desktop uses
Qt to render Markdown; Chat uses Codex's renderer, so visual layout can differ.
The shared parser tests establish structural preservation rather than identical
presentation in every host. See [validation evidence](validation.md).

| Output | Behavior | Verification |
| --- | --- | --- |
| Markdown tables | Translate headers and cells; preserve numeric cells, separators, alignment, escaped pipes and inline code. | Unit fixtures cover normal, single-column, no outer pipe, quoted, CRLF and formatted cells. Real models and Qt cover the reported shopping table in both modes. |
| Headings | Translate titles; preserve ATX markers, closing markers and setext underlines. | ATX/setext fixtures. |
| Bullet, ordered and nested lists | Translate item text without treating indented child items as code. | Nested list and numbered list fixtures. |
| Task lists | Preserve checked/unchecked states while translating labels. | Checkbox fixtures and Qt smoke output. |
| Quotes and callouts | Translate prose; preserve quote prefixes and alert identifiers. | Nested quote and NOTE fixtures. |
| Bold, italic, strikethrough | Translate visible text; preserve emphasis syntax. | Inline-format fixtures. |
| Links, references, image alt text | Translate labels; preserve URL/title/ID. Collapsed and shortcut references become explicit references to the original ID. Images still do not load. | Nested parentheses, code brackets, quoted titles and reference fixtures. |
| Footnotes | Translate single-line definition text; preserve footnote markers. | Definition/reference fixtures. Qt does not provide full scholarly footnote layout. |
| Mixed-language text, emoji, punctuation | Preserve the original and use the existing local detection/translation engine. | Structure fixtures; quality still depends on Argos and language detection. |
| Code, JSON, shell output, Mermaid/ASCII diagrams inside fences | Preserve verbatim; display once in bilingual mode. | Multiple fence types, quoted/unfinished fences and real-model code checks. |
| Inline code, paths, emails, URLs, math | Preserve these tokens and exclude them from local-model input. | Protection fixtures and real-model mixed Markdown. |
| Raw HTML blocks, reference definitions, display math, Codex directives | Preserve verbatim. | Single/multiline formulas, HTML and directive fixtures. |
| Incomplete/malformed Markdown | Preserve original source, avoid crashing; recognizable text may translate. | Malformed link/table/fence and empty/numeric fixtures. |

Bilingual tables are two complete tables, original then translated, with the same columns. Translation-only renders just the translated table. The copy action returns the same Markdown used for display. Desktop's original inbox message is never rewritten; Chat emits a new final reply rather than editing earlier messages.

Markdown block structure uses markdown-it-py; inline/source reconstruction retains original delimiters rather than serializing a parsed tree. Model-generated pipes and line breaks are escaped/flattened inside table cells so they cannot create extra rows or columns.

A small five-language offline glossary handles the table header **Quantity** (数量 / Quantité / Cantidad), since the local model misinterpreted this short English word as “termination reason” in Chinese. The glossary applies only to the header, not body cells or ordinary prose; other text uses Argos.

This coverage concerns Markdown text. It does not translate text inside screenshots, raster charts, PDFs, videos, arbitrary HTML applications, or native Codex controls. Fenced diagram identifiers are preserved rather than rewritten. Multiline footnote extensions and nonstandard Markdown may remain partly untranslated. Offline model quality is distinct from formatting correctness.
