import io
import json
import os
import re
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from twintext.config import TwinTextError, update_settings
from twintext.google_free import GoogleFreeEngine, pack_fragments, unpack_fragments
from twintext.service import Service


def article():
    return "\n\n".join(
        f"## Topic {i}: practical example\n\n"
        f"This section describes **example {i}**, explains how a reader can inspect the result, "
        f"and discusses the implications for topic {i}.\n\n"
        f"- Use the command `example-{i} --help` to inspect the available options.\n"
        f"- Read [the documentation for topic {i}](https://example.com/topic/{i}) "
        "before changing a setting.\n\n"
        "| Item | Description | Quantity |\n| --- | --- | ---: |\n"
        f"| Sample {i} | A distinct explanation for item {i} | {i} |"
        for i in range(1, 26)
    )


class TranslationPerformanceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        environment = patch.dict(os.environ, TWINTEXT_HOME=folder.name)
        environment.start()
        self.addCleanup(environment.stop)
        update_settings(provider="google-free", source="en", target="zh")
        self.requests = []

    def engine(self, damage=False):
        def send(request, timeout):
            self.assertLessEqual(len(request.full_url), 1800)
            value = parse_qs(urlsplit(request.full_url).query)["q"][0]
            self.requests.append(value)
            output = "\n".join(line if line.startswith("__TT") else "译:" + line
                               for line in value.split("\n"))
            if damage and "__TT" in value:
                output = re.sub(r"__TT\w+__", "", output)
            return io.BytesIO(json.dumps([[[output]]]).encode())

        return GoogleFreeEngine(opener=send)

    def test_long_formatted_article_uses_fewer_requests_and_reuses_existing_cache(self):
        source = article()
        progress = []
        service = Service(self.engine())
        result = service.translate(source, progress=progress.append)
        first = len(self.requests)
        self.assertLess(first, 40, "The previous path needed 157 requests on this fixture")
        self.assertEqual(result["original"], source)
        self.assertNotIn("__TT", result["translation"])
        self.assertIn("`example-25 --help`", result["translation"])
        self.assertIn("https://example.com/topic/25", result["translation"])
        self.assertIn("| 25 |", result["translation"])
        self.assertTrue(all("example-25 --help" not in value for value in self.requests))
        self.assertTrue(all("https://example.com" not in value for value in self.requests))
        self.assertGreaterEqual(len(progress), 1)
        self.assertFalse(progress[0]["complete"])
        self.assertIn("Topic 25", progress[0]["translation"], "Pending source stays visible")
        self.assertTrue(result["complete"])
        repeated = service.translate(source)
        self.assertEqual(len(self.requests), first)
        self.assertGreater(repeated["cache_hits"], 0)

    def test_marker_damage_falls_back_once_without_mixing_fragments(self):
        engine = self.engine(damage=True)
        texts = ["First text", "Second text", "Third text"]
        self.assertEqual(list(engine.iter_translations(texts, "en", "zh")),
                         list(enumerate("译:" + text for text in texts)))
        self.assertEqual(len(self.requests), 4)
        self.assertFalse(engine.batching)
        list(engine.iter_translations(texts, "en", "zh"))
        self.assertEqual(len(self.requests), 7, "Do not repeat a failed batch probe")

    def test_batch_mapping_rejects_reordered_duplicate_missing_and_empty_boundaries(self):
        packed, markers = pack_fragments(["First", "Second"], "abcdef")
        self.assertEqual(unpack_fragments(packed, markers), ["First", "Second"])
        for bad in (packed.replace(markers[1], markers[0]),
                    packed.replace(markers[1], ""),
                    packed.replace("First", ""), "prefix" + packed, packed + "suffix",
                    packed.replace(markers[0], "TEMP").replace(markers[2], markers[0])
                    .replace("TEMP", markers[2])):
            self.assertIsNone(unpack_fragments(bad, markers))

    def test_unicode_and_long_individual_fragments_keep_the_url_budget(self):
        texts = ["中文😀 " * 300, *[f"Short fragment {i}" for i in range(40)]]
        output = list(self.engine().iter_translations(texts, "en", "zh"))
        self.assertEqual([index for index, _ in output], list(range(len(texts))))
        self.assertTrue(all(value.strip() for _, value in output))

    def test_cancel_after_partial_output_stops_the_remaining_work(self):
        cancel = threading.Event()
        progress = []

        def report(value):
            progress.append(value)
            cancel.set()

        with self.assertRaisesRegex(TwinTextError, "cancelled"):
            Service(self.engine()).translate(article(), cancel=cancel, progress=report)
        self.assertEqual(len(progress), 1)
        self.assertFalse(progress[0]["complete"])
        self.assertEqual(len(self.requests), 1)

    def test_partial_translation_does_not_duplicate_bilingual_code_blocks(self):
        source = "First paragraph.\n\n```sh\nnpm test\n```\n\nSecond paragraph."
        progress = []
        final = Service(self.engine()).translate(source, mode="bilingual", progress=progress.append)
        for result in [*progress, final]:
            self.assertEqual(result["original"], source)
            self.assertEqual(result["display"].count("npm test"), 1)
            self.assertIn("```sh\nnpm test\n```", result["translation"])

    def test_worker_exposes_latest_progress_before_the_final_result(self):
        from twintext.desktop import Translator

        entered, release = threading.Event(), threading.Event()

        class StreamingService:
            def translate(self, text, *, progress, **kwargs):
                progress({"first": True})
                progress({"latest": True})
                entered.set()
                release.wait(2)
                return {"complete": True}

        worker = Translator(service=StreamingService())
        self.addCleanup(release.set)
        worker.submit(7, "Public fixture", "en", "zh")
        self.assertTrue(entered.wait(2))
        self.assertTrue(worker.results.empty(), "Progress must arrive before completion")
        self.assertEqual(worker.progress.qsize(), 1, "Do not retain obsolete full-text previews")
        self.assertEqual(worker.progress.get_nowait(), (7, {"latest": True}))
        release.set()
        self.assertEqual(worker.results.get(timeout=2), (7, {"complete": True}, None))


if __name__ == "__main__":
    unittest.main()
