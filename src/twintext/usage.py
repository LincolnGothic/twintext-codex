"""Local monthly cloud submission counts. Never stores text or credentials."""

import json
import os
import tempfile
from datetime import date
from pathlib import Path

from twintext.config import TwinTextError, data_dir, private_dir
from twintext.locking import file_lock


class CloudUsage:
    def __init__(self, today=date.today):
        self.today = today

    def snapshot(self):
        month = self.today().strftime("%Y-%m")
        path = data_dir() / "cloud-usage.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if value.get("month") == month:
                return {
                    "month": month,
                    "requests": int(value["requests"]),
                    "characters": int(value["characters"]),
                }
            return {"month": month, "requests": 0, "characters": 0}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise TwinTextError("Cannot read cloud usage. Check cloud-usage.json.") from None

    def record(self, characters):
        folder = private_dir(data_dir())
        with file_lock(folder / "cloud-usage.lock"):
            value = self.snapshot()
            value["requests"] += 1
            value["characters"] += characters
            fd, temporary = tempfile.mkstemp(prefix="cloud-usage-", dir=folder)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(value, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, folder / "cloud-usage.json")
            finally:
                Path(temporary).unlink(missing_ok=True)


def usage_label(value):
    return f"This month: {value['requests']:,} requests · {value['characters']:,} characters"
