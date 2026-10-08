import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from twintext.bridge import MAX_SESSIONS, Inbox, capture, desktop_lock, desktop_running
from twintext.config import update_settings

ROOT = Path(__file__).resolve().parents[1]


def payload(session="one", turn="first", text="Hello `npm test`."):
    return {
        "hook_event_name": "Stop",
        "session_id": session,
        "turn_id": turn,
        "last_assistant_message": text,
    }


class BridgeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {"TWINTEXT_HOME": directory.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.inbox = Inbox()
        update_settings(desktop_auto_start=False)

    def test_latest_reply_per_session_is_exact_and_duplicate_event_is_ignored(self):
        text = "# Reply\n\n中文 `npm test`\n\n```sh\nprintf 'hello'\n```"
        self.assertTrue(self.inbox.publish(payload(text=text)))
        self.assertFalse(self.inbox.publish(payload(text=text)))
        self.assertEqual(self.inbox.replies()[0]["text"], text)
        self.inbox.publish(payload(turn="next", text="Next"))
        self.assertEqual(len(self.inbox.replies()), 1)
        self.assertEqual(self.inbox.replies()[0]["text"], "Next")
        if os.name != "nt":
            self.assertEqual(self.inbox.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.inbox.path.parent.stat().st_mode & 0o777, 0o700)

    def test_bounded_concurrent_sessions_and_clear(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda n: self.inbox.publish(payload(session=str(n))), range(40)))
        self.assertEqual(len(self.inbox.replies()), MAX_SESSIONS)
        self.inbox.clear()
        self.assertEqual(self.inbox.replies(), [])

    def test_bad_missing_and_oversized_payloads_do_not_capture(self):
        for value in (
            [],
            {},
            payload(text=None),
            payload(text=""),
            payload(text="a" * 100001),
            {**payload(), "hook_event_name": "UserPromptSubmit"},
        ):
            self.assertFalse(self.inbox.publish(value))
        for value in ("bad JSON", "[]", "a" * 1_100_001):
            capture(io.StringIO(value))
        self.assertEqual(self.inbox.replies(), [])

    def test_disabled_capture_does_not_store_or_launch(self):
        update_settings(enabled=False)
        with patch("twintext.bridge.launch_desktop") as launch:
            capture(io.StringIO(json.dumps(payload())))
            launch.assert_not_called()
        self.assertEqual(self.inbox.replies(), [])

    def test_background_launch_happens_only_for_a_new_event_when_enabled(self):
        update_settings(desktop_auto_start=True)
        with patch("twintext.bridge.launch_desktop") as launch:
            capture(io.StringIO(json.dumps(payload())))
            capture(io.StringIO(json.dumps(payload())))
            launch.assert_called_once_with(background=True)

    def test_stop_hook_preserves_stdin_and_returns_no_model_context(self):
        with patch.dict(os.environ, {"TWINTEXT_PYTHON": sys.executable}):
            result = subprocess.run(
                [sys.executable, str(ROOT / "plugins/twintext/hooks/capture.py")],
                input=json.dumps(payload(text="A reply with $(literal) and `code`.")),
                text=True,
                capture_output=True,
                timeout=10,
                check=True,
            )
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(result.stderr, "")
        self.assertEqual(self.inbox.replies()[0]["text"], "A reply with $(literal) and `code`.")

    def test_singleton_lock_and_activation(self):
        lock = desktop_lock()
        self.addCleanup(lock.close)
        self.assertTrue(desktop_running())
        self.assertIsNone(desktop_lock())
        self.inbox.activate()
        revision = self.inbox.activation()
        self.inbox.activate()
        self.assertEqual(self.inbox.activation(), revision + 1)


if __name__ == "__main__":
    unittest.main()
