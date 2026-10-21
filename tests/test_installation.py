import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from twintext.config import update_settings

ROOT = Path(__file__).resolve().parents[1]


class InstallationTests(unittest.TestCase):
    def test_codex_package_exposes_capture_hook_without_portable_shadow(self):
        plugin = ROOT / "plugins/twintext"
        self.assertFalse((plugin / "plugin.json").exists())
        manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
        hooks = json.loads((plugin / manifest["hooks"]).read_text())
        self.assertEqual(set(hooks["hooks"]), {"SessionStart", "UserPromptSubmit", "Stop"})
        command = hooks["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertIn("${PLUGIN_ROOT}/hooks/capture.py", command)
        mcp = json.loads((plugin / manifest["mcpServers"]).read_text())
        self.assertIn("twintext", mcp["mcpServers"])
        self.assertTrue((plugin / manifest["skills"]).is_dir())

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        self.plugin = self.home / "data/twintext/plugin"
        self.plugin.mkdir(parents=True)
        self.marketplace = self.home / ".agents/plugins/marketplace.json"
        self.marketplace.parent.mkdir(parents=True)

    def register(self):
        with (
            patch.object(Path, "home", return_value=self.home),
            patch.object(sys, "argv", ["register-plugin.py", str(self.plugin)]),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            runpy.run_path(str(ROOT / "scripts/register-plugin.py"), run_name="__main__")

    def test_windows_launcher_waits_and_cancellation_does_not_pause(self):
        app = self.home / "TwinText %test%"
        app.mkdir()
        install = runpy.run_path(str(ROOT / "scripts/install.py"))
        with (patch.dict(os.environ, APPDATA=str(self.home / "appdata"), TWINTEXT_HOME="",
                         TWINTEXT_CONFIG_DIR="", TWINTEXT_DATA_DIR=""),
              patch("subprocess.run")):
            install["windows_launchers"](app)
        batch = (app / "Open Codex with TwinText.cmd").read_bytes()
        interpreter = self.home / "TwinText %%test%%/venv/Scripts/python.exe"
        self.assertEqual(batch.split(b"\r\n"), [
            b"@echo off",
            b"setlocal DisableDelayedExpansion",
            b'set "TWINTEXT_HOME="',
            f'set "TWINTEXT_DATA_DIR={str(app.resolve()).replace("%", "%%")}"'.encode(),
            f'set "TWINTEXT_CONFIG_DIR={(self.home / "appdata/TwinText").resolve()}"'.encode(),
            f'"{interpreter}" -m twintext.cli codex-launch --wait'.encode(),
            b"if errorlevel 130 exit /b 130",
            b"if errorlevel 1 pause",
            b"",
        ])

    @unittest.skipUnless(sys.platform == "win32", "Windows command interpreter")
    def test_windows_launcher_preserves_percent_and_bang_in_settings_paths(self):
        app = self.home / "TwinText %test% !TASK_LAUNCHER_PROFILE!"
        app.mkdir()
        settings = self.home / "settings %test% !TASK_LAUNCHER_PROFILE!"
        install = runpy.run_path(str(ROOT / "scripts/install.py"))
        environment = dict(os.environ, TWINTEXT_HOME="", TWINTEXT_DATA_DIR=str(app),
                           TWINTEXT_CONFIG_DIR=str(settings), TASK_LAUNCHER_PROFILE="wrong")
        with patch.dict(os.environ, environment), patch("subprocess.run"):
            install["windows_launchers"](app)
        probe = self.home / "probe.py"
        probe.write_text(
            "import json, os\nprint(json.dumps([os.environ['TWINTEXT_DATA_DIR'], "
            "os.environ['TWINTEXT_CONFIG_DIR']]))\n", encoding="utf-8",
        )
        launcher = (app / "Open Codex with TwinText.cmd").read_text(encoding="utf-8")
        interpreter = str(app / "venv/Scripts/python.exe").replace("%", "%%")
        prefix, separator, _ = launcher.partition(f'"{interpreter}"')
        self.assertTrue(separator)
        batch = self.home / "probe.cmd"
        batch.write_text(prefix + f'"{sys.executable}" "{probe}"\n', encoding="utf-8")
        result = subprocess.run(
            f'cmd.exe /d /v:on /s /c ""{batch}""', env=environment,
            text=True, capture_output=True, check=True, timeout=10,
        )
        self.assertEqual(json.loads(result.stdout), [str(app.resolve()), str(settings.resolve())])

    def test_registration_preserves_marketplace_and_other_plugins(self):
        other = {"name": "existing", "source": {"source": "local", "path": "./existing"}}
        self.marketplace.write_text(json.dumps({"name": "personal", "plugins": [other]}))
        self.register()
        self.register()
        result = json.loads(self.marketplace.read_text())
        self.assertEqual(result["name"], "personal")
        self.assertEqual(result["plugins"][0], other)
        self.assertEqual(len(result["plugins"]), 2)
        self.assertEqual(result["plugins"][1]["source"]["path"], "./data/twintext/plugin")

    def test_conflicting_plugin_registration_leaves_file_unchanged(self):
        original = json.dumps(
            {"name": "personal", "plugins": [{"name": "twintext", "source": {"path": "./other"}}]}
        )
        self.marketplace.write_text(original)
        with self.assertRaises(SystemExit):
            self.register()
        self.assertEqual(self.marketplace.read_text(), original)

    def test_legacy_hook_never_injects_model_instructions(self):
        with patch.dict(
            os.environ, {"TWINTEXT_HOME": str(self.home), "TWINTEXT_PYTHON": sys.executable}
        ):
            update_settings(target="ja", ui_language="fr")

            def invoke():
                result = subprocess.run(
                    [sys.executable, str(ROOT / "plugins/twintext/hooks/context.py")],
                    input=json.dumps({"hook_event_name": "SessionStart"}),
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=10,
                )
                return json.loads(result.stdout)

            self.assertEqual(invoke(), {})
            update_settings(enabled=False)
            self.assertEqual(invoke(), {})


if __name__ == "__main__":
    unittest.main()
