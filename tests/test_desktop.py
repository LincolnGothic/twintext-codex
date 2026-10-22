import json
import os
import queue
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent, QWheelEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from test_bridge import payload  # noqa: E402
from test_core import FakeEngine  # noqa: E402
from test_markdown_formats import TABLE  # noqa: E402

from twintext.bridge import Inbox  # noqa: E402
from twintext.cache import Cache  # noqa: E402
from twintext.config import LANGUAGES, config_dir, load_settings, update_settings  # noqa: E402
from twintext.desktop import WORDS, Companion, run  # noqa: E402
from twintext.service import Service  # noqa: E402


class PendingTranslator:
    def __init__(self):
        self.results = queue.SimpleQueue()
        self.progress = queue.Queue(maxsize=1)
        self.jobs = []

    def submit(self, *job):
        self.jobs.append(job)


class PendingAdapter:
    def __init__(self, language):
        self.language = language
        self.events = queue.Queue()
        self.feedbacks = []
        self.status = "buttons_connected"

    def feedback(self, request, state):
        self.feedbacks.append((request, state))

    def close(self):
        pass


class DesktopTests(unittest.TestCase):
    def test_manual_settings_do_not_offer_retired_methods_or_automatic_controls(self):
        for key in ("location", "response_scope"):
            self.assertNotIn(key, self.window.selects)
        for key in ("message_buttons", "translate_questions", "start"):
            self.assertNotIn(key, self.window.checks)
        self.window.poll()
        self.window.settings_button.click()
        self.window.selects["mode"].setCurrentIndex(1)
        self.window.checks["session_cache"].click()
        self.window.settings_button.click()
        self.window.poll()
        self.assertFalse(self.window.quitting)
        self.assertEqual(self.window.message_adapter.status, "buttons_connected")
        self.assertEqual(self.worker.jobs, [])

    def test_message_buttons_translate_only_clicked_reply_and_toggle_original(self):
        with patch("twintext.desktop.MessageAdapter", PendingAdapter):
            update_settings(workflow="chat", chat_presentation="floating", message_buttons=True,
                            cache_lifetime="session")
            self.inbox.publish(payload(text="Previously captured answer"), archive=True)
            self.window.poll()
            self.assertEqual(self.worker.jobs, [])
            adapter = self.window.message_adapter
            old = {"document": "doc", "request": 1, "action": "translate", "session": "thread",
                   "message": "old-message", "text": "Exact old English reply"}
            adapter.events.put(old)
            self.window.poll()
            self.assertEqual(self.worker.jobs[-1][1], "Exact old English reply")
            self.deliver_result()
            self.assertIn("译:", self.window.reader.toPlainText())
            self.assertEqual(adapter.feedbacks[-1][1], "ready")
            jobs = len(self.worker.jobs)
            adapter.events.put({**old, "request": 2, "action": "original"})
            self.window.poll()
            self.assertEqual(len(self.worker.jobs), jobs)
            self.assertEqual(self.window.reader.toPlainText(), "Exact old English reply")
            adapter.events.put({**old, "request": 3})
            self.window.poll()
            self.assertEqual(len(self.worker.jobs), jobs, "Repeat clicks reuse a completed result")
            self.window.copy()
            self.assertEqual(self.app.clipboard().text(), "Exact old English reply")
            self.inbox.publish(payload(text="New automatic reply"), archive=True)
            self.window.poll()
            self.assertEqual(self.window.text, old["text"], "New replies must not steal selection")

    def test_message_navigation_cancels_pending_work_and_ignores_old_completion(self):
        with patch("twintext.desktop.MessageAdapter", PendingAdapter):
            update_settings(workflow="chat", chat_presentation="floating", message_buttons=True)
            self.window.poll()
            adapter = self.window.message_adapter
            old = {"document": "doc", "request": 1, "action": "translate", "session": "thread",
                   "message": "old", "text": "Old source"}
            adapter.events.put(old)
            self.window.poll()
            revision = self.worker.jobs[-1][0]
            adapter.events.put({"action": "reset"})
            self.window.poll()
            self.worker.results.put((revision, {"display": "Stale translation"}, None))
            self.window.poll()
            self.assertIsNone(self.window.last_result)
            self.assertEqual(self.window.reader.toPlainText(), "Old source")
            self.assertNotEqual(self.window.status_key, "working")

    def test_disabling_manual_translation_cancels_inflight_message(self):
        with patch("twintext.desktop.MessageAdapter", PendingAdapter):
            update_settings(workflow="chat", chat_presentation="floating", message_buttons=True)
            self.window.poll()
            self.window.message_adapter.events.put({"document": "doc", "request": 1,
                "action": "translate", "session": "thread", "message": "old", "text": "Old source"})
            self.window.poll()
            revision = self.window.revision
            update_settings(enabled=False)
            self.window.poll()
            self.assertGreater(self.window.revision, revision)
            self.assertFalse(self.window.show_translation)
            self.assertNotEqual(self.window.status_key, "working")

    def test_existing_message_click_keeps_dropdown_and_pending_request_in_sync(self):
        with patch("twintext.desktop.MessageAdapter", PendingAdapter):
            update_settings(workflow="chat", chat_presentation="floating", message_buttons=True)
            self.window.poll()
            adapter = self.window.message_adapter
            for index, name in enumerate(("A", "B", "A"), 1):
                adapter.events.put({"document": "doc", "request": index, "action": "translate",
                                    "session": "thread", "message": name, "text": name + " reply"})
                self.window.poll()
                self.assertEqual(self.window.sessions.currentData(), self.window.reply_id)
                self.assertIsNotNone(self.window.message_request)
                self.assertTrue(self.window.show_translation)
            self.window.sessions.setCurrentIndex(0)
            self.assertEqual(self.window.text, "B reply")

    def test_manual_mode_preferences_and_expansion_do_not_trigger_inference(self):
        with patch("twintext.desktop.MessageAdapter", PendingAdapter):
            update_settings(workflow="chat", chat_presentation="floating", message_buttons=True,
                            mode="original")
            self.inbox.publish(payload(), archive=True)
            self.window.poll()
            self.window.select_reply(0)
            update_settings(mode="translated")
            self.window.poll()
            self.window.expand()
            self.assertEqual(self.worker.jobs, [])

    def test_navigation_drain_racing_with_reader_poll_does_not_raise(self):
        with patch("twintext.desktop.MessageAdapter", PendingAdapter):
            update_settings(workflow="chat", chat_presentation="floating", message_buttons=True)
            self.window.poll()
            adapter = self.window.message_adapter
            with patch.object(adapter.events, "empty", return_value=False):
                self.window.poll()  # The producer can drain a previously nonempty queue.

    def test_session_cache_and_button_settings_are_localized_and_saved(self):
        update_settings(workflow="chat", chat_presentation="floating")
        self.window.poll()
        with patch("twintext.desktop.MessageAdapter", PendingAdapter):
            self.window.checks["session_cache"].click()
            self.assertTrue(load_settings().message_buttons)
            self.assertEqual(load_settings().cache_lifetime, "session")
            for language in LANGUAGES:
                self.window.settings = update_settings(ui_language=language)
                self.window.localize()
                self.assertTrue(self.window.checks["enabled"].text())
                self.assertTrue(self.window.checks["session_cache"].text())
                self.assertTrue(self.window.checks["enabled"].isChecked())
                self.assertTrue(self.window.checks["session_cache"].isChecked())

    def test_google_provider_is_localized_and_failure_keeps_original(self):
        self.window.settings = update_settings(provider="google-free", target="zh-TW")
        self.window.localize()
        for language in LANGUAGES:
            self.window.settings = update_settings(ui_language=language)
            self.window.localize()
            combo = self.window.selects["provider"]
            self.assertEqual(combo.currentData(), "google-free")
            self.assertIn("Google", combo.currentText())
            self.assertTrue(self.window.google_notice.text())
            self.assertEqual(self.window.selects["target"].currentData(), "zh-TW")
            self.assertEqual(self.window.selects["ui"].findData("zh-TW"), -1)
        self.click_reply(text="Original answer")
        revision = self.worker.jobs[-1][0]
        self.worker.results.put((revision, None, "Google Free network request failed."))
        self.window.poll()
        self.assertEqual(self.window.reader.toPlainText(), "Original answer")
        self.assertIn("Google Free", self.window.status.text())


    def test_settings_occupy_body_and_back_restores_paste_editor(self):
        self.window.show()
        self.window.paste()
        self.window.settings_button.click()
        self.app.processEvents()
        self.assertTrue(self.window.preference_scroll.isVisible())
        for widget in (self.window.reader, self.window.editor, self.window.sessions,
                       self.window.paste_button, self.window.translate_button,
                       self.window.copy_button, self.window.toggle_button,
                       self.window.clear_button):
            self.assertFalse(widget.isVisible())
        self.assertGreater(self.window.preference_scroll.height(), 360)
        self.window.settings_button.click()
        self.assertTrue(self.window.reader.isVisible())
        self.assertTrue(self.window.editor.isVisible())
        self.assertTrue(self.window.translate_button.isVisible())


    def test_reader_toggle_reuses_translation_without_changing_preferences(self):
        self.window.settings = update_settings(workflow="chat", chat_presentation="floating")
        self.window.localize()
        text = "Original English.\n\n```sh\nnpm test\n```\n"
        self.click_reply(text=text)
        self.deliver_result()
        saved = load_settings()
        jobs = len(self.worker.jobs)
        self.window.toggle_button.click()
        self.assertNotIn("译:", self.window.reader.toPlainText())
        self.window.toggle_button.click()
        self.assertIn("译:Original English", self.window.reader.toPlainText())
        self.assertEqual(len(self.worker.jobs), jobs)
        self.assertEqual(load_settings(), saved)
        self.window.copy()
        self.assertEqual(self.app.clipboard().text(), text)

    def test_reader_toggle_cancels_pending_result_and_can_translate_again(self):
        self.click_reply(text="Hello")
        revision = self.worker.jobs[-1][0]
        with patch.object(self.window, "cancel_translation") as cancel:
            self.window.toggle_button.click()
            cancel.assert_called_once_with()
        self.worker.results.put((revision, self.service.translate("Hello"), None))
        self.window.poll()
        self.assertEqual(self.window.reader.toPlainText(), "Hello")
        self.window.toggle_button.click()
        self.deliver_result()
        self.assertIn("译:Hello", self.window.reader.toPlainText())

    def test_reader_toggle_from_original_mode_and_after_failure(self):
        self.window.settings = update_settings(mode="original")
        self.window.localize()
        self.inbox.publish(payload(text="Hello"), archive=True)
        self.window.poll()
        self.window.sessions.setCurrentIndex(0)
        self.assertFalse(self.worker.jobs)
        self.window.toggle_button.click()
        revision = self.worker.jobs[-1][0]
        self.worker.results.put((revision, None, "No model"))
        self.window.poll()
        self.assertEqual(self.window.reader.toPlainText(), "Hello")
        self.assertEqual(self.window.toggle_button.text(), "Translate")
        self.window.toggle_button.click()
        self.deliver_result()
        self.assertIn("译:Hello", self.window.reader.toPlainText())
        self.assertEqual(load_settings().mode, "original")

    def test_arriving_history_never_replaces_or_translates_the_clicked_reply(self):
        self.click_reply(text="First")
        self.deliver_result()
        jobs = len(self.worker.jobs)
        self.inbox.publish(payload(turn="next", text="Second"), archive=True)
        self.window.poll()
        self.assertEqual(len(self.worker.jobs), jobs)
        self.assertEqual(self.window.text, "First")
        self.window.sessions.setCurrentIndex(0)
        self.assertEqual(self.window.reader.toPlainText(), "Second")
        self.assertEqual(len(self.worker.jobs), jobs)
        self.window.toggle_button.click()
        self.deliver_result()
        self.assertIn("译:Second", self.window.reader.toPlainText())

    def test_floating_chat_button_toggles_reader_and_copy_preserves_original(self):
        self.window.settings = update_settings(workflow="chat", chat_presentation="floating")
        self.window.localize()
        text = "Original English.\n\n```sh\nnpm test\n```\n"
        self.click_reply(text=text)
        self.deliver_result()
        jobs = len(self.worker.jobs)
        self.window.collapse()
        self.window.orb_button.click()
        self.assertTrue(self.window.isVisible())
        self.assertTrue(self.window.orb.isVisible())
        self.assertIn("译:Original English", self.window.reader.toPlainText())
        self.window.copy()
        self.assertEqual(self.app.clipboard().text(), text)
        self.window.orb_button.click()
        self.assertFalse(self.window.isVisible())
        self.assertTrue(self.window.orb.isVisible())
        self.window.orb_button.click()
        self.assertTrue(self.window.isVisible())
        self.assertEqual(len(self.worker.jobs), jobs)

    def test_floating_reader_reuses_saved_translations_for_previous_replies(self):
        self.window.settings = update_settings(workflow="chat", chat_presentation="floating")
        self.window.localize()
        self.click_reply(text="First")
        self.deliver_result()
        self.click_reply(turn="next", text="Second")
        self.deliver_result()
        self.assertEqual(self.window.sessions.count(), 2)
        jobs = len(self.worker.jobs)
        self.window.sessions.setCurrentIndex(1)
        self.window.toggle_button.click()
        self.assertIn("译:First", self.window.reader.toPlainText())
        self.assertEqual(len(self.worker.jobs), jobs)
        Cache().clear()
        self.window.sessions.setCurrentIndex(0)
        self.window.sessions.setCurrentIndex(1)
        self.window.toggle_button.click()
        self.assertIn("译:First", self.window.reader.toPlainText())
        self.assertEqual(len(self.worker.jobs), jobs)

    def test_background_floating_chat_creates_button_without_entering_inline_reader(self):
        update_settings(workflow="chat", chat_presentation="floating")
        with (
            patch("twintext.desktop.desktop_lock") as acquire,
            patch("twintext.desktop.Companion", return_value=self.window),
            patch.object(self.app, "exec", return_value=0) as execute,
        ):
            self.window.settings = load_settings()
            self.assertEqual(run(background=True), 0)
            execute.assert_called_once_with()
            acquire.return_value.close.assert_called_once_with()

    def test_close_quits_both_windows_and_preserves_preferences(self):
        saved = load_settings()
        self.window.show()
        self.window.timer.start(300)
        with patch.object(self.app, "quit") as quit_app:
            self.assertTrue(self.window.close())
            quit_app.assert_called_once_with()
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.window.orb.isVisible())
        self.assertFalse(self.window.timer.isActive())
        self.assertEqual(load_settings(), saved)

    def test_compact_quit_hides_both_windows_and_cancels_translation(self):
        saved = load_settings()
        self.window.collapse()
        with (
            patch.object(self.app, "quit") as quit_app,
            patch.object(self.window, "cancel_translation") as cancel,
        ):
            self.window.orb_quit_button.click()
            quit_app.assert_called_once_with()
            cancel.assert_called_once_with()
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.window.orb.isVisible())
        self.assertEqual(load_settings(), saved)

    def test_native_compact_close_quits_both_windows(self):
        self.window.collapse()
        with patch.object(self.app, "quit") as quit_app:
            self.assertTrue(self.window.orb.close())
            quit_app.assert_called_once_with()
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.window.orb.isVisible())


    def test_manual_reader_in_chat_still_opens_for_settings(self):
        chat = update_settings(workflow="chat")
        self.window.settings = chat
        self.window.localize()

        def execute():
            self.assertTrue(self.window.isVisible())
            self.assertTrue(self.window.orb.isVisible())
            return 0

        with (
            patch("twintext.desktop.desktop_lock") as acquire,
            patch("twintext.desktop.Companion", return_value=self.window),
            patch.object(self.app, "exec", side_effect=execute),
            patch.object(self.app, "quit"),
        ):
            self.assertEqual(run(), 0)
            acquire.return_value.close.assert_called_once_with()

    def test_shutdown_hides_windows_before_releasing_singleton_lock(self):
        def release():
            self.assertFalse(self.window.isVisible())
            self.assertFalse(self.window.orb.isVisible())

        with (
            patch("twintext.desktop.desktop_lock") as acquire,
            patch("twintext.desktop.Companion", return_value=self.window),
            patch.object(self.app, "exec", return_value=0),
        ):
            acquire.return_value.close.side_effect = release
            self.assertEqual(run(background=True), 0)
            acquire.return_value.close.assert_called_once_with()

    def test_wheel_preserves_all_dropdowns_even_when_focused(self):
        self.window.settings = update_settings(workflow="chat")
        self.window.localize()
        self.window.sessions.addItems(["First chat", "Second chat"])
        self.window.show()
        self.window.preference_scroll.show()
        self.app.processEvents()
        for combo in [*self.window.selects.values(), self.window.sessions]:
            combo.setFocus()
            previous = combo.currentData(), combo.currentIndex()
            saved = load_settings()
            pos = combo.rect().center()
            event = QWheelEvent(
                QPointF(pos), QPointF(combo.mapToGlobal(pos)), QPoint(), QPoint(0, -120),
                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                Qt.ScrollPhase.NoScrollPhase, False,
            )
            QApplication.sendEvent(combo, event)
            self.assertEqual((combo.currentData(), combo.currentIndex()), previous)
            self.assertEqual(load_settings(), saved)

    def test_wheel_over_dropdown_scrolls_preferences_without_changing_selection(self):
        self.window.show()
        self.window.resize(480, 560)
        self.window.preference_scroll.show()
        self.app.processEvents()
        bar = self.window.preference_scroll.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        bar.setValue(0)
        combo = self.window.selects["provider"]
        combo.setFocus()
        pos = QPoint(8, combo.height() // 2)
        QTest.wheelEvent(
            self.window.windowHandle(), combo.mapTo(self.window, pos), QPoint(0, -120)
        )
        self.app.processEvents()
        self.assertEqual(combo.currentData(), "offline")
        self.assertGreater(bar.value(), 0)

    def test_dropdown_keyboard_selection_still_works(self):
        combo = self.window.selects["mode"]
        QTest.keyClick(combo, Qt.Key.Key_Down)
        self.assertEqual(combo.currentData(), "translated")
        self.assertEqual(load_settings().mode, "translated")


    def test_provider_selection_status_and_conditional_credentials(self):
        self.assertEqual(self.window.selects["provider"].currentData(), "offline")
        self.assertTrue(self.window.azure_button.isHidden())
        combo = self.window.selects["provider"]
        combo.setCurrentIndex(combo.findData("azure"))
        self.assertEqual(load_settings().provider, "azure")
        self.assertFalse(self.window.azure_button.isHidden())
        self.assertIn("Azure", self.window.offline.text())
        self.assertIn("This month:", self.window.azure_status.text())
        self.assertNotIn("key", self.window.selects)

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {"TWINTEXT_HOME": directory.name})
        environment.start()
        self.addCleanup(environment.stop)
        slot_errors = []
        exception_hook = patch.object(
            sys, "excepthook", lambda kind, value, trace: slot_errors.append(str(value))
        )
        exception_hook.start()
        self.addCleanup(exception_hook.stop)
        self.addCleanup(lambda: self.assertEqual(slot_errors, [], "Qt slot raised an exception"))
        adapter = patch("twintext.desktop.MessageAdapter", PendingAdapter)
        adapter.start()
        self.addCleanup(adapter.stop)
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

    def click_reply(self, text="Hello", turn="first"):
        """An explicit per-reply gesture at the adapter/reader boundary, never auto capture."""
        self.window.poll()
        self.window.message_adapter.events.put({
            "document": "fixture", "request": len(self.worker.jobs) + 1,
            "action": "translate", "session": "test-session", "message": turn, "text": text,
        })
        self.window.poll()

    def test_external_legacy_mode_writes_do_not_remove_buttons_or_quit_reader(self):
        self.window.poll()
        self.window.expand()
        adapter = self.window.message_adapter
        for workflow, presentation in (("chat", "inline"), ("desktop", "inline")):
            saved = load_settings().as_dict()
            saved.update(workflow=workflow, chat_presentation=presentation, message_buttons=False)
            (config_dir() / "settings.json").write_text(json.dumps(saved), encoding="utf-8")
            self.window.poll()
            self.assertFalse(self.window.quitting)
            self.assertTrue(self.window.isVisible())
            self.assertIs(self.window.message_adapter, adapter)
            self.assertEqual(self.worker.jobs, [])

    def deliver_result(self):
        revision, text, source, target = self.worker.jobs[-1]
        result = self.service.translate(text, source=source, target=target, mode="translated")
        self.worker.results.put((revision, result, None))
        self.window.poll()

    def test_clicked_reply_is_bilingual_and_copy_keeps_original(self):
        text = "Hello world.\n\n```sh\nnpm test\n```\n"
        self.click_reply(text=text)
        self.deliver_result()
        self.assertIn("Hello world.", self.window.reader.toPlainText())
        self.assertIn("译:Hello world.", self.window.reader.toPlainText())
        self.assertEqual(self.window.reader.toPlainText().count("npm test"), 1)
        self.window.copy()
        self.assertEqual(self.app.clipboard().text(), text)
        self.assertEqual(self.inbox.replies()[0]["text"], text)

    def test_stale_model_result_does_not_replace_a_newer_reply(self):
        self.click_reply(text="First")
        old_revision = self.worker.jobs[-1][0]
        self.click_reply(turn="second", text="Second")
        self.worker.results.put((old_revision, self.service.translate("First"), None))
        self.window.poll()
        self.assertEqual(self.window.reader.toPlainText(), "Second")
        self.deliver_result()
        self.assertIn("译:Second", self.window.reader.toPlainText())

    def test_partial_progress_is_visible_but_never_saved_as_a_completed_translation(self):
        text = "First paragraph.\n\nSecond paragraph."
        self.click_reply(text=text)
        revision = self.worker.jobs[-1][0]
        progress = []
        final = self.service.translate(text, mode="translated", progress=progress.append)
        self.worker.progress.put((revision, progress[0]))
        self.window.poll()
        self.assertIn("译:First paragraph.", self.window.reader.toPlainText())
        self.assertIn("Second paragraph.", self.window.reader.toPlainText())
        self.assertIn("%", self.window.status.text())
        self.assertIsNone(self.window.last_result)
        self.assertIsNone(self.inbox.translation(*self.window.pending_translation))
        self.window.copy()
        self.assertEqual(self.app.clipboard().text(), text)
        self.worker.results.put((revision, final, None))
        self.window.poll()
        self.assertEqual(self.window.last_result, final)
        self.assertEqual(self.window.status_key, "ready")
        self.assertEqual(self.inbox.translation(*self.window.pending_translation), final)

    def test_stale_partial_results_cannot_replace_a_new_reply_or_original_view(self):
        self.click_reply(text="First paragraph.\n\nSecond paragraph.")
        revision = self.worker.jobs[-1][0]
        progress = []
        self.service.translate(self.window.text, progress=progress.append)
        self.click_reply(turn="next", text="Different answer")
        self.worker.progress.put((revision, progress[0]))
        self.window.poll()
        self.assertEqual(self.window.reader.toPlainText(), "Different answer")
        self.window.toggle_translation()
        self.worker.progress.put((self.window.revision, progress[0]))
        self.window.poll()
        self.assertEqual(self.window.reader.toPlainText(), "Different answer")

    def test_failure_after_partial_output_restores_exact_source(self):
        text = "First paragraph.\n\nSecond paragraph."
        self.click_reply(text=text)
        revision = self.worker.jobs[-1][0]
        progress = []
        self.service.translate(text, progress=progress.append)
        self.worker.progress.put((revision, progress[0]))
        self.window.poll()
        self.worker.results.put((revision, None, "Fixture failure"))
        self.window.poll()
        self.assertEqual(self.window.reader.toPlainText(), "First paragraph.\nSecond paragraph.")
        self.window.copy()
        self.assertEqual(self.app.clipboard().text(), text)
        self.assertIsNone(self.window.last_result)
        self.assertIsNone(self.inbox.translation(*self.window.pending_translation))

    def test_display_modes_switch_without_new_inference_after_translation(self):
        self.click_reply(text="Hello")
        self.deliver_result()
        count = len(self.worker.jobs)
        self.window.selects["mode"].setCurrentIndex(1)
        self.window.toggle_button.click()
        self.assertEqual(self.window.reader.toPlainText(), "译:Hello")
        self.window.selects["mode"].setCurrentIndex(2)
        self.assertEqual(self.window.reader.toPlainText(), "Hello")
        self.window.selects["mode"].setCurrentIndex(0)
        self.window.toggle_button.click()
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
        self.click_reply(text="Hello")
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
        self.assertTrue(self.window.orb.isVisible())
        self.assertTrue(self.window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.assertIsNone(self.window.reader.loadResource(2, "https://example.com/image.png"))

    def test_table_renders_and_copy_modes_preserve_rows_and_numbers(self):
        self.click_reply(text=TABLE)
        self.deliver_result()
        plain = self.window.reader.toPlainText()
        self.assertIn("译:Fresh red apples", plain)
        self.assertIn("Fresh red apples", plain)
        self.assertEqual(plain.count("Whole wheat loaf"), 2)
        self.window.copy()
        self.assertEqual(self.app.clipboard().text(), TABLE)
        self.window.selects["mode"].setCurrentIndex(1)
        self.window.toggle_button.click()
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
            self.assertTrue(self.window.orb.isVisible())
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
