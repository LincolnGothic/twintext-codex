"""Offline real-model Markdown + Qt smoke test in an isolated temporary inbox."""

import json
import os
import queue
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from markdown_it import MarkdownIt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from twintext.cache import Cache  # noqa: E402
from twintext.config import data_dir, update_settings  # noqa: E402
from twintext.desktop import Companion  # noqa: E402
from twintext.service import Service  # noqa: E402

models = data_dir() / "argos/packages"
output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path("/tmp/twintext-formats")
output.mkdir(parents=True, exist_ok=True)
text = (
    "## Shopping list\n\n"
    "| Item | Description | Quantity |\n"
    "| :--- | --- | ---: |\n"
    "| Apples | Fresh red apples | 5 |\n"
    "| Bread | Whole wheat loaf | 2 |\n"
    "| Milk | One-liter bottle | 1 |\n\n"
    "- [ ] Read the [installation guide](https://example.com/guide).\n"
    "    - Save the file in `/tmp/example.py`.\n\n"
    "> **Note:** Please check the quantities.\n\n"
    "```sh\nprintf 'hello'\n```\n"
)
with tempfile.TemporaryDirectory(prefix="twintext-formats-") as directory:
    folder = Path(directory)
    (folder / "argos").mkdir()
    (folder / "argos/packages").symlink_to(models)
    with patch.dict(os.environ, {"TWINTEXT_HOME": directory}):
        update_settings(target="zh", source="en", desktop_auto_start=False, cache=False)
        service = Service()
        report = []
        parser = MarkdownIt("commonmark").enable("table")
        result = None
        for target in ("zh", "ja", "fr", "es"):
            start = time.monotonic()
            value = service.translate(text, source="en", target=target, mode="translated")
            translated = value["translation"]
            assert translated != text
            assert "https://example.com/guide" in translated
            assert "`/tmp/example.py`" in translated
            assert translated.count("printf 'hello'") == 1
            assert "| :--- | --- | ---: |" in translated
            assert {"zh": "数量", "ja": "数量", "fr": "Quantité", "es": "Cantidad"}[
                target
            ] in translated
            tokens = parser.parse(translated)
            assert sum(t.type == "th_open" for t in tokens) == 3
            assert sum(t.type == "td_open" for t in tokens) == 9
            report.append(
                {
                    "target": target,
                    "seconds": round(time.monotonic() - start, 2),
                    "table_rows_preserved": True,
                    "translation": translated,
                }
            )
            if target == "zh":
                result = value
        app = QApplication([])
        window = Companion(
            translator=type(
                "Worker",
                (),
                {"results": queue.SimpleQueue(), "submit": lambda *args: None},
            )()
        )
        window.timer.stop()
        window.inbox.publish(
            {
                "hook_event_name": "Stop",
                "session_id": "demo-formats",
                "turn_id": "demo",
                "last_assistant_message": text,
            }
        )
        window.poll()
        window.last_result = result
        window.text = text
        window.copy_button.setEnabled(True)
        window.status_key = "ready"
        window.update_status()
        window.show()
        for mode in ("bilingual", "translated"):
            window.selects["mode"].setCurrentIndex(window.selects["mode"].findData(mode))
            window.render_result()
            app.processEvents()
            plain = window.reader.toPlainText()
            assert plain.count("printf 'hello'") == 1
            assert (
                "Fresh red apples" in plain
                if mode == "bilingual"
                else "Fresh red apples" not in plain
            )
            assert "项目" in plain or "物品" in plain
            assert window.grab().save(str(output / f"{mode}.png"))
        window.preferences.show()
        app.processEvents()
        assert window.grab().save(str(output / "settings.png"))
        window.collapse()
        app.processEvents()
        assert window.orb.grab().save(str(output / "orb.png"))
        # Measure logical deletion, without touching the user's actual cache.
        cache = Cache()
        with cache.connect() as con:
            con.executemany(
                "INSERT INTO translations VALUES (?, ?, ?)",
                [(f"demo-{i}", "示例翻译", i) for i in range(10000)],
            )
        start = time.monotonic()
        window.clear_cache()
        elapsed = time.monotonic() - start
        with sqlite3.connect(cache.path) as con:
            assert con.execute("SELECT COUNT(*) FROM translations").fetchone()[0] == 0
        metadata = {
            "directions": report,
            "gui_modes_passed": ["bilingual", "translated"],
            "cache_clear_10000_seconds": round(elapsed, 4),
            "screenshots": str(output),
        }
        (output / "results.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        print(json.dumps({k: v for k, v in metadata.items() if k != "directions"}))
        print(json.dumps([{k: v for k, v in row.items() if k != "translation"} for row in report]))
        window.hide()
        window.orb.hide()
