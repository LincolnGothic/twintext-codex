import os
import queue
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from test_bridge import payload  # noqa: E402
from test_core import FakeEngine  # noqa: E402
from test_markdown_formats import TABLE  # noqa: E402

from twintext.bridge import Inbox  # noqa: E402
from twintext.cache import Cache  # noqa: E402
from twintext.config import LANGUAGES, load_settings, update_settings  # noqa: E402
from twintext.desktop import WORDS, Companion  # noqa: E402
from twintext.service import Service  # noqa: E402


class PendingTranslator:
    def __init__(self):
        self.results = queue.SimpleQueue()
        self.jobs = []

    def submit(self, *job):
        self.jobs.append(job)


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {"TWINTEXT_HOME": directory.name})
        environment.start()
        self.addCleanup(environment.stop)
        update_settings(target="zh", desktop_auto_start=False)
        self.inbox = Inbox()
        self.worker = PendingTranslator()
        self.window = Companion(self.inbox, self.worker)
        self.addCleanup(self.dispose)
        self.window.timer.stop()
        self.service = Service(FakeEngine(), detector=lambda text: "en")

    def dispose(self):
        self.window.hide()
        self.window.orb.hide()
        self.window.orb.deleteLater()
        self.window.deleteLater()
        self.app.processEvents()

    def deliver_result(self):
        revision, text, source, target = self.worker.jobs[-1]
        result = self.service.translate(text, source=source, target=target, mode="translated")
        self.worker.results.put((revision, result, None))
        self.window.poll()

    def test_capture_to_bilingual_reader_and_copy_does_not_modify_original(self):
        text = "Hello world.\n\n```sh\nnpm test\n```\n"
        self.inbox.publish(payload(text=text))
        self.window.poll()
        self.deliver_result()
        self.assertIn("Hello world.", self.window.reader.toPlainText())
        self.assertIn("译:Hello world.", self.window.reader.toPlainText())
        self.assertEqual(self.window.reader.toPlainText().count("npm test"), 1)
        self.window.copy()
        self.assertIn("译:", self.app.clipboard().text())
        self.assertEqual(self.inbox.replies()[0]["text"], text)

    def test_stale_model_result_does_not_replace_a_newer_reply(self):
        self.inbox.publish(payload(text="First"))
        self.window.poll()
        old_revision = self.worker.jobs[-1][0]
        self.inbox.publish(payload(turn="second", text="Second"))
        self.window.poll()
        self.worker.results.put((old_revision, self.service.translate("First"), None))
        self.window.poll()
        self.assertEqual(self.window.reader.toPlainText(), "Second")
        self.deliver_result()
        self.assertIn("译:Second", self.window.reader.toPlainText())

    def test_display_modes_switch_without_new_inference_after_translation(self):
        self.inbox.publish(payload(text="Hello"))
        self.window.poll()
        self.deliver_result()
        count = len(self.worker.jobs)
        self.window.selects["mode"].setCurrentIndex(1)
        self.assertEqual(self.window.reader.toPlainText(), "译:Hello")
        self.window.selects["mode"].setCurrentIndex(2)
        self.assertEqual(self.window.reader.toPlainText(), "Hello")
        self.window.selects["mode"].setCurrentIndex(0)
        self.assertIn("译:Hello", self.window.reader.toPlainText())
        self.assertEqual(len(self.worker.jobs), count)

    def test_all_ui_languages_are_complete_and_independent_of_translation_target(self):
        for code in LANGUAGES:
            self.assertEqual(WORDS[code].keys(), WORDS["en"].keys())
            update_settings(ui_language=code)
            self.window.poll()
            self.assertEqual(self.window.settings_button.text(), WORDS[code]["settings"])
            self.assertEqual(load_settings().target, "zh")
        update_settings(ui_language="auto", host_locale="fr")
        self.window.poll()
        self.assertEqual(self.window.settings_button.text(), "Paramètres")

    def test_translation_location_is_saved_without_changing_language_or_mode(self):
        self.window.selects["workflow"].setCurrentIndex(1)
        settings = load_settings()
        self.assertEqual(settings.workflow, "chat")
        self.assertEqual(settings.target, "zh")
        self.assertEqual(settings.mode, "bilingual")
        self.window.selects["workflow"].setCurrentIndex(0)
        self.assertEqual(load_settings().workflow, "desktop")

    def test_settings_scroll_in_a_small_window_without_clipping_controls(self):
        self.window.show()
        self.window.resize(480, 560)
        self.window.settings_button.click()
        self.app.processEvents()
        self.assertTrue(self.window.preference_scroll.isVisible())
        self.assertGreater(self.window.preference_scroll.verticalScrollBar().maximum(), 0)
        self.window.preference_scroll.ensureWidgetVisible(self.window.cache_button)
        self.app.processEvents()
        for combo in self.window.selects.values():
            self.assertGreaterEqual(combo.height(), combo.fontMetrics().height())

    def test_model_error_shows_original_and_clear_invalidates_pending_work(self):
        self.inbox.publish(payload(text="Hello"))
        self.window.poll()
        revision = self.worker.jobs[-1][0]
        self.worker.results.put((revision, None, "No model"))
        self.window.poll()
        self.assertEqual(self.window.reader.toPlainText(), "Hello")
        self.assertIn("No model", self.window.status.text())
        self.window.clear()
        self.worker.results.put((revision, self.service.translate("Hello"), None))
        self.window.poll()
        self.assertEqual(self.inbox.replies(), [])
        self.assertFalse(self.window.copy_button.isEnabled())

    def test_collapse_activation_and_resource_loading(self):
        self.window.show()
        self.window.collapse()
        self.assertTrue(self.window.orb.isVisible())
        self.inbox.activate()
        self.window.poll()
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.orb.isVisible())
        self.assertTrue(self.window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.assertIsNone(self.window.reader.loadResource(2, "https://example.com/image.png"))

    def test_table_renders_and_copy_modes_preserve_rows_and_numbers(self):
        self.inbox.publish(payload(text=TABLE))
        self.window.poll()
        self.deliver_result()
        plain = self.window.reader.toPlainText()
        self.assertIn("译:Fresh red apples", plain)
        self.assertIn("Fresh red apples", plain)
        self.assertEqual(plain.count("Whole wheat loaf"), 2)
        self.window.copy()
        self.assertIn("| 译:Apples | 译:Fresh red apples | 5 |", self.app.clipboard().text())
        self.window.selects["mode"].setCurrentIndex(1)
        self.assertEqual(self.window.reader.toPlainText().count("Whole wheat loaf"), 1)
        self.window.selects["mode"].setCurrentIndex(2)
        self.assertNotIn("译:", self.window.reader.toPlainText())
        self.assertEqual(self.inbox.replies()[0]["text"], TABLE)

    def test_clear_cache_does_not_clear_inbox_or_preferences(self):
        self.inbox.publish(payload(text="Hello"))
        self.service.translate("Hello")
        cache = Cache()
        with cache.connect() as con:
            self.assertEqual(con.execute("select count(*) from translations").fetchone()[0], 1)
        saved = load_settings()
        self.window.cache_button.click()
        with cache.connect() as con:
            self.assertEqual(con.execute("select count(*) from translations").fetchone()[0], 0)
        self.assertEqual(self.inbox.replies()[0]["text"], "Hello")
        self.assertEqual(load_settings(), saved)
        self.assertIn("cleared", self.window.status.text())

    def test_orb_handle_starts_move_and_click_opens_without_dragging(self):
        self.window.collapse()
        self.app.processEvents()
        self.assertGreaterEqual(self.window.orb_handle.width(), 30)
        self.assertEqual(self.window.orb_handle.toolTip(), "Drag to move")
        with patch("twintext.desktop.start_window_move") as move:
            QTest.mouseClick(self.window.orb_handle, Qt.MouseButton.LeftButton)
            move.assert_called_once_with(self.window.orb_handle)
            self.assertTrue(self.window.orb.isVisible())
            QTest.mouseClick(self.window.orb_button, Qt.MouseButton.LeftButton)
            self.assertTrue(self.window.isVisible())
            self.assertFalse(self.window.orb.isVisible())
            self.assertEqual(move.call_count, 1)

    def test_dragging_expand_button_does_not_open_reader(self):
        self.window.collapse()
        self.app.processEvents()
        button = self.window.orb_button
        pos = button.rect().center()
        QTest.mousePress(button, Qt.MouseButton.LeftButton, pos=pos)
        moved = pos + QPoint(QApplication.startDragDistance() + 10, 0)
        event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(moved),
            QPointF(button.mapToGlobal(moved)),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        with patch("twintext.desktop.start_window_move") as move:
            QApplication.sendEvent(button, event)
            move.assert_called_once_with(button)
        QTest.mouseRelease(button, Qt.MouseButton.LeftButton, pos=moved)
        self.assertFalse(self.window.isVisible())
        self.assertTrue(self.window.orb.isVisible())


if __name__ == "__main__":
    unittest.main()
