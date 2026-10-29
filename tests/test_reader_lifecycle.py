"""Exercise window dismissal and recovery through a real Qt process/event loop."""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class ReaderLifecycleTests(unittest.TestCase):
    def test_close_reopen_and_explicit_quit_without_restarting_the_reader_process(self):
        probe = textwrap.dedent('''
            import sys
            from unittest.mock import patch
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication
            from test_desktop import PendingAdapter, PendingTranslator
            from twintext.desktop import Companion, run

            app = QApplication([])
            completed = []
            errors = []
            def fail(kind, value, trace):
                errors.append(str(value))
                app.exit(1)
            sys.excepthook = fail
            worker = PendingTranslator()
            with patch("twintext.desktop.MessageAdapter", PendingAdapter):
                window = Companion(translator=worker)
                adapter = window.message_adapter
                def reopen():
                    assert not window.isVisible() and not window.orb.isVisible()
                    assert window.timer.isActive() and not window.quitting
                    assert window.message_adapter is adapter
                    adapter.events.put({
                        "document": "fixture", "request": 1, "action": "translate",
                        "session": "thread", "message": "reply", "text": "Exact reply",
                    })
                    window.poll()
                    assert window.isVisible() and window.reader_open
                    assert worker.jobs[-1][1] == "Exact reply"
                    completed.append("reply reopened")
                    window.orb.close()
                    assert not window.isVisible() and not window.orb.isVisible()
                    assert run() == 0  # Existing singleton requests activation, no second UI.
                    window.poll()
                    assert window.isVisible() and len(worker.jobs) == 1
                    completed.append("launcher reopened")
                    window.quit_button.click()
                    completed.append("quit")
                def dismiss():
                    assert window.isVisible()
                    window.close_button.click()
                    completed.append("hidden")
                    QTimer.singleShot(50, reopen)
                QTimer.singleShot(0, dismiss)
                QTimer.singleShot(5000, lambda: app.exit(2))
                with patch("twintext.desktop.Companion", return_value=window):
                    assert run() == 0
            assert not errors, errors
            assert completed == ["hidden", "reply reopened", "launcher reopened", "quit"], completed
            assert window.quitting and not window.timer.isActive()
            print("Real Qt process: close, reply recovery, singleton activation and Quit passed")
        ''')
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, "-c", probe], cwd=Path(__file__).parent,
                env={**os.environ, "TWINTEXT_HOME": folder, "QT_QPA_PLATFORM": "offscreen"},
                text=True, capture_output=True, timeout=15,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Real Qt process:", result.stdout)
