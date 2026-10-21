"""Opt-in message buttons through a loopback-only Codex debugging connection.

No remote page targets, clipboard access, application patching or source logging.
Only explicit button events enter the existing reader's translation queue.
"""

import json
import queue
import re
import secrets
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from websocket import WebSocketTimeoutException, create_connection

from twintext.config import TwinTextError
from twintext.service import MAX_TEXT_LENGTH

PORT = 9223
MAX_BYTES = 1_100_000


def app_page(url):
    parsed = urlsplit(url)
    return (parsed.scheme == "app" and parsed.netloc == "-"
            and parsed.path in ("/", "/index.html")
            and parse_qs(parsed.query).get("window") != ["page"])


def valid_target(target):
    try:
        if (not isinstance(target, dict) or target.get("type") != "page"
                or not app_page(target.get("url", ""))):
            return False
        parsed = urlsplit(target.get("webSocketDebuggerUrl", ""))
        return bool(parsed.scheme == "ws" and parsed.hostname == "127.0.0.1"
                    and parsed.port == PORT and not parsed.username and not parsed.password
                    and not parsed.query and not parsed.fragment
                    and re.fullmatch(r"/devtools/page/[\w-]{1,80}", parsed.path))
    except (TypeError, ValueError):
        return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def read_targets():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(f"http://127.0.0.1:{PORT}/json/list", timeout=2) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise TwinTextError("Codex debugging response is too large.")
    value = json.loads(raw)
    if not isinstance(value, list):
        raise TwinTextError("Codex debugging response is not a target list.")
    return value


def discover():
    candidates = [target for target in read_targets() if valid_target(target)]
    return candidates[0]["webSocketDebuggerUrl"] if len(candidates) == 1 else None


class CDPSession:
    def __init__(self, socket, events, language):
        self.socket = socket
        self.events = events
        self.language = language
        self.nonce = secrets.token_hex(16)
        self.binding = "__twintextClick_" + self.nonce
        self.serial = 0
        self.contexts = set()
        self.frame = None
        self.script = None
        self.rejected = queue.Queue(maxsize=16)

    def emit(self, value):
        if value.get("action") == "reset":
            while True:
                try:
                    self.events.get_nowait()
                except queue.Empty:
                    break
        try:
            self.events.put_nowait(value)
            return True
        except queue.Full:
            return False

    def event(self, value):
        method, params = value.get("method"), value.get("params", {})
        if method == "Runtime.executionContextCreated":
            context = params.get("context", {})
            auxiliary = context.get("auxData", {})
            if (context.get("origin") == "app://-" and auxiliary.get("isDefault") is True
                    and auxiliary.get("frameId") == self.frame):
                self.contexts.add(context.get("id"))
        elif method == "Runtime.executionContextDestroyed":
            if params.get("executionContextId") in self.contexts:
                self.contexts.discard(params["executionContextId"])
                self.emit({"action": "reset"})
        elif method == "Runtime.executionContextsCleared":
            self.contexts.clear()
            self.emit({"action": "reset"})
        elif method == "Page.frameNavigated":
            frame = params.get("frame", {})
            if not frame.get("parentId"):
                self.frame = frame.get("id") if app_page(frame.get("url", "")) else None
                self.contexts.clear()
                self.emit({"action": "reset"})
        elif (method == "Runtime.bindingCalled" and params.get("name") == self.binding
              and params.get("executionContextId") in self.contexts):
            raw = params.get("payload")
            if not isinstance(raw, str) or len(raw) > MAX_BYTES:
                return
            try:
                payload = json.loads(raw)
            except ValueError:
                return
            if not self.valid_click(payload):
                return
            if not self.emit(payload):
                # Never nest a command/recv loop inside event handling: it could
                # consume the response awaited by the outer command.
                self.rejected.put_nowait({key: payload[key] for key in ("document", "request")})

    def valid_click(self, value):
        if not isinstance(value, dict):
            return False
        identity = (value.get("session"), value.get("message"), value.get("document"))
        text = value.get("text")
        return (all(isinstance(item, str) and item.strip() and len(item) <= 256
                    for item in identity)
                and value["document"].startswith(self.nonce + ":")
                and type(value.get("request")) is int and 0 < value["request"] < 2**53
                and value.get("action") in ("translate", "original")
                and isinstance(text, str) and bool(text.strip()) and len(text) <= MAX_TEXT_LENGTH)

    def read(self):
        try:
            raw = self.socket.recv()
        except WebSocketTimeoutException:
            return None
        if not raw or len(raw) > MAX_BYTES:
            raise TwinTextError("Codex debugging connection closed or returned too much data.")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise TwinTextError("Invalid Codex debugging response.")
        self.event(value)
        return value

    def command(self, method, params=None):
        self.serial += 1
        serial = self.serial
        self.socket.send(json.dumps({"id": serial, "method": method, "params": params or {}}))
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            value = self.read()
            if value and value.get("id") == serial:
                if "error" in value:
                    raise TwinTextError("Codex rejected the optional interface adapter.")
                return value.get("result", {})
        raise TwinTextError("Codex debugging request timed out.")

    def install(self):
        self.command("Page.enable")
        frame = self.command("Page.getFrameTree")["frameTree"]["frame"]
        if not app_page(frame.get("url", "")):
            raise TwinTextError("The selected page is not the Codex main window.")
        self.frame = frame["id"]
        self.command("Runtime.enable")
        self.command("Runtime.addBinding", {"name": self.binding})
        config = json.dumps({"binding": self.binding, "language": self.language})
        adapter = (Path(__file__).parent / "web/message-buttons.js").read_text(encoding="utf-8")
        source = (
            "(() => { if (window.top !== window || location.origin !== 'app://-') return;"
            f"window.TWINTEXT_MESSAGE_CONFIG = {config};"
            f"window.TWINTEXT_MESSAGE_CONFIG.document = '{self.nonce}:' + crypto.randomUUID();"
            + adapter + "})();"
        )
        self.script = self.command("Page.addScriptToEvaluateOnNewDocument", {"source": source})[
            "identifier"
        ]
        result = self.command("Runtime.evaluate", {"expression": source, "returnByValue": True})
        if "exceptionDetails" in result:
            raise TwinTextError("This Codex renderer cannot load TwinText message buttons.")

    def feedback(self, request, state):
        if not str(request.get("document", "")).startswith(self.nonce + ":"):
            return
        value = {"document": request["document"], "request": request["request"], "state": state}
        self.command("Runtime.evaluate", {
            "expression": f"window.__twintextMessages?.feedback({json.dumps(value)})",
        })

    def cleanup(self):
        try:
            self.command("Runtime.evaluate", {"expression": (
                f"if (window.TWINTEXT_MESSAGE_CONFIG?.binding === '{self.binding}') "
                "window.__twintextMessages?.stop()"
            )})
            if self.script:
                self.command("Page.removeScriptToEvaluateOnNewDocument", {
                    "identifier": self.script,
                })
            self.command("Runtime.removeBinding", {"name": self.binding})
        except Exception:
            pass  # The app may have closed. Never log source text or debugger payloads.


class MessageAdapter:
    def __init__(self, language):
        self.language = language
        self.events = queue.Queue(maxsize=8)
        self.responses = queue.Queue(maxsize=16)
        self.stopping = threading.Event()
        self.status = "buttons_waiting"
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def feedback(self, request, state):
        if request:
            try:
                self.responses.put_nowait((request, state))
            except queue.Full:
                pass

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=2)

    def run(self):
        while not self.stopping.is_set():
            socket = session = None
            try:
                url = discover()
                if url:
                    socket = create_connection(
                        url, timeout=0.5, suppress_origin=True,
                        http_no_proxy=["127.0.0.1"], enable_multithread=True,
                    )
                    session = CDPSession(socket, self.events, self.language)
                    session.install()
                    self.status = "buttons_connected"
                    while not self.stopping.is_set():
                        while not session.rejected.empty():
                            session.feedback(session.rejected.get_nowait(), "error")
                        while not self.responses.empty():
                            request, state = self.responses.get_nowait()
                            session.feedback(request, state)
                        session.read()
            except Exception:
                pass  # Unavailable debugging must never break the reader.
            finally:
                self.status = "buttons_waiting"
                if session:
                    session.cleanup()
                    session.emit({"action": "reset"})
                if socket:
                    socket.close()
            self.stopping.wait(3)
