import os
import ssl
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

import httpx

from twintext.config import TwinTextError
from twintext.google_free import GoogleFreeEngine
from twintext.google_transport import GoogleTransport


class GoogleTransportTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        environment = patch.dict(os.environ, TWINTEXT_HOME=folder.name)
        environment.start()
        self.addCleanup(environment.stop)

    def test_connections_are_reused_without_cookies_or_redirects(self):
        clients, paths, cookies = set(), [], []

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                pass

            def do_GET(self):
                clients.add(self.client_address)
                paths.append(self.path)
                cookies.append(self.headers.get("Cookie"))
                self.send_response(302 if self.path == "/redirect" else 200)
                self.send_header("Content-Length", "2")
                self.send_header("Set-Cookie", "tracking=fixture")
                self.send_header("Location", "/must-not-follow")
                self.end_headers()
                self.wfile.write(b"OK")

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        transport = GoogleTransport()
        self.addCleanup(transport.close)
        factory = httpx.Client

        def client(**kwargs):
            kwargs.update(trust_env=False, proxy=None)
            return factory(**kwargs)

        with patch("twintext.google_transport.httpx.Client", side_effect=client):
            root = f"http://127.0.0.1:{server.server_port}"
            for path in ("/first", "/second"):
                with transport.open(Request(root + path), timeout=2) as response:
                    self.assertEqual(response.read(10), b"OK")
            with self.assertRaises(HTTPError) as caught:
                with transport.open(Request(root + "/redirect"), timeout=2):
                    self.fail("Redirect was accepted")
        self.assertEqual(caught.exception.code, 302)
        self.assertEqual(len(clients), 1, "Subsequent requests must share the connection")
        self.assertEqual(paths, ["/first", "/second", "/redirect"])
        self.assertEqual(cookies, [None, None, None])

    def test_system_proxy_and_trusted_certificates_are_retained(self):
        factory = httpx.Client
        seen = []

        def client(**kwargs):
            seen.append(kwargs)
            return factory(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=b'[[["OK"]]]')), trust_env=False)

        engine = GoogleFreeEngine()
        self.addCleanup(engine.close)
        with (patch("twintext.google_transport.getproxies", return_value={
                  "https": "http://127.0.0.1:8123", "all": "socks://127.0.0.1:8124"}),
              patch("twintext.google_transport.proxy_bypass", return_value=False),
              patch("twintext.google_transport.httpx.Client", side_effect=client)):
            self.assertEqual(engine.translate("Public fixture", "en", "zh"), "OK")
        self.assertEqual(seen[0]["proxy"], "http://127.0.0.1:8123")
        self.assertFalse(seen[0]["follow_redirects"])
        self.assertEqual(seen[0]["verify"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(seen[0]["verify"].check_hostname)

    def test_http_status_reaches_existing_retry_and_rate_limit_handling(self):
        factory = httpx.Client
        calls = []

        def send(request):
            calls.append(request)
            return (httpx.Response(429, headers={"Retry-After": "4"}) if len(calls) == 1
                    else httpx.Response(200, content=b'[[["OK"]]]'))

        engine = GoogleFreeEngine()
        self.addCleanup(engine.close)
        delays = []
        engine.pause = lambda seconds, cancel: delays.append(seconds)
        with patch("twintext.google_transport.httpx.Client", return_value=factory(
                transport=httpx.MockTransport(send), trust_env=False)):
            self.assertEqual(engine.translate("Public fixture", "en", "zh"), "OK")
        self.assertEqual(delays, [4])
        self.assertEqual(len(calls), 2)

    def test_decompressed_response_limit_is_enforced(self):
        factory = httpx.Client
        consumed = []

        class Body(httpx.SyncByteStream):
            closed = False

            def __iter__(self):
                for _ in range(100):
                    consumed.append(1)
                    yield b"x" * 65536

            def close(self):
                self.closed = True

        body = Body()
        engine = GoogleFreeEngine()
        self.addCleanup(engine.close)
        with patch("twintext.google_transport.httpx.Client", return_value=factory(
                transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=body)),
                trust_env=False)):
            with self.assertRaisesRegex(TwinTextError, "response"):
                engine.translate("Public fixture", "en", "zh")
        self.assertLess(len(consumed), 40)
        self.assertTrue(body.closed)


if __name__ == "__main__":
    unittest.main()
