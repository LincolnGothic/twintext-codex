"""Settings UI served only on loopback, also bundled as an MCP App resource."""

import json
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files

from twintext.config import TwinTextError
from twintext.mcp import call_tool
from twintext.service import Service


def html(token="", embedded=False):
    root = files("twintext").joinpath("web")
    value = root.joinpath("index.html").read_text(encoding="utf-8")
    value = value.replace("{{TOKEN}}", token).replace("{{EMBEDDED}}", str(embedded).lower())
    value = value.replace("{{CSS}}", root.joinpath("style.css").read_text(encoding="utf-8"))
    return value.replace("{{JS}}", root.joinpath("app.js").read_text(encoding="utf-8"))


def create_server(port=0, service=None):
    token = secrets.token_urlsafe(32)
    service = service or Service()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Do not log user text, settings, or URLs.

        def respond(self, status, value, content_type="application/json"):
            raw = (
                value.encode("utf-8")
                if isinstance(value, str)
                else json.dumps(value, ensure_ascii=False).encode("utf-8")
            )
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; "
                f"script-src 'nonce-{token}'; style-src 'unsafe-inline'; "
                "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(raw)

        def host_allowed(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.host_allowed():
                self.respond(403, {"error": "Untrusted host"})
            elif self.path == "/":
                self.respond(200, html(token=token), "text/html")
            else:
                self.respond(404, {"error": "Not found"})

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (
                not self.host_allowed()
                or self.headers.get("X-TwinText-Token") != token
                or self.headers.get("Origin") not in (None, origin)
            ):
                self.respond(403, {"error": "Untrusted request"})
                return
            if self.path != "/api/tool":
                self.respond(404, {"error": "Not found"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 1_000_000:
                    self.respond(413, {"error": "Request must be between 1 byte and 1 MB"})
                    return
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    self.respond(415, {"error": "Send JSON"})
                    return
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise TwinTextError("Request must be an object.")
                result = call_tool(body.get("name"), body.get("arguments", {}), service)
                self.respond(200, result)
            except (TwinTextError, OSError, ValueError, TypeError, RuntimeError) as exc:
                self.respond(400, {"error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def serve(port=0, open_browser=False):
    server = create_server(port)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"TwinText settings: {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
