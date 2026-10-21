import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from twintext.bridge import Inbox, capture, send_to_reader
from twintext.cli import parser
from twintext.config import TwinTextError, load_settings, update_settings
from twintext.mcp import call_tool
from twintext.service import Service, context


class ManualOnlyTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        environment = patch.dict(os.environ, TWINTEXT_HOME=folder.name)
        environment.start()
        self.addCleanup(environment.stop)

    def test_new_profile_never_automatically_captures_or_forwards_a_reply(self):
        with patch("twintext.bridge.launch_desktop"):
            capture(io.StringIO(json.dumps({"hook_event_name": "Stop",
                                           "last_assistant_message": "Unrequested reply"})))
        self.assertFalse(send_to_reader("Unrequested progress")["received"])
        self.assertEqual(Inbox().history(), [])
        self.assertEqual(Inbox().replies(), [])
        self.assertTrue(load_settings().manual_reader)

    def test_each_valid_legacy_profile_migrates_without_losing_unrelated_preferences(self):
        for workflow, presentation, buttons in (("desktop", "inline", False),
                                                ("chat", "inline", False),
                                                ("chat", "floating", False)):
            with self.subTest(workflow=workflow, presentation=presentation):
                path = self.folder / "settings.json"
                path.write_text(json.dumps({
                    "workflow": workflow, "chat_presentation": presentation,
                    "message_buttons": buttons, "provider": "google-free", "target": "zh-TW",
                    "source": "auto", "mode": "translated", "ui_language": "fr",
                    "enabled": False, "cache_lifetime": "session", "future_field": {"keep": 7},
                }), encoding="utf-8")
                self.assertTrue(load_settings().manual_reader)
                saved = update_settings()
                self.assertEqual((saved.workflow, saved.chat_presentation, saved.message_buttons),
                                 ("chat", "floating", True))
                self.assertEqual((saved.provider, saved.target, saved.mode, saved.ui_language),
                                 ("google-free", "zh-TW", "translated", "fr"))
                self.assertFalse(saved.enabled)
                self.assertEqual(saved.cache_lifetime, "session")
                self.assertEqual(json.loads(path.read_text())["future_field"], {"keep": 7})

    def test_legacy_inline_profile_cannot_instruct_automatic_in_chat_translation(self):
        (self.folder / "settings.json").write_text(
            '{"workflow":"chat","chat_presentation":"inline","target":"zh"}',
            encoding="utf-8",
        )
        instructions = context()
        self.assertIn("manual per-message", instructions)
        self.assertIn("Keep assistant messages in their original language", instructions)
        self.assertNotIn("present its display verbatim", instructions)

    def test_public_settings_cannot_reactivate_removed_methods(self):
        for key, value in (("workflow", "desktop"), ("chat_presentation", "inline"),
                           ("message_buttons", False), ("response_scope", "all"),
                           ("translate_questions", True), ("desktop_auto_start", True)):
            with self.subTest(key=key), self.assertRaisesRegex(TwinTextError, "Unexpected"):
                call_tool("twintext_set_settings", {key: value}, Service())
        for arguments in (("settings", "--workflow", "desktop"), ("send-to-reader",)):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parser().parse_args(arguments)

    def test_legacy_desktop_originals_are_available_in_manual_history_after_upgrade(self):
        inbox = Inbox()
        inbox.publish({"hook_event_name": "Stop", "last_assistant_message": "Old desktop reply",
                       "session_id": "old-chat", "turn_id": "old-turn"})
        original = inbox.replies()[0]
        reopened = Inbox()
        rows = reopened.history()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["text"], rows[0]["created"]),
                         ("Old desktop reply", original["created"]))
        self.assertEqual(Inbox().history(), rows, "Reopening must not duplicate migrated history")
        self.assertEqual(reopened.replies()[0], original)

    def test_migrated_originals_keep_chronological_order_with_existing_history(self):
        inbox = Inbox()
        inbox.publish({"hook_event_name": "Stop", "last_assistant_message": "Older desktop",
                       "session_id": "desktop", "turn_id": "old"})
        inbox.publish({"hook_event_name": "Stop", "last_assistant_message": "Newer reader",
                       "session_id": "reader", "turn_id": "new"}, archive=True)
        with inbox.connection() as connection:
            connection.execute("UPDATE replies SET created = 100 WHERE session = 'desktop'")
            connection.execute("UPDATE history SET created = 200 WHERE session = 'reader'")
        self.assertEqual([row["text"] for row in Inbox().history()],
                         ["Newer reader", "Older desktop"])


if __name__ == "__main__":
    unittest.main()
