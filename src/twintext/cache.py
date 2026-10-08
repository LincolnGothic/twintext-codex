"""Bounded local translation cache; original text is represented by a digest."""

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager

from twintext.config import data_dir, private_dir


class Cache:
    def __init__(self):
        self.path = private_dir(data_dir()) / "translations.sqlite3"

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS translations "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL, used INTEGER NOT NULL)"
            )
            self.path.chmod(0o600)
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def key(text: str, source: str, target: str, fingerprint: str):
        raw = json.dumps([text, source, target, fingerprint], ensure_ascii=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, key: str):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM translations WHERE key=?", (key,)
            ).fetchone()
            if row:
                connection.execute(
                    "UPDATE translations SET used=? WHERE key=?", (int(time.time()), key)
                )
            return row[0] if row else None

    def put(self, key: str, value: str):
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO translations VALUES (?, ?, ?)",
                (key, value, int(time.time())),
            )
            connection.execute(
                "DELETE FROM translations WHERE key IN "
                "(SELECT key FROM translations ORDER BY used DESC, rowid DESC "
                "LIMIT -1 OFFSET 10000)"
            )

    def clear(self):
        with self.connect() as connection:
            connection.execute("DELETE FROM translations")
