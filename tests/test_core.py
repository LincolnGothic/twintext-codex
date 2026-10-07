import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from twintext.cache import Cache
from twintext.config import TwinTextError, load_settings, update_settings
from twintext.engine import ArgosEngine, sentence_chunks, validate_model_archive
from twintext.markdown import blocks
from twintext.service import Service, context


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.version = "v1"

    def route(self, source, target):
        return [SimpleNamespace(to_code=target)] if source != target else []

    def fingerprint(self, source, target):
        return self.version

    def translate(self, text, source, target):
        self.calls.append(text)
        return "译:" + text

    def routes(self):
        return [{"source": "en", "target": "zh", "version": "1"}]


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {"TWINTEXT_HOME": self.directory.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.engine = FakeEngine()
        self.service = Service(self.engine, detector=lambda text: "en")
        update_settings(target="zh")

    def test_preferences_default_target_and_independent_locale(self):
        Path(self.directory.name, "settings.json").unlink()
        self.assertEqual(load_settings().target, "en")
        update_settings(target="ja", ui_language="fr", mode="translated")
        self.assertEqual(load_settings().target, "ja")
        self.assertEqual(load_settings().ui_language, "fr")
        self.assertEqual(context(), "")
        update_settings(enabled=False)
        self.assertEqual(context(), "")

    def test_invalid_preferences_do_not_damage_previous_settings(self):
        with self.assertRaises(TwinTextError):
            update_settings(target="xx")
        with self.assertRaises(TwinTextError):
            update_settings(enabled="true")
        self.assertEqual(load_settings().target, "zh")
        self.assertEqual(Path(self.directory.name, "settings.json").stat().st_mode & 0o777, 0o600)

    def test_corrupt_settings_fail_explicitly(self):
        Path(self.directory.name, "settings.json").write_text("[]")
        with self.assertRaises(TwinTextError):
            load_settings()

    def test_code_links_paths_and_math_do_not_reach_the_model(self):
        text = (
            "# Hello\n\nRun `npm test` with /tmp/app.py and [docs](https://example.com).\n\n"
            "```python\nprint('hello')\n```\n\n$$\nx = y + 1\n$$\n"
        )
        result = self.service.translate(text)
        self.assertIn("# 译:Hello", result["display"])
        self.assertEqual(result["display"].count("print('hello')"), 1)
        for token in ("`npm test`", "/tmp/app.py", "[docs](https://example.com)", "x = y + 1"):
            self.assertIn(token, result["translation"])
            self.assertTrue(all(token not in call for call in self.engine.calls))

    def test_tilde_and_unclosed_fences_stay_verbatim(self):
        for text in ("~~~js\nconst a = 1;\n~~~\n", "```python\nprint('a')"):
            self.assertEqual(self.service.translate(text)["display"], text)
        self.assertFalse(blocks("````\n```\ncode\n````\n")[0].translatable)

    def test_tables_references_and_indented_code_are_preserved(self):
        text = "| A | B |\n|---|---|\n\n[docs]: https://example.com\n\n    print('a')\n"
        self.assertEqual(self.service.translate(text)["display"], text)
        self.assertFalse(self.engine.calls)

    def test_nested_inline_code_quoted_fence_and_unprefixed_table_are_preserved(self):
        text = (
            "Run ``printf `hello` `` now.\n\n> ```sh\n> npm test\n> ```\n\n"
            "Name | Value\n--- | ---\none | two\n"
        )
        result = self.service.translate(text)
        self.assertIn("``printf `hello` ``", result["translation"])
        self.assertIn("Name | Value\n--- | ---\none | two", result["translation"])
        self.assertEqual(result["display"].count("> npm test"), 1)
        self.assertTrue(
            all("printf" not in call and "npm" not in call for call in self.engine.calls)
        )

    def test_modes_identity_and_disabled_do_not_duplicate_text(self):
        self.assertEqual(self.service.translate("Hello", mode="translated")["display"], "译:Hello")
        self.assertEqual(self.service.translate("Hello", mode="original")["display"], "Hello")
        self.assertEqual(self.service.translate("Hello", target="en")["display"], "Hello")
        update_settings(enabled=False)
        self.assertEqual(context(), "")
        self.assertIn("译:Hello", self.service.translate("Hello")["display"])

    def test_cache_reuse_clear_and_model_version_invalidation(self):
        self.service.translate("Hello")
        result = self.service.translate("Hello")
        self.assertEqual(len(self.engine.calls), 1)
        self.assertEqual(result["cache_hits"], 1)
        self.engine.version = "v2"
        self.service.translate("Hello")
        self.assertEqual(len(self.engine.calls), 2)
        Cache().clear()
        self.service.translate("Hello")
        self.assertEqual(len(self.engine.calls), 3)

    def test_disabling_cache_does_not_save_results(self):
        update_settings(cache=False)
        self.service.translate("Hello")
        self.service.translate("Hello")
        self.assertEqual(len(self.engine.calls), 2)
        self.assertFalse(Path(self.directory.name, "translations.sqlite3").exists())

    def test_long_input_and_invalid_mode_fail(self):
        for kwargs in ({"text": "a" * 100001}, {"text": "Hello", "mode": "wrong"}, {"text": 123}):
            with self.assertRaises(TwinTextError):
                self.service.translate(**kwargs)

    def test_short_chunks_preserve_the_whole_input(self):
        chunks = sentence_chunks("a" * 1200)
        self.assertEqual("".join(chunks), "a" * 1200)
        self.assertTrue(all(len(chunk) <= 450 for chunk in chunks))

    def test_pivot_route_and_missing_model(self):
        engine = ArgosEngine()
        packages = [
            SimpleNamespace(from_code="ja", to_code="en"),
            SimpleNamespace(from_code="en", to_code="fr"),
        ]
        with patch.object(engine, "packages", return_value=packages):
            self.assertEqual([p.to_code for p in engine.route("ja", "fr")], ["en", "fr"])
            with self.assertRaises(TwinTextError):
                engine.route("zh", "fr")

    def test_runaway_decode_fails_instead_of_returning_repeated_text(self):
        engine = ArgosEngine()
        package = SimpleNamespace(
            tokenizer=SimpleNamespace(encode=lambda text: [text]), target_prefix=""
        )
        translator = SimpleNamespace(
            translate_batch=lambda tokens, **kwargs: [
                SimpleNamespace(hypotheses=[["loop"] * kwargs["max_decoding_length"]])
            ]
        )
        with (
            patch.object(engine, "route", return_value=[package]),
            patch.object(engine, "_model", return_value=translator),
            self.assertRaisesRegex(TwinTextError, "decoding limit"),
        ):
            engine.translate("Hello", "en", "es")

    def test_archive_traversal_is_rejected(self):
        path = Path(self.directory.name, "unsafe.argosmodel")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("../outside", "bad")
        with self.assertRaises(TwinTextError):
            validate_model_archive(path)

    def test_bilingual_prose_keeps_original_exact(self):
        text = "The first paragraph.\n\n- One item\n- Another item\n"
        result = self.service.translate(text)
        self.assertEqual(result["original"], text)
        self.assertIn("The first paragraph.\n\n译:The first paragraph.", result["display"])


if __name__ == "__main__":
    unittest.main()
