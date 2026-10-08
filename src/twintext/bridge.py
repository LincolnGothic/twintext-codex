"""Bounded local inbox between the Codex Stop hook and the desktop companion.

No model calls, transcript edits, network listeners, or translated hook output.
"""

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from twintext.config import TwinTextError, data_dir, load_settings, private_dir
from twintext.locking import acquire_lock
from twintext.service import MAX_TEXT_LENGTH

MAX_SESSIONS = 24
MAX_HOOK_BYTES = 1_100_000


class Inbox:
    def __init__(self):
        self.path = private_dir(data_dir() / "desktop") / "inbox.sqlite3"

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=5)
        self.path.chmod(0o600)
        connection.row_factory = sqlite3.Row
        try:
            # Reserve the writer before reading: concurrent read-then-write upgrades
            # can otherwise deadlock without honoring SQLite's busy timeout.
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS replies ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, session TEXT UNIQUE NOT NULL, "
                "turn TEXT NOT NULL, text TEXT NOT NULL, created REAL NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS control (id INTEGER PRIMARY KEY, revision INTEGER)"
            )
            with connection:
                yield connection
        finally:
            connection.close()

    def publish(self, payload):
        if not isinstance(payload, dict) or payload.get("hook_event_name") != "Stop":
            return False
        text = payload.get("last_assistant_message")
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_LENGTH:
            return False
        session = str(payload.get("session_id") or "codex")[:256]
        turn = str(payload.get("turn_id") or "")[:256]
        with self.connection() as connection:
            existing = connection.execute(
                "SELECT turn, text FROM replies WHERE session = ?", (session,)
            ).fetchone()
            if existing and existing["turn"] == turn and existing["text"] == text:
                return False
            connection.execute("DELETE FROM replies WHERE session = ?", (session,))
            connection.execute(
                "INSERT INTO replies (session, turn, text, created) VALUES (?, ?, ?, ?)",
                (session, turn, text, time.time()),
            )
            connection.execute(
                "DELETE FROM replies WHERE id NOT IN "
                "(SELECT id FROM replies ORDER BY id DESC LIMIT ?)",
                (MAX_SESSIONS,),
            )
        return True

    def replies(self):
        with self.connection() as connection:
            return [
                dict(row) for row in connection.execute("SELECT * FROM replies ORDER BY id DESC")
            ]

    def clear(self):
        with self.connection() as connection:
            connection.execute("DELETE FROM replies")

    def activate(self):
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO control VALUES (1, 1) "
                "ON CONFLICT(id) DO UPDATE SET revision = revision + 1"
            )

    def activation(self):
        with self.connection() as connection:
            row = connection.execute("SELECT revision FROM control WHERE id = 1").fetchone()
            return row[0] if row else 0


def desktop_lock():
    path = private_dir(data_dir() / "desktop") / "window.lock"
    return acquire_lock(path, blocking=False)


def desktop_running():
    lock = desktop_lock()
    if lock is None:
        return True
    lock.close()
    return False


def launch_desktop(background=False):
    if desktop_running():
        if not background:
            Inbox().activate()
        return {"running": True, "started": False}
    if (
        sys.platform != "win32"
        and not os.environ.get("DISPLAY")
        and not os.environ.get("WAYLAND_DISPLAY")
    ):
        raise TwinTextError("Open TwinText Desktop inside your Linux graphical session.")
    if importlib.util.find_spec("PySide6") is None:
        raise TwinTextError("Install TwinText's desktop extra or rerun scripts/install-linux.sh.")
    folder = private_dir(data_dir() / "desktop")
    log = folder / "window.log"
    if log.exists() and log.stat().st_size > 1_000_000:
        log.unlink()
    with log.open("a", encoding="utf-8") as errors:
        log.chmod(0o600)
        interpreter = sys.executable
        if sys.platform == "win32":
            windowless = str(Path(interpreter).with_name("pythonw.exe"))
            if Path(windowless).exists():
                interpreter = windowless
        command = [interpreter, "-m", "twintext.cli", "desktop"]
        if background:
            command.append("--background")
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
            start_new_session=True,
        )
    return {"running": True, "started": True, "pid": process.pid}


def capture(stream):
    """Fail open and return no text/context to Codex, including on malformed input."""
    try:
        raw = stream.read(MAX_HOOK_BYTES + 1)
        if len(raw.encode("utf-8")) > MAX_HOOK_BYTES:
            return
        payload = json.loads(raw)
        settings = load_settings()
        if settings.workflow != "desktop":
            return
        if settings.enabled and Inbox().publish(payload) and settings.desktop_auto_start:
            launch_desktop(background=True)
    except (TwinTextError, OSError, ValueError, TypeError, sqlite3.Error):
        pass
