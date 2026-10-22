import io
import json
import os
import socket
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from twintext.config import TwinTextError, load_settings, update_settings
from twintext.service import Service


class GoogleFreeTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        environment = patch.dict(os.environ, {"TWINTEXT_HOME": folder.name})
        environment.start()
        self.addCleanup(environment.stop)

    def engine(self, values=None):
        from twintext.google_free import GoogleFreeEngine

        values = iter(values or [b'[[["Hello","original"],[" world","source"]],null,"en"]'])
        self.sent = []
        self.delays = []

        def send(request, timeout):
            self.sent.append((request, timeout))
            value = next(values)
            if isinstance(value, Exception):
                raise value
            return io.BytesIO(value)

        engine = GoogleFreeEngine(opener=send)
        engine.pause = lambda delay, cancel: self.delays.append(delay)
        return engine

    def test_request_encoding_and_only_translation_segments(self):
        engine = self.engine()
        self.assertEqual(engine.translate("中文 & + ?\n😀", "auto", "zh-TW"), "Hello world")
        request, timeout = self.sent[0]
        query = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(query, {"client": ["gtx"], "sl": ["auto"], "tl": ["zh-TW"],
                                 "dt": ["t"], "q": ["中文 & + ?\n😀"]})
        self.assertEqual(timeout, 15)
        self.assertEqual(request.get_method(), "GET")
        self.assertNotIn("Authorization", request.headers)

    def test_language_mapping(self):
        from twintext.google_free import google_language

        for value, expected in {"auto": "auto", "zh": "zh-CN", "zh-CN": "zh-CN",
                                "zh-Hans": "zh-CN", "zh-TW": "zh-TW",
                                "zh-Hant": "zh-TW", "en": "en", "fr": "fr"}.items():
            self.assertEqual(google_language(value), expected)
        with self.assertRaises(TwinTextError):
            google_language("untrusted&tl=en")

    def test_empty_identity_and_invalid_responses(self):
        engine = self.engine()
        self.assertEqual(engine.translate(" \n", "en", "fr"), " \n")
        self.assertEqual(engine.translate("Hello", "en", "en"), "Hello")
        self.assertEqual(self.sent, [])
        for value in [b'{}', b'[]', b'[null]', b'[[[null,"romanized"]]]',
                      b'[[[123,"source"]]]', b'[[["","source"]]]', b'not JSON',
                      b'[[["Good","source"],null]]', b'[[["Good","source"],"bad"]]']:
            with self.subTest(value=value), self.assertRaisesRegex(TwinTextError, "response"):
                self.engine([value]).translate("Hello", "en", "fr")

    def test_encoded_url_chunking_preserves_text_and_boundaries(self):
        from twintext.google_free import google_chunks, google_url

        text = ("Sentence one. 中文😀 & next sentence!\n" * 200)
        chunks = list(google_chunks(text, "en", "zh"))
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(google_url(c, "en", "zh")) <= 1800 for c in chunks))
        engine = self.engine([json.dumps([[[str(i), c]]]).encode()
                              for i, c in enumerate(chunks)])
        result = engine.translate(text, "en", "zh")
        self.assertEqual(result.replace(" ", "").replace("\n", ""),
                         "".join(map(str, range(len(chunks)))))
        sent_chunks = [parse_qs(urlsplit(r.full_url).query)["q"][0] for r, _ in self.sent]
        self.assertEqual(sent_chunks, chunks)

    def test_trimmed_remote_chunks_preserve_original_boundary_whitespace(self):
        from twintext.google_free import google_chunks

        text = ("bonjour " * 400).strip()
        chunks = list(google_chunks(text, "fr", "en"))
        engine = self.engine([json.dumps([[[chunk.strip()]]]).encode() for chunk in chunks])
        self.assertEqual(engine.translate(text, "fr", "en"), text)

    def test_stdio_processes_cancellation_during_running_translation(self):
        import sys
        from types import SimpleNamespace

        from twintext.mcp import serve

        entered = threading.Event()
        frames = [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "twintext_translate", "arguments": {"text": "Hello"}}},
            {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}},
        ]

        class Input:
            index = 0

            def readline(self, maximum):
                if self.index == 1:
                    entered.wait(2)
                if self.index >= len(frames):
                    return b""
                line = json.dumps(frames[self.index]).encode() + b"\n"
                self.index += 1
                return line

        def translate(text, cancel=None):
            entered.set()
            self.assertIsNotNone(cancel)
            self.assertTrue(cancel.wait(2), "stdin must remain responsive during translation")
            raise TwinTextError("Translation cancelled.")

        output = io.StringIO()
        service = SimpleNamespace(translate=translate)
        with patch.object(sys, "stdin", SimpleNamespace(buffer=Input())), \
                patch.object(sys, "stdout", output), \
                patch("twintext.mcp.Service", return_value=service):
            serve()
        result = json.loads(output.getvalue())["result"]
        self.assertTrue(result["isError"])
        self.assertIn("cancelled", result["content"][0]["text"])

    def test_retry_after_backoff_and_limit(self):
        def error(code, headers=None):
            return HTTPError("https://example", code, "private text", headers or {}, io.BytesIO())

        engine = self.engine([error(429, {"Retry-After": "3"}), error(503), b'[[["OK"]]]'])
        self.assertEqual(engine.translate("Hello", "en", "fr"), "OK")
        self.assertEqual(self.delays, [3, 2])
        engine = self.engine([error(429), error(429), error(429)])
        with self.assertRaisesRegex(TwinTextError, "rate limit"):
            engine.translate("Hello", "en", "fr")
        self.assertEqual(len(self.sent), 3)
        self.assertEqual(self.delays, [1, 2])
        for code in (400, 401, 403, 404, 302, 501):
            engine = self.engine([error(code)])
            with self.assertRaises(TwinTextError) as caught:
                engine.translate("Hello", "en", "fr")
            self.assertNotIn("private text", str(caught.exception))
            self.assertEqual(len(self.sent), 1)

    def test_timeout_transient_network_and_cancel(self):
        for error in (TimeoutError(), URLError(TimeoutError()), URLError("temporary")):
            engine = self.engine([error, error, error])
            with self.assertRaises(TwinTextError):
                engine.translate("Hello", "en", "fr")
            self.assertEqual(len(self.sent), 3)
        cancel = threading.Event()
        cancel.set()
        engine = self.engine()
        with self.assertRaisesRegex(TwinTextError, "cancelled"):
            engine.translate("Hello", "en", "fr", cancel)
        self.assertEqual(self.sent, [])
        cancel.clear()
        engine = self.engine([HTTPError("x", 429, "", {}, io.BytesIO())])
        engine.pause = lambda *_: cancel.set()
        with self.assertRaisesRegex(TwinTextError, "cancelled"):
            engine.translate("Hello", "en", "fr", cancel)
        self.assertEqual(len(self.sent), 1)

    def test_retry_after_http_date(self):
        from twintext.google_free import retry_after

        with patch("twintext.google_free.time.time", return_value=0):
            self.assertEqual(retry_after("Thu, 01 Jan 1970 00:00:05 GMT"), 5)
        self.assertEqual(retry_after("not a date"), 0)
        self.assertEqual(retry_after("-5"), 0)
        self.assertEqual(retry_after("Infinity"), 0)

    def test_page_disconnect_cancels_waits_and_remaining_fragments(self):
        from twintext.ui import ConnectionCancellation

        server, client = socket.socketpair()
        self.addCleanup(server.close)
        self.addCleanup(client.close)
        cancel = ConnectionCancellation(server)
        self.assertFalse(cancel.is_set())
        self.assertFalse(cancel.wait(0.001))
        client.close()
        self.assertTrue(cancel.is_set())
        self.assertTrue(cancel.wait(10))
        with self.assertRaisesRegex(TwinTextError, "cancelled"):
            self.engine().translate("Hello", "en", "fr", cancel)
        self.assertEqual(self.sent, [])

    def test_mcp_and_cli_save_restore_without_touching_default_or_model_pack(self):
        import subprocess
        import sys

        from twintext.engine import STARTER_PAIRS
        from twintext.mcp import call_tool

        self.assertEqual(load_settings().provider, "offline")
        self.assertEqual(len(STARTER_PAIRS), 8)
        result = call_tool("twintext_set_settings", {"provider": "google-free",
                                                   "target": "zh-TW"}, Service())
        self.assertEqual(result["settings"]["target"], "zh-TW")
        self.assertFalse(result["offline"])
        output = subprocess.check_output(
            [sys.executable, "-B", "-m", "twintext.cli", "settings"], text=True,
        )
        self.assertEqual(json.loads(output)["provider"], "google-free")
        with self.assertRaisesRegex(TwinTextError, "Traditional"):
            update_settings(provider="offline")
        self.assertEqual(load_settings().provider, "google-free")

    def test_ssl_errors_are_not_retried_and_cancellation_interrupts_backoff(self):
        import ssl

        engine = self.engine([URLError(ssl.SSLCertVerificationError("private"))])
        with self.assertRaisesRegex(TwinTextError, "network"):
            engine.translate("Hello", "en", "fr")
        self.assertEqual(len(self.sent), 1)
        cancel = threading.Event()
        cancel.set()
        with self.assertRaisesRegex(TwinTextError, "cancelled"):
            type(engine).pause(100, cancel)

    def test_serial_requests_and_cancellable_lock_wait(self):
        from twintext.google_free import GoogleFreeEngine

        entered, release, done = threading.Event(), threading.Event(), threading.Event()
        errors = []

        def send(*a, **k):
            entered.set()
            release.wait(3)
            return io.BytesIO(b'[[["OK"]]]')

        first = threading.Thread(target=lambda: GoogleFreeEngine(send).translate("A", "en", "fr"))
        first.start()
        self.assertTrue(entered.wait(2))
        cancel = threading.Event()
        blocked = Mock()

        def waiting():
            try:
                GoogleFreeEngine(blocked).translate("B", "en", "fr", cancel)
            except TwinTextError as exc:
                errors.append(str(exc))
            finally:
                done.set()

        second = threading.Thread(target=waiting)
        second.start()
        cancel.set()
        try:
            self.assertTrue(done.wait(2))
            blocked.assert_not_called()
            self.assertIn("cancelled", errors[0])
        finally:
            release.set()
            first.join(3)
            second.join(3)

    def test_service_auto_paragraphs_cache_and_setting_restore(self):
        update_settings(provider="google-free", source="auto", target="zh-TW")
        self.assertEqual(load_settings().provider, "google-free")
        engine = self.engine([b'[[["Batch markers were removed"]]]',
                              b'[[["First translated"]]]', b'[[["Second translated"]]]'])
        service = Service(engine, detector=lambda _: self.fail("Google auto must reach provider"))
        result = service.translate("First paragraph.\n\nSecond paragraph.")
        self.assertEqual(result["original"], "First paragraph.\n\nSecond paragraph.")
        self.assertEqual(result["translation"], "First translated\n\nSecond translated")
        self.assertEqual(len(self.sent), 3)
        service.translate(result["original"])
        self.assertEqual(len(self.sent), 3)
        update_settings(provider="offline", target="zh")
        self.assertEqual(load_settings().provider, "offline")
        self.assertNotIn("Offline translation stays", self._google_context())

    def _google_context(self):
        from twintext.service import context

        update_settings(provider="google-free", workflow="chat")
        return context()

    def test_cancel_stops_remaining_chunks_and_no_cache_on_failure(self):
        update_settings(provider="google-free", source="en", target="fr")
        cancel = threading.Event()
        engine = self.engine()
        opener = engine.opener

        def send(*args, **kwargs):
            response = opener(*args, **kwargs)
            cancel.set()
            return response

        engine.opener = send
        with self.assertRaisesRegex(TwinTextError, "cancelled"):
            Service(engine).translate("Hello " * 600, cancel=cancel)
        self.assertEqual(len(self.sent), 1)
        cancel.clear()
        result = Service(self.engine()).translate("Hello")
        self.assertEqual(result["cache_hits"], 0)


if __name__ == "__main__":
    unittest.main()
