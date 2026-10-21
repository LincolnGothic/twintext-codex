import os
import sys
import tempfile
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from test_bridge import payload  # noqa: E402
from test_core import FakeEngine  # noqa: E402
from test_desktop import PendingAdapter, PendingTranslator  # noqa: E402

from twintext.bridge import Inbox  # noqa: E402
from twintext.cli import main  # noqa: E402
from twintext.config import TwinTextError, load_settings, update_settings  # noqa: E402
from twintext.desktop import Companion  # noqa: E402
from twintext.service import Service  # noqa: E402
from twintext.window_follow import logical_bounds  # noqa: E402
from twintext.window_tracking import (  # noqa: E402
    Snapshot,
    TargetWindow,
    codex_wm_class,
    create_tracker,
)


class Tracker:
    def __init__(self):
        self.target = TargetWindow(9001, 50, 30, 700, 700)
        self.foreground = self.target.id
        self.closed = False

    def read(self):
        return Snapshot(self.target, self.foreground)

    def close(self):
        self.closed = True


class FollowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        environment = patch.dict(os.environ, TWINTEXT_HOME=folder.name)
        environment.start()
        self.addCleanup(environment.stop)
        adapter = patch("twintext.desktop.MessageAdapter", PendingAdapter)
        adapter.start()
        self.addCleanup(adapter.stop)
        update_settings(target="zh", desktop_auto_start=False)
        self.worker = PendingTranslator()
        self.inbox = Inbox()
        self.window = Companion(self.inbox, self.worker)
        self.window.timer.stop()
        self.addCleanup(self.dispose)
        self.tracker = Tracker()
        self.window.follower.factory = lambda: self.tracker
        previous = self.window.settings
        self.window.settings = update_settings(follow_codex=True)
        self.window.settings_changed(previous)
        self.window.collapse()

    def dispose(self):
        self.window.follower.close()
        self.window.hide()
        self.window.orb.hide()
        self.window.orb.deleteLater()
        self.window.deleteLater()
        self.app.processEvents()

    def test_button_follows_move_and_stays_inside_resized_window(self):
        orb = self.window.orb
        position = orb.pos()
        self.tracker.target = replace(self.tracker.target, x=75, y=50)
        self.window.follower.tick()
        self.assertEqual(orb.pos(), position + QPoint(25, 20))
        self.tracker.target = replace(self.tracker.target, width=350, height=300)
        self.window.follower.tick()
        self.assertTrue(self.window.follower.bounds.contains(orb.geometry()))

    def test_user_drag_offset_is_retained_as_codex_moves(self):
        self.window.orb.move(180, 160)
        self.app.processEvents()
        self.window.follower.tick()
        self.assertEqual(self.window.orb.pos(), QPoint(180, 160))
        self.tracker.target = replace(self.tracker.target, x=70, y=40)
        self.window.follower.tick()
        self.assertEqual(self.window.orb.pos(), QPoint(200, 170))

    def test_minimize_focus_loss_close_restore_and_new_codex_window(self):
        self.window.expand()
        for reason in ("minimized", "other_app", "closed"):
            with self.subTest(reason=reason):
                original = self.tracker.target
                if reason == "minimized":
                    self.tracker.target = replace(original, visible=False)
                elif reason == "other_app":
                    self.tracker.foreground = 7777
                else:
                    self.tracker.target = None
                self.window.follower.tick()
                self.assertFalse(self.window.isVisible())
                self.assertFalse(self.window.orb.isVisible())
                self.assertTrue(self.window.reader_open)
                self.tracker.target = replace(original, id=9002)
                self.tracker.foreground = 9002
                self.window.follower.tick()
                self.assertTrue(self.window.isVisible())
                self.assertTrue(self.window.orb.isVisible())

    def test_twintext_focus_keeps_reader_visible(self):
        self.window.expand()
        self.tracker.foreground = int(self.window.winId())
        self.window.follower.tick()
        self.assertTrue(self.window.isVisible())

    def test_following_reader_translates_only_after_explicit_reply_selection(self):
        self.inbox.publish(payload(text="Hello world."), archive=True)
        self.window.poll()
        self.assertFalse(self.worker.jobs, "A collapsed attached reader translates on demand")
        self.window.orb_button.click()
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.worker.jobs, [])
        self.window.sessions.setCurrentIndex(0)
        self.window.toggle_button.click()
        revision, text, source, target = self.worker.jobs[-1]
        result = Service(FakeEngine()).translate(text, source="en", target=target)
        self.worker.results.put((revision, result, None))
        self.window.poll()
        self.assertIn("Hello world.", self.window.reader.toPlainText())
        self.assertIn("译:", self.window.reader.toPlainText())
        settings = load_settings()
        self.window.orb_button.click()
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.window.orb_button.isChecked())
        self.window.orb_button.click()
        self.assertTrue(self.window.isVisible())
        self.assertEqual(len(self.worker.jobs), 1)
        self.assertEqual(settings, load_settings())
        update_settings(mode="translated")
        self.window.poll()
        self.window.toggle_button.click()
        self.assertTrue(self.window.reader.toPlainText().startswith("译:"))
        self.assertEqual(len(self.worker.jobs), 1)

    def test_settings_remain_reachable_while_codex_is_inactive(self):
        self.window.expand()
        self.window.toggle_settings()
        self.tracker.foreground = 7777
        self.window.follower.tick()
        self.assertTrue(self.window.preference_scroll.isVisible())
        self.window.checks["follow"].setChecked(False)
        self.window.poll()
        self.assertFalse(load_settings().follow_codex)
        self.assertTrue(self.tracker.closed)

    def test_backend_failure_falls_back_to_manual_button(self):
        self.tracker.foreground = 7777
        self.window.follower.tick()
        self.assertFalse(self.window.orb.isVisible())
        with patch.object(self.tracker, "read", side_effect=OSError("Display disconnected")):
            self.window.follower.tick()
        self.assertEqual(self.window.follower.status, "follow_unavailable")
        self.assertTrue(self.window.orb.isVisible())
        self.assertTrue(self.tracker.closed)
        self.window.orb_button.click()
        self.assertTrue(self.window.isVisible())

    def test_explicit_launch_reopens_settings_after_codex_closes(self):
        self.tracker.target = None
        self.window.follower.tick()
        self.assertFalse(self.window.orb.isVisible())
        self.inbox.activate()
        self.window.poll()
        self.assertTrue(self.window.isVisible())
        self.assertTrue(self.window.preference_scroll.isVisible())

    def test_follow_preferences_default_validation_and_cli(self):
        with self.assertRaises(TwinTextError):
            update_settings(follow_codex="true")
        with patch("sys.stdout"):
            self.assertEqual(main(["settings", "--follow-codex", "false"]), 0)
        self.assertFalse(load_settings().follow_codex)

    def test_windows_per_monitor_scaling_and_negative_origins(self):
        screen = SimpleNamespace(name=lambda: "second", devicePixelRatio=lambda: 2,
                                 geometry=lambda: QRect(-1280, 0, 1280, 720))
        target = TargetWindow(1, -2400, 120, 1200, 800, monitor=(-2560, 0),
                              screen_name="second")
        self.assertEqual(logical_bounds(target, [screen]), QRect(-1200, 60, 600, 400))

    def test_pure_wayland_reports_unsupported_without_touching_display(self):
        with patch("sys.platform", "linux"), patch.dict(os.environ, DISPLAY=""):
            with self.assertRaises(OSError):
                create_tracker()

    def test_linux_codex_identity_includes_legacy_electron_class(self):
        self.assertTrue(codex_wm_class(("codex", "Codex")))
        self.assertTrue(codex_wm_class(("chatgpt (/home/user/.config/Codex)", "Chatgpt")))
        self.assertFalse(codex_wm_class(("chatgpt", "Chatgpt")))
        self.assertFalse(codex_wm_class(("gnome-terminal", "Codex terminal")))

    @unittest.skipUnless(sys.platform == "win32", "Native Windows API smoke check")
    def test_native_windows_api_uses_valid_pointer_signatures(self):
        tracker = create_tracker()
        self.addCleanup(tracker.close)
        self.assertIsInstance(tracker.read(), Snapshot)
