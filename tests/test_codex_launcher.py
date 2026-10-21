import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from twintext.codex_launcher import launch
from twintext.config import TwinTextError, update_settings


class LauncherTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        env = patch.dict(os.environ, TWINTEXT_HOME=folder.name)
        env.start()
        self.addCleanup(env.stop)
        self.executable = self.folder / "Codex.exe"
        self.executable.write_bytes(b"fixture")
        update_settings(workflow="chat", chat_presentation="floating", message_buttons=True)

    def test_launcher_refuses_existing_app_and_never_kills_processes(self):
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", return_value=(self.executable, True)),
              patch("twintext.codex_launcher.subprocess.Popen") as spawn):
            with self.assertRaisesRegex(TwinTextError, "Exit Codex"):
                launch()
            spawn.assert_not_called()

    def test_launcher_uses_loopback_debugging_and_opens_existing_reader(self):
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", return_value=(self.executable, False)),
              patch("twintext.codex_launcher.check_port"),
              patch("twintext.codex_launcher.subprocess.Popen") as spawn,
              patch("twintext.codex_launcher.launch_desktop") as reader):
            launch()
            command = spawn.call_args.args[0]
            self.assertEqual(command, [str(self.executable), "--remote-debugging-address=127.0.0.1",
                                       "--remote-debugging-port=9223"])
            reader.assert_called_once_with()

    def test_launcher_requires_explicit_opt_in_and_supported_platform(self):
        update_settings(message_buttons=False)
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app") as inspect):
            with self.assertRaisesRegex(TwinTextError, "settings"):
                launch()
            inspect.assert_not_called()
        with patch("twintext.codex_launcher.sys.platform", "linux"):
            with self.assertRaisesRegex(TwinTextError, "Windows"):
                launch()
