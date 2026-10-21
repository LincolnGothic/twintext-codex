import contextlib
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

from twintext.bridge import Inbox
from twintext.cache import Cache
from twintext.cli import main
from twintext.config import TwinTextError, load_settings, update_settings
from twintext.service import Service


class SessionCacheTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        env = patch.dict(os.environ, TWINTEXT_HOME=folder.name)
        env.start()
        self.addCleanup(env.stop)
        self.engine = FakeEngine()
        self.service = Service(self.engine, detector=lambda text: "en")
        update_settings(target="zh")

    def test_lifetime_saves_restores_and_rejects_invalid_value(self):
        update_settings(cache_lifetime="session")
        self.assertEqual(load_settings().cache_lifetime, "session")
        with self.assertRaises(TwinTextError):
            update_settings(cache_lifetime="forever")
        self.assertEqual(load_settings().cache_lifetime, "session")

    def test_session_translation_reuses_fragments_without_touching_disk_cache(self):
        self.service.translate("Existing disk result")
        before = (self.folder / "translations.sqlite3").read_bytes()
        update_settings(cache_lifetime="session")
        self.service.translate("Existing disk result")
        self.service.translate("New session result")
        self.assertEqual(self.service.translate("New session result")["cache_hits"], 1)
        self.assertEqual(self.engine.calls.count("Existing disk result"), 2)
        self.assertEqual((self.folder / "translations.sqlite3").read_bytes(), before)

    def test_cli_restores_manual_and_session_preferences(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["settings", "--cache-lifetime", "session"]), 0)
        self.assertTrue(json.loads(output.getvalue())["message_buttons"])
        self.assertEqual(load_settings().cache_lifetime, "session")

    def test_memory_cache_is_shared_within_process_bounded_and_lost_on_restart(self):
        cache = Cache(memory=True)
        for index in range(10001):
            cache.put(str(index), "value")
        self.assertIsNone(Cache(memory=True).get("0"))
        self.assertEqual(Cache(memory=True).get("10000"), "value")
        child = subprocess.run(
            [sys.executable, "-c", "from twintext.cache import Cache; "
             "print(Cache(memory=True).get('10000'))"],
            check=True, capture_output=True, text=True,
        )
        self.assertEqual(child.stdout.strip(), "None")
        self.assertFalse((self.folder / "translations.sqlite3").exists())

    def test_reader_session_results_never_read_or_write_saved_translations(self):
        inbox = Inbox()
        inbox.publish(payload(), archive=True)
        reply = inbox.history()[0]["id"]
        args = (reply, "offline", "en", "zh")
        inbox.save_translation(*args, {"translation": "old disk"})
        update_settings(cache_lifetime="session")
        self.assertIsNone(inbox.translation(*args))
        inbox.save_translation(*args, {"translation": "new memory"})
        self.assertEqual(inbox.translation(*args), {"translation": "new memory"})
        with inbox.connection() as db:
            rows = list(db.execute("SELECT result FROM history_translations"))
        self.assertEqual([json.loads(row[0]) for row in rows], [{"translation": "old disk"}])
        update_settings(cache=False)
        self.assertIsNone(inbox.translation(*args))
        inbox.save_translation(*args, {"translation": "disabled"})
        update_settings(cache=True)
        self.assertEqual(inbox.translation(*args), {"translation": "new memory"})

    def test_clear_translations_clears_both_caches_but_preserves_original_history(self):
        inbox = Inbox()
        inbox.publish(payload(), archive=True)
        reply = inbox.history()[0]["id"]
        args = (reply, "offline", "en", "zh")
        self.service.translate("Hello")
        inbox.save_translation(*args, {"translation": "saved"})
        update_settings(cache_lifetime="session")
        self.service.translate("Hello")
        inbox.save_translation(*args, {"translation": "session"})
        inbox.clear_translations()
        self.assertIsNone(inbox.translation(*args))
        self.assertEqual(self.service.translate("Hello")["cache_hits"], 0)
        update_settings(cache_lifetime="disk")
        self.assertIsNone(inbox.translation(*args))
        self.assertEqual(self.service.translate("Hello")["cache_hits"], 0)
        self.assertEqual(len(inbox.history()), 1)
