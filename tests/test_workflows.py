import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_bridge import payload
from test_core import FakeEngine
from test_markdown_formats import TABLE

from twintext.bridge import Inbox, capture
from twintext.config import config_dir, data_dir, load_settings, update_settings
from twintext.locking import acquire_lock
from twintext.mcp import handle
from twintext.service import Service, context

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        environment = patch.dict(os.environ, {"TWINTEXT_HOME": folder.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.service = Service(FakeEngine(), lambda _: "en")
        update_settings(target="zh", desktop_auto_start=False, cache=False)

    def test_chat_context_follows_language_mode_and_pause(self):
        self.assertEqual(context(), "")
        update_settings(workflow="chat", target="ja", mode="translated")
        self.assertIn("Japanese", context())
        self.assertIn("translated", context())
        self.assertIn("twintext_translate", context())
        update_settings(enabled=False)
        self.assertIn("paused", context())
        update_settings(enabled=True, mode="original")
        self.assertIn("paused", context())
        update_settings(workflow="desktop")
        self.assertEqual(context(), "")

    def test_chat_stop_does_not_store_or_launch(self):
        update_settings(workflow="chat", desktop_auto_start=True)
        with patch("twintext.bridge.launch_desktop") as launch:
            capture(io.StringIO(json.dumps(payload())))
        launch.assert_not_called()
        self.assertEqual(Inbox().replies(), [])

    def test_cli_preserves_utf8_even_with_legacy_windows_pipe_encoding(self):
        text = "中文 日本語 Français Español\n"
        environment = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        result = subprocess.run(
            [sys.executable, "-m", "twintext.cli", "translate", "--mode", "original"],
            input=text.encode("utf-8"),
            capture_output=True,
            check=True,
            env=environment,
        )
        self.assertEqual(result.stdout.decode("utf-8").rstrip("\n"), text.rstrip("\n"))

    def test_same_table_translation_for_chat_mcp_and_desktop_backend(self):
        for mode in ("bilingual", "translated"):
            update_settings(workflow="chat", mode=mode)
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "twintext_translate", "arguments": {"text": TABLE}},
            }
            tool = handle(request, self.service)["result"]
            self.assertFalse(tool["isError"])
            self.assertIn("译:Fresh red apples", tool["content"][0]["text"])
            update_settings(workflow="desktop")
            self.assertEqual(tool["structuredContent"], self.service.translate(TABLE))

    def test_old_settings_load_and_future_fields_survive_update(self):
        path = self.folder / "settings.json"
        old = {
            "target": "zh",
            "source": "auto",
            "mode": "bilingual",
            "cache": True,
            "enabled": True,
            "ui_language": "en",
            "future_option": {"keep": True},
        }
        path.write_text(json.dumps(old), encoding="utf-8")
        self.assertEqual(load_settings().workflow, "desktop")
        update_settings(workflow="chat")
        self.assertEqual(json.loads(path.read_text())["future_option"], {"keep": True})
        self.assertEqual(load_settings().target, "zh")

    def test_native_windows_directories_and_explicit_isolation(self):
        with patch("twintext.config.sys.platform", "win32"):
            self.assertEqual(data_dir(), self.folder)
            self.assertEqual(config_dir(), self.folder)
            with patch.dict(
                os.environ,
                {
                    "LOCALAPPDATA": str(self.folder / "Local"),
                    "APPDATA": str(self.folder / "Roaming"),
                },
            ):
                os.environ.pop("TWINTEXT_HOME")
                self.assertEqual(data_dir(), self.folder / "Local/TwinText")
                self.assertEqual(config_dir(), self.folder / "Roaming/TwinText")

    def test_file_lock_excludes_another_process_and_releases_on_close(self):
        path = self.folder / "shared.lock"
        script = (
            "from pathlib import Path; from twintext.locking import acquire_lock; "
            "import sys; lock=acquire_lock(Path(sys.argv[1]),blocking=False); "
            "print(lock is not None); lock.close() if lock else None"
        )
        lock = acquire_lock(path)
        try:
            result = subprocess.check_output([sys.executable, "-c", script, str(path)], text=True)
            self.assertEqual(result.strip(), "False")
        finally:
            lock.close()
        result = subprocess.check_output([sys.executable, "-c", script, str(path)], text=True)
        self.assertEqual(result.strip(), "True")

    def test_chat_hooks_return_preferences_only_in_chat_workflow(self):
        hook = ROOT / "plugins/twintext/hooks/context.py"
        with patch.dict(os.environ, {"TWINTEXT_PYTHON": sys.executable}):
            for workflow in ("desktop", "chat"):
                update_settings(workflow=workflow)
                for event in ("SessionStart", "UserPromptSubmit"):
                    result = subprocess.run(
                        [sys.executable, str(hook)],
                        input=json.dumps({"hook_event_name": event}),
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=10,
                    )
                    output = json.loads(result.stdout)
                    if workflow == "desktop":
                        self.assertEqual(output, {})
                    else:
                        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], event)
                        self.assertIn("Chinese", output["hookSpecificOutput"]["additionalContext"])

    def test_windows_installer_wires_private_python_without_changing_other_plugins(self):
        spec = importlib.util.spec_from_file_location(
            "twintext_installer", ROOT / "scripts/install.py"
        )
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        plugin = self.folder / "plugin"
        python = self.folder / "Name with spaces/venv/Scripts/python.exe"
        installer.prepare_plugin(plugin, python, windows=True)
        mcp = json.loads((plugin / ".mcp.json").read_text())
        self.assertEqual(mcp["mcpServers"]["twintext"]["command"], str(python))
        hooks = json.loads((plugin / "hooks/hooks.json").read_text())["hooks"]
        for entries in hooks.values():
            command = entries[0]["hooks"][0]["commandWindows"]
            self.assertIn(str(python), command)
            self.assertIn("powershell.exe", command)
        self.assertFalse((plugin / "plugin.json").exists())


if __name__ == "__main__":
    unittest.main()
