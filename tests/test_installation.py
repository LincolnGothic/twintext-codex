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
        self.assertEqual(list(hooks["hooks"]), ["Stop"])
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
