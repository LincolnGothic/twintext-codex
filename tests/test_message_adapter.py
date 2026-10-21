import json
import queue
import unittest
from unittest.mock import patch

from twintext.message_adapter import CDPSession, discover, valid_target


class Socket:
    """Protocol peer for our client, including a real main-frame context event."""
    def __init__(self):
        self.incoming = queue.SimpleQueue()
        self.sent = []

    def send(self, raw):
        call = json.loads(raw)
        self.sent.append(call)
        if call["method"] == "Runtime.enable":
            self.incoming.put(json.dumps({"method": "Runtime.executionContextCreated", "params": {
                "context": {"id": 7, "origin": "app://-", "auxData": {
                    "isDefault": True, "frameId": "main-frame"}}}}))
        result = ({"frameTree": {"frame": {"id": "main-frame", "url": "app://-/index.html"}}}
                  if call["method"] == "Page.getFrameTree" else
                  {"identifier": "installed-script"}
                  if call["method"] == "Page.addScriptToEvaluateOnNewDocument" else {})
        self.incoming.put(json.dumps({"id": call["id"], "result": result}))

    def recv(self):
        return self.incoming.get_nowait()


class AdapterTests(unittest.TestCase):
    def test_discovery_only_accepts_one_main_app_on_the_fixed_loopback_port(self):
        good = {"type": "page", "id": "main", "url": "app://-/index.html",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9223/devtools/page/main"}
        self.assertTrue(valid_target(good))
        for changes in (
            {"url": "https://chatgpt.com/"}, {"type": "iframe"},
            {"url": "app://-/detached-window.html"},
            {"webSocketDebuggerUrl": "ws://example.com:9223/devtools/page/main"},
            {"webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/main"},
            {"webSocketDebuggerUrl": "ws://user:pass@127.0.0.1:9223/devtools/page/main"},
            {"url": "app://-/index.html?window=page"},
        ):
            self.assertFalse(valid_target({**good, **changes}))
        with patch("twintext.message_adapter.read_targets", return_value=[good]):
            self.assertEqual(discover(), good["webSocketDebuggerUrl"])
        with patch("twintext.message_adapter.read_targets", return_value=[good, good]):
            self.assertIsNone(discover(), "Ambiguous windows must not be guessed")

    def test_click_delivery_checks_document_context_identity_and_length(self):
        socket = Socket()
        events = queue.Queue(maxsize=8)
        session = CDPSession(socket, events, "zh")
        session.install()
        value = {"document": session.nonce + ":doc-1", "request": 1, "action": "translate",
                 "session": "thread-1", "message": "old-reply", "text": "Private original"}

        def deliver(payload, context=7, name=None):
            session.event({"method": "Runtime.bindingCalled", "params": {
                "name": name or session.binding, "executionContextId": context,
                "payload": json.dumps(payload)}})

        deliver(value)
        self.assertEqual(events.get_nowait(), value)
        for changes in (
            {"document": "wrong:document"}, {"action": "run-command"}, {"request": True},
            {"session": ""}, {"message": ""}, {"text": ""}, {"text": "x" * 100001},
        ):
            deliver({**value, **changes})
        deliver(value, context=8)
        deliver(value, name="not-our-binding")
        deliver([])
        self.assertTrue(events.empty())

    def test_binding_and_script_reinstall_across_reload_and_cleanup(self):
        socket = Socket()
        session = CDPSession(socket, queue.Queue(maxsize=8), "en")
        session.install()
        methods = [call["method"] for call in socket.sent]
        self.assertIn("Runtime.addBinding", methods)
        self.assertIn("Page.addScriptToEvaluateOnNewDocument", methods)
        source = next(call["params"]["source"] for call in socket.sent
                      if call["method"] == "Page.addScriptToEvaluateOnNewDocument")
        self.assertIn("crypto.randomUUID()", source)
        session.feedback({"document": session.nonce + ":doc-1", "request": 1}, "original")
        expression = socket.sent[-1]["params"]["expression"]
        self.assertIn('"state": "original"', expression)
        self.assertNotIn("Private original", expression)
        session.cleanup()
        methods = [call["method"] for call in socket.sent]
        self.assertIn("Page.removeScriptToEvaluateOnNewDocument", methods)
        self.assertIn("Runtime.removeBinding", methods)

    def test_context_reset_cancels_queued_delivery_and_rejects_old_context(self):
        events = queue.Queue(maxsize=8)
        session = CDPSession(Socket(), events, "en")
        session.install()
        session.event({"method": "Runtime.executionContextsCleared"})
        self.assertEqual(events.get_nowait()["action"], "reset")
        value = {"document": session.nonce + ":old", "request": 1, "action": "translate",
                 "session": "thread", "message": "reply", "text": "Do not translate"}
        session.event({"method": "Runtime.bindingCalled", "params": {
            "name": session.binding, "executionContextId": 7, "payload": json.dumps(value)}})
        self.assertTrue(events.empty())

    def test_navigation_reset_discards_clicks_even_when_event_queue_is_full(self):
        events = queue.Queue(maxsize=8)
        session = CDPSession(Socket(), events, "en")
        for index in range(8):
            events.put({"action": "translate", "request": index})
        session.event({"method": "Runtime.executionContextsCleared"})
        self.assertEqual(events.qsize(), 1)
        self.assertEqual(events.get_nowait(), {"action": "reset"})
