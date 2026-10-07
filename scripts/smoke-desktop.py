"""Offscreen hook → inbox → real model → Qt reader smoke check; no model requests."""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication  # noqa: E402

from twintext.bridge import Inbox  # noqa: E402
from twintext.config import data_dir, update_settings  # noqa: E402
from twintext.desktop import Companion  # noqa: E402

root = Path(__file__).resolve().parents[1]
models = data_dir() / "argos/packages"
output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "docs/desktop.png"
with tempfile.TemporaryDirectory(prefix="twintext-desktop-smoke-") as directory:
    folder = Path(directory)
    (folder / "argos").mkdir()
    (folder / "argos/packages").symlink_to(models)
    with patch.dict(
        os.environ,
        {
            "TWINTEXT_HOME": directory,
            "TWINTEXT_PYTHON": sys.executable,
        },
    ):
        update_settings(desktop_auto_start=False)
        message = (
            "# Votre programme est prêt\n\n"
            "Le programme fonctionne maintenant. Veuillez enregistrer le fichier.\n\n"
            "Exécutez `npm test` pour vérifier les modifications.\n\n"
            "```sh\nnpm test\n```\n"
        )
        payload = {
            "hook_event_name": "Stop",
            "session_id": "demo-french",
            "turn_id": "demo",
            "last_assistant_message": message,
        }
        hook = subprocess.run(
            [sys.executable, str(root / "plugins/twintext/hooks/capture.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
        assert json.loads(hook.stdout) == {} and not hook.stderr
        app = QApplication([])
        window = Companion()
        window.show()
        deadline = time.monotonic() + 90
        while window.last_result is None and time.monotonic() < deadline:
            app.processEvents()
            window.poll()
            if window.status_key == "error":
                raise RuntimeError(window.status.text())
            time.sleep(0.05)
        assert window.last_result is not None, "Timed out waiting for the local model"
        assert window.last_result["source"] == "fr"
        assert window.last_result["target"] == "en"
        assert window.last_result["translation"] != message
        assert "npm test" in window.last_result["translation"]
        assert Inbox().replies()[0]["text"] == message
        assert window.reader.toPlainText().count("npm test") == 3
        app.processEvents()
        output.parent.mkdir(parents=True, exist_ok=True)
        assert window.grab().save(str(output))
        window.selects["mode"].setCurrentIndex(1)
        assert "Le programme fonctionne" not in window.reader.toPlainText()
        print(
            json.dumps(
                {
                    "hook_output": {},
                    "source": "fr",
                    "target": "en",
                    "desktop_rendered": True,
                    "screenshot": str(output),
                },
                indent=2,
            )
        )
        window.hide()
        window.orb.hide()
