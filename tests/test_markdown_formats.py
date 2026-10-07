"""Visible-text coverage and source-preservation regressions across reply formats."""

import os
import tempfile
import unittest
from unittest.mock import patch

from markdown_it import MarkdownIt
from test_core import FakeEngine

from twintext.config import update_settings
from twintext.markdown import blocks, prose
from twintext.service import Service

TABLE = (
    "| Item | Description | Quantity |\n"
    "| :--- | --- | ---: |\n"
    "| Apples | Fresh red apples | 5 |\n"
    "| Bread | Whole wheat loaf | 2 |\n"
    "| Milk | One-liter bottle | 1 |\n"
)


class MarkdownFormatTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        env = patch.dict(os.environ, {"TWINTEXT_HOME": directory.name})
        env.start()
        self.addCleanup(env.stop)
        update_settings(target="zh", cache=False)
        self.engine = FakeEngine()
        self.service = Service(self.engine, detector=lambda text: "en")

    def test_reported_table_translates_headers_and_cells_in_both_modes(self):
        for mode in ("bilingual", "translated"):
            with self.subTest(mode=mode):
                result = self.service.translate(TABLE, mode=mode)
                self.assertIn("| 译:Item | 译:Description | 数量 |", result["display"])
                self.assertIn("| 译:Apples | 译:Fresh red apples | 5 |", result["display"])
                self.assertEqual(result["original"], TABLE)
                self.assertEqual(
                    result["display"].count("| :--- | --- | ---: |"),
                    2 if mode == "bilingual" else 1,
                )
                tokens = MarkdownIt("commonmark").enable("table").parse(result["display"])
                self.assertEqual(
                    sum(t.type == "table_open" for t in tokens), 2 if mode == "bilingual" else 1
                )
                self.assertNotIn("5", self.engine.calls)

    def test_table_variants_keep_alignment_and_protected_cell_values(self):
        for text in (
            "Name | Value\n:--- | ---:\nBread | 2\n",
            "| Title |\n| --- |\n| Hello |\n",
            "> | Name | Value |\n> | --- | --- |\n> | Bread | 2 |\n",
            "| Name | Value |\r\n| --- | --- |\r\n| Bread | 2 |\r\n",
            "| Name | Value |\n| --- | --- |\n| A\\|B | `x\\|y` |\n",
            "| Name | Value |\n| --- | --- |\n| **Bread** | [Read](https://x.test/a_(b)) |",
        ):
            with self.subTest(text=text):
                result = self.service.translate(text, mode="translated")
                self.assertEqual("".join(b.original for b in blocks(text)), text)
                self.assertIn("译:", result["translation"])
                before = MarkdownIt("commonmark").enable("table").parse(text)
                after = MarkdownIt("commonmark").enable("table").parse(result["translation"])

                def signature(tokens):
                    return [t.type for t in tokens if t.type != "inline"]

                self.assertEqual(signature(before), signature(after))
                self.assertTrue(all("x\\|y" not in call for call in self.engine.calls))

    def test_model_created_pipe_and_newline_cannot_break_table_shape(self):
        self.engine.translate = lambda *args: "中文|内容\n下一行"
        value = self.service.translate(TABLE, mode="translated")["translation"]
        self.assertIn(r"中文\|内容 下一行", value)
        tokens = MarkdownIt("commonmark").enable("table").parse(value)
        self.assertEqual(sum(t.type == "th_open" for t in tokens), 3)
        self.assertEqual(sum(t.type == "td_open" for t in tokens), 9)

    def test_quantity_glossary_is_limited_to_header_and_handles_all_five_languages(self):
        names = {"en": "Quantity", "zh": "数量", "ja": "数量", "fr": "Quantité", "es": "Cantidad"}
        for source, name in names.items():
            for target, translated in names.items():
                if source == target:
                    continue
                with self.subTest(source=source, target=target):
                    text = f"| {name} |\n| --- |\n| {name} |\n"
                    value = self.service.translate(
                        text, source=source, target=target, mode="translated"
                    )["translation"]
                    self.assertEqual(value, f"| {translated} |\n| --- |\n| 译:{name} |\n")

    def test_prose_structures_translate_without_losing_markers(self):
        cases = [
            ("## Heading ##\n", "## 译:Heading ##"),
            ("Heading\n=======\n", "译:Heading\n======="),
            ("Heading\n-------\n", "译:Heading\n-------"),
            ("- First\n    - Child\n        - Grandchild\n", "        - 译:Grandchild"),
            ("1. First\n   2. Second\n", "   2. 译:Second"),
            ("- [ ] Pending\n- [x] Finished\n", "- [x] 译:Finished"),
            ("> [!NOTE]\n> Read carefully\n", "> 译:Read carefully"),
            ("> > Nested quotation\n", "> > 译:Nested quotation"),
            ("**Strong** and *emphasis* with ~~removed~~.\n", "**译:Strong**"),
            ("Text[^1]\n\n[^1]: More details.\n", "[^1]: 译:More details."),
            ("Hello 😀\n世界\n", "译:Hello 😀"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                result = self.service.translate(text, mode="translated")
                self.assertIn(expected, result["translation"])
                self.assertEqual(result["original"], text)
                self.assertEqual(self.service.translate(text, mode="original")["display"], text)

    def test_link_labels_translate_without_changing_destinations_or_reference_ids(self):
        text = (
            '[Read **guide**](https://example.com/a_(b) "Original title")\n'
            "[Details][docs] and [Manual][] and [Manual].\n"
            "![Screenshot](https://example.com/image.png)\n\n"
            '[docs]: https://example.com/docs "Title"\n'
            "[Manual]: https://example.com/manual\n"
        )
        value = self.service.translate(text, mode="translated")["translation"]
        self.assertIn('[译:Read **译:guide**](https://example.com/a_(b) "Original title")', value)
        self.assertIn("[译:Details][docs]", value)
        self.assertEqual(value.count("[译:Manual][Manual]"), 2)
        self.assertIn("![译:Screenshot](https://example.com/image.png)", value)
        self.assertIn('[docs]: https://example.com/docs "Title"', value)
        self.assertTrue(
            all(
                "https://" not in call and "Original title" not in call
                for call in self.engine.calls
            )
        )

    def test_code_math_html_diagrams_and_app_directives_are_never_sent_to_model(self):
        protected = [
            '```json\n{"message": "Hello"}\n```\n',
            "~~~mermaid\ngraph LR; A[Hello] --> B[World]\n~~~\n",
            "> ```sh\n> echo hello\n> ```\n",
            "    print('hello')\n",
            "$$\nx = y + 1\n$$\n",
            "$$x = y$$\n",
            "\\[\nx = y\n\\]\n",
            "\\[x = y\\]\n",
            '<div title="Hello">World</div>\n',
            ':codex-annotation{index="1"}\n',
        ]
        for text in protected:
            with self.subTest(text=text):
                before = len(self.engine.calls)
                result = self.service.translate(text + "\nRead this.\n", mode="bilingual")
                self.assertEqual(result["display"].count(text.rstrip()), 1)
                self.assertEqual(self.engine.calls[before:], ["Read this."])
                self.assertIn("译:Read this.", result["display"])

    def test_inline_code_paths_urls_entities_and_escapes_stay_exact(self):
        tokens = [
            "``printf `hello` ``",
            "/tmp/app.py",
            r"C:\Users\test.py",
            "plugin://app/item",
            "name@example.com",
            "$x + y$",
            r"\(x + y\)",
            r"\*",
            "&amp;",
        ]
        text = "Read " + " and ".join(tokens) + ".\n"
        value = self.service.translate(text, mode="translated")["translation"]
        for token in tokens:
            self.assertIn(token, value)
            self.assertTrue(all(token not in call for call in self.engine.calls))

    def test_detection_uses_table_and_link_text_but_not_source_code(self):
        detected = []
        self.service.detector = lambda text: detected.append(text) or "en"
        self.service.translate(TABLE)
        self.assertIn("Fresh red apples", detected[-1])
        self.service.translate("[Read guide](https://example.com)\n\n```sh\nnpm test\n```\n")
        self.assertIn("Read guide", detected[-1])
        self.assertNotIn("https://", detected[-1])
        self.assertNotIn("npm test", detected[-1])
        self.assertEqual(prose("````\nprint(1)\n````\n"), "")

    def test_code_bracket_in_link_label_and_parenthesis_in_title_remain_valid(self):
        text = '[Use `a]b`](https://example.com "Title (unfinished")\n'
        value = self.service.translate(text, mode="translated")["translation"]
        self.assertEqual(value, '[译:Use `a]b`](https://example.com "Title (unfinished")\n')

    def test_currency_text_translates_without_confusing_two_prices_with_math(self):
        text = "Pay $5.00 per item and $10 shipping, or €8.50.\n"
        value = self.service.translate(text, mode="translated")["translation"]
        for price in ("$5.00", "$10", "€8.50"):
            self.assertIn(price, value)
            self.assertTrue(all(price not in call for call in self.engine.calls))
        self.assertTrue(any("per item and" in call for call in self.engine.calls))

    def test_inline_app_directive_remains_exact(self):
        directive = ':codex-annotation{index="1"}'
        text = "Read this. " + directive + "\n"
        value = self.service.translate(text, mode="translated")["translation"]
        self.assertIn(directive, value)
        self.assertTrue(all("codex-annotation" not in call for call in self.engine.calls))

    def test_file_link_labels_and_relative_paths_keep_their_identifiers(self):
        text = "Read [app.py](/tmp/app.py:12), src/app.ts, and [Instructions](/tmp/README.md).\n"
        value = self.service.translate(text, mode="translated")["translation"]
        self.assertIn("[app.py](/tmp/app.py:12)", value)
        self.assertIn("src/app.ts", value)
        self.assertIn("[译:Instructions](/tmp/README.md)", value)
        self.assertTrue(
            all("app.py" not in call and "app.ts" not in call for call in self.engine.calls)
        )

    def test_incomplete_or_malformed_markdown_preserves_source_without_crashing(self):
        for text in (
            "[Broken](https://example.com",
            "```python\nprint('unfinished')",
            "Text with `unclosed",
            "| A | B |\nnot a separator\n",
            "",
            "12345\n",
            "Hello\r\nWorld\r\n",
        ):
            with self.subTest(text=text):
                result = self.service.translate(text)
                self.assertEqual(result["original"], text)
                self.assertEqual("".join(b.original for b in blocks(text)), text)
                self.assertIsInstance(result["display"], str)


if __name__ == "__main__":
    unittest.main()
