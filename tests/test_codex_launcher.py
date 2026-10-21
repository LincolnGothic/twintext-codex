import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from twintext.cli import main, parser
from twintext.codex_launcher import launch, windows_app
from twintext.config import TwinTextError, update_settings


class LauncherTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        env = patch.dict(os.environ, TWINTEXT_HOME=folder.name)
        env.start()
        self.addCleanup(env.stop)
        output = patch("sys.stderr", new_callable=io.StringIO)
        output.start()
        self.addCleanup(output.stop)
        self.executable = self.folder / "Codex.exe"
        self.executable.write_bytes(b"fixture")
        self.process = Mock()
        self.process.poll.return_value = None
        update_settings(workflow="chat", chat_presentation="floating", message_buttons=True)

    @unittest.skipUnless(sys.platform == "win32", "Windows package discovery")
    def test_discovery_selects_shared_app_instead_of_activation_stub(self):
        run = subprocess.run
        for name, binaries, expected, process_name, process_location, running in (
            ("shared", ("Codex.exe", "ChatGPT.exe"), "ChatGPT.exe",
             "codex.exe", "unrelated-cli/codex.exe", False),
            ("shared-only", ("ChatGPT.exe",), "ChatGPT.exe",
             "codex.exe", "unrelated-cli/codex.exe", False),
            ("legacy", ("Codex.exe",), "Codex.exe",
             "codex.exe", "unrelated-cli/codex.exe", False),
            ("running-shared", ("Codex.exe", "ChatGPT.exe"), "ChatGPT.exe",
             "ChatGPT.exe", "app/ChatGPT.exe", True),
            ("running-legacy", ("Codex.exe",), "Codex.exe",
             "Codex.exe", "app/Codex.exe", True),
            ("sibling", ("Codex.exe", "ChatGPT.exe"), "ChatGPT.exe",
             "ChatGPT.exe", "app-sibling/ChatGPT.exe", False),
        ):
            with self.subTest(package=name):
                package = self.folder / name
                app = package / "app"
                app.mkdir(parents=True)
                for binary in binaries:
                    (app / binary).write_bytes(b"fixture")
                # Execute the actual discovery script against a controlled package;
                # the real Codex app and process list are never accessed.
                prelude = (
                    "function Get-AppxPackage { [pscustomobject]@{ InstallLocation = '"
                    + str(package).replace("'", "''")
                    + "'; Version = '1.0' } }; "
                    "function Get-CimInstance { [pscustomobject]@{ Name = '"
                    + process_name + "'; ExecutablePath = '"
                    + str(package / process_location).replace("'", "''") + "' } }; "
                )

                def discover(command, prelude=prelude, **kwargs):
                    return run([*command[:-1], prelude + command[-1]], **kwargs)

                with patch("twintext.codex_launcher.subprocess.run", side_effect=discover):
                    self.assertEqual(windows_app(), (app / expected, running))

    def test_launcher_refuses_existing_app_and_never_kills_processes(self):
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", return_value=(self.executable, True)),
              patch("twintext.codex_launcher.subprocess.Popen") as spawn):
            with self.assertRaisesRegex(TwinTextError, "Exit Codex"):
                launch()
            spawn.assert_not_called()

    def test_failure_is_recorded_locally_after_terminal_dismissal(self):
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", return_value=(self.executable, True)),
              patch("sys.stderr", new_callable=io.StringIO)):
            with self.assertRaisesRegex(TwinTextError, "Exit Codex"):
                launch()
        log = self.folder / "desktop/launcher.log"
        self.assertTrue(log.is_file(), "The terminal error must remain available after dismissal")
        self.assertIn("Exit Codex", log.read_text(encoding="utf-8"))
        self.assertIn(str(self.folder / "settings.json"), log.read_text(encoding="utf-8"))
        self.assertIn("message_buttons=True", log.read_text(encoding="utf-8"))

    def test_wait_option_is_explicit_in_cli(self):
        self.assertTrue(parser().parse_args(["codex-launch", "--wait"]).wait)
        self.assertFalse(parser().parse_args(["codex-launch"]).wait)

    def test_waiting_launcher_continues_only_after_user_exits_shared_app(self):
        newer = self.folder / "ChatGPT.exe"
        newer.write_bytes(b"fixture")
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", side_effect=[
                  (self.executable, True), (self.executable, True), (newer, False)]),
              patch("twintext.codex_launcher.check_port"),
              patch("twintext.codex_launcher.subprocess.Popen", return_value=self.process) as spawn,
              patch("socket.create_connection"),
              patch("time.sleep") as sleep,
              patch("sys.stderr", new_callable=io.StringIO) as output,
              patch("twintext.codex_launcher.launch_desktop") as reader):

            def keep_app_running(_seconds):
                spawn.assert_not_called()
                reader.assert_not_called()

            sleep.side_effect = keep_app_running
            self.assertTrue(launch(wait=True)["launched"])
            self.assertEqual(spawn.call_args.args[0][0], str(newer))
            self.assertEqual(sleep.call_count, 2)
            self.assertIn("Waiting", output.getvalue())
            self.assertIn("Ctrl+C", output.getvalue())
            reader.assert_called_once_with()

    def test_cancelling_wait_does_not_start_or_stop_apps(self):
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", return_value=(self.executable, True)),
              patch("twintext.codex_launcher.subprocess.Popen") as spawn,
              patch("time.sleep", side_effect=KeyboardInterrupt),
              patch("sys.stderr", new_callable=io.StringIO),
              patch("twintext.codex_launcher.launch_desktop") as reader):
            self.assertEqual(main(["codex-launch", "--wait"]), 130)
            spawn.assert_not_called()
            reader.assert_not_called()
        self.assertIn("cancelled", (self.folder / "desktop/launcher.log").read_text(
            encoding="utf-8").lower())

    def test_launcher_uses_loopback_debugging_and_opens_existing_reader(self):
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", return_value=(self.executable, False)),
              patch("twintext.codex_launcher.check_port"),
              patch("twintext.codex_launcher.subprocess.Popen", return_value=self.process) as spawn,
              patch("socket.create_connection"),
              patch("twintext.codex_launcher.launch_desktop") as reader):
            launch()
            command = spawn.call_args.args[0]
            self.assertEqual(command, [str(self.executable), "--remote-debugging-address=127.0.0.1",
                                       "--remote-debugging-port=9223"])
            reader.assert_called_once_with()

    def test_reader_starts_only_after_debugging_port_becomes_ready(self):
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", return_value=(self.executable, False)),
              patch("twintext.codex_launcher.check_port"),
              patch("twintext.codex_launcher.subprocess.Popen", return_value=self.process),
              patch("socket.create_connection") as connect,
              patch("time.sleep"),
              patch("twintext.codex_launcher.launch_desktop") as reader):
            connect.side_effect = [OSError(), connect.return_value]

            def open_reader():
                self.assertEqual(connect.call_count, 2, "Reader opened before port readiness")

            reader.side_effect = open_reader
            result = launch()
            self.assertEqual(connect.call_count, 2)
            self.assertEqual(connect.call_args.args[0], ("127.0.0.1", 9223))
            self.assertTrue(result["launched"])
            reader.assert_called_once_with()

    def test_missing_debugging_port_is_an_error_instead_of_false_success(self):
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", return_value=(self.executable, False)),
              patch("twintext.codex_launcher.check_port"),
              patch("twintext.codex_launcher.subprocess.Popen", return_value=self.process),
              patch("socket.create_connection", side_effect=OSError()),
              patch("time.monotonic", side_effect=[0, 0, 21]),
              patch("time.sleep"),
              patch("twintext.codex_launcher.launch_desktop") as reader):
            with self.assertRaisesRegex(TwinTextError, "debugging"):
                launch()
            reader.assert_not_called()
            self.process.kill.assert_not_called()
            self.process.terminate.assert_not_called()

    def test_app_exit_during_startup_is_reported_without_opening_reader(self):
        self.process.poll.return_value = 1
        with (patch("twintext.codex_launcher.sys.platform", "win32"),
              patch("twintext.codex_launcher.windows_app", return_value=(self.executable, False)),
              patch("twintext.codex_launcher.check_port"),
              patch("twintext.codex_launcher.subprocess.Popen", return_value=self.process),
              patch("twintext.codex_launcher.launch_desktop") as reader):
            with self.assertRaisesRegex(TwinTextError, "exited"):
                launch()
            reader.assert_not_called()

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
