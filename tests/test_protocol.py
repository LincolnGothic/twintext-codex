import http.client
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from test_core import FakeEngine

from twintext.mcp import UI_URI, handle, tools
from twintext.service import Service
from twintext.ui import create_server


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {"TWINTEXT_HOME": directory.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.service = Service(FakeEngine(), lambda text: "en")

    def request(self, method, params=None):
        return handle(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}, self.service
        )

    def test_initialize_and_ui_resource(self):
        result = self.request("initialize", {"protocolVersion": "2025-11-25"})["result"]
        self.assertEqual(result["protocolVersion"], "2025-11-25")
        self.assertEqual(len(self.request("tools/list")["result"]["tools"]), 6)
        resource = self.request("resources/read", {"uri": UI_URI})["result"]["contents"][0]
        self.assertIn("embedded: true", resource["text"])
        self.assertIn("ui/initialize", resource["text"])
        self.assertNotIn("{{JS}}", resource["text"])

    def test_missing_unknown_and_wrong_type_arguments_are_tool_errors(self):
        for params in (
            {"name": "twintext_translate", "arguments": {}},
            {"name": "not_a_tool"},
            {"name": "twintext_status", "arguments": {"extra": True}},
            {"name": "twintext_translate", "arguments": {"text": None}},
        ):
            self.assertTrue(self.request("tools/call", params)["result"]["isError"])

    def test_valid_tool_result_and_preferences(self):
        self.request(
            "tools/call",
            {"name": "twintext_set_settings", "arguments": {"target": "zh", "ui_language": "es"}},
        )
        result = self.request(
            "tools/call", {"name": "twintext_translate", "arguments": {"text": "Hello"}}
        )["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["target"], "zh")

    def test_model_runtime_failure_returns_an_actionable_tool_error(self):
        with patch.object(self.service, "translate", side_effect=RuntimeError("Model cannot load")):
            result = self.request(
                "tools/call", {"name": "twintext_translate", "arguments": {"text": "Hello"}}
            )["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["content"][0]["text"], "Model cannot load")

    def test_notifications_no_response_and_unknown_methods(self):
        self.assertIsNone(
            handle({"jsonrpc": "2.0", "method": "notifications/initialized"}, self.service)
        )
        self.assertEqual(self.request("wrong")["error"]["code"], -32601)
        self.assertEqual(handle([], self.service)["error"]["code"], -32600)

    def test_stdio_contains_only_json_frames(self):
        frames = [
            "bad json",
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}),
        ]
        process = subprocess.run(
            [sys.executable, "-m", "twintext.cli", "mcp"],
            input="\n".join(frames) + "\n",
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        results = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["error"]["code"], -32700)
        self.assertEqual(results[-1]["result"], {})

    def test_mcp_model_install_is_explicitly_networked(self):
        definition = next(item for item in tools() if item["name"] == "twintext_install_models")
        self.assertTrue(definition["annotations"]["openWorldHint"])
        self.assertFalse(definition["annotations"]["readOnlyHint"])

    def test_local_ui_requires_token_origin_and_loopback_host(self):
        server = create_server(service=self.service)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        self.addCleanup(connection.close)
        connection.request("GET", "/")
        response = connection.getresponse()
        html = response.read().decode()
        self.assertEqual(response.status, 200)
        token = re.search(r'token: "([A-Za-z0-9_-]+)"', html)[1]
        body = json.dumps({"name": "twintext_status", "arguments": {}})
        for headers in (
            {"Content-Type": "application/json"},
            {
                "Content-Type": "application/json",
                "X-TwinText-Token": token,
                "Origin": "https://foreign.example",
            },
            {
                "Content-Type": "application/json",
                "X-TwinText-Token": token,
                "Host": "foreign.example",
            },
        ):
            connection.request("POST", "/api/tool", body, headers)
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 403)
        connection.request(
            "POST",
            "/api/tool",
            body,
            {"Content-Type": "application/json", "X-TwinText-Token": token},
        )
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn("settings", json.loads(response.read()))


if __name__ == "__main__":
    unittest.main()
