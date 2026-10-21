"""Exercise the release installer, native hooks and a real offline table translation."""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = (
    "| Item | Description | Quantity |\n| --- | --- | ---: |\n| Apples | Fresh red apples | 5 |\n"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("windows", "linux"), required=True)
    args = parser.parse_args()
    version = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)[1]
    name = f"TwinText-{version}-{args.platform}"
    if os.environ.get("GITHUB_ACTIONS") != "true":
        parser.error("Run this installer smoke only on an ephemeral GitHub Actions runner.")
    with tempfile.TemporaryDirectory(prefix="twintext-installer-", dir=Path.home()) as folder:
        base = Path(folder)
        with zipfile.ZipFile(ROOT / f"dist/{name}.zip") as archive:
            archive.extractall(base)
        source = base / name
        environment = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        # Data/config are isolated; personal registration is restricted to this
        # ephemeral Actions runner, never run this smoke against a user's account.
        environment.update(
            LOCALAPPDATA=str(base / "Local"),
            APPDATA=str(base / "Roaming"),
            XDG_DATA_HOME=str(base / "data"),
            XDG_CONFIG_HOME=str(base / "config"),
        )
        windows = args.platform == "windows"
        installer = (
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(source / "scripts/install-windows.ps1"),
                "-Python",
                sys.executable,
            ]
            if windows
            else [sys.executable, str(source / "scripts/install.py")]
        )
        subprocess.run(installer, env=environment, check=True, timeout=600)
        app = base / ("Local/TwinText" if windows else "data/twintext")
        python = str(app / ("venv/Scripts/python.exe" if windows else "venv/bin/python"))
        if not windows:
            launcher = app / "Open Codex with TwinText.sh"
            assert launcher.is_file() and os.access(launcher, os.X_OK)
            assert "codex-launch --wait" in launcher.read_text(encoding="utf-8")
            entry = base / "data/applications/twintext-codex.desktop"
            assert "Name=Codex with TwinText" in entry.read_text(encoding="utf-8")
            assert "Terminal=true" in entry.read_text(encoding="utf-8")
            subprocess.run(["sh", "-n", str(launcher)], check=True, timeout=10)

        def run(*command, text=None):
            return subprocess.run(
                [python, "-m", "twintext.cli", *command],
                env=environment,
                input=text,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
                timeout=300,
            )

        settings = json.loads(run("settings").stdout)
        assert settings["workflow"] == "chat" and settings["chat_presentation"] == "floating"
        assert settings["message_buttons"] is True, settings
        assert not (app / "argos/packages").exists(), "Installer downloaded models unexpectedly"
        run("models", "install", "--source", "en", "--target", "zh")
        run("settings", "--target", "zh", "--source", "en")
        for mode in ("bilingual", "translated"):
            result = json.loads(run("translate", "--mode", mode, "--json", text=TABLE).stdout)
            assert result["translation"] != TABLE
            assert "数量" in result["translation"]
            assert "| 5 |" in result["translation"]
            assert (
                "Item" in result["display"]
                if mode == "bilingual"
                else "Item" not in result["display"]
            )
        hooks = json.loads((app / "plugin/hooks/hooks.json").read_text())["hooks"]
        environment["PLUGIN_ROOT"] = str(app / "plugin")
        assert set(hooks) == {"SessionStart", "UserPromptSubmit"}
        for event in hooks:
            command = hooks[event][0]["hooks"][0]["commandWindows" if windows else "command"]
            command = command.replace("${PLUGIN_ROOT}", str(app / "plugin"))
            payload = json.dumps({"hook_event_name": event, "session_id": "smoke"})
            reply = subprocess.run(
                command, shell=True, input=payload, text=True, encoding="utf-8",
                capture_output=True, check=True, env=environment, timeout=30,
            )
            value = json.loads(reply.stdout)
            assert "manual per-message" in value["hookSpecificOutput"]["additionalContext"]
        compatibility = subprocess.run(
            [python, str(app / "plugin/hooks/capture.py")], input="{}", text=True,
            capture_output=True, check=True, env=environment, timeout=10,
        )
        assert json.loads(compatibility.stdout) == {}
        # Verify actual native Qt rendering with the installed environment.
        probe = (
            "from PySide6.QtWidgets import QApplication; from twintext.desktop import Companion; "
            "from types import SimpleNamespace; import queue; "
            "from unittest.mock import patch; "
            "adapter=patch('twintext.desktop.MessageAdapter', return_value=None); adapter.start(); "
            "app=QApplication([]); worker=SimpleNamespace(submit=lambda *args: None, "
            "results=queue.SimpleQueue()); window=Companion(translator=worker); "
            "assert 'location' not in window.selects; assert window.settings.manual_reader; "
            "window.reader.setMarkdown(" + repr(TABLE) + "); "
            "assert 'Fresh red apples' in window.reader.toPlainText(); "
            "window.quit(); adapter.stop(); print('Native Qt and manual hooks passed')"
        )
        subprocess.run([python, "-c", probe], env=environment, check=True, timeout=30)
        # An upgrade must retain independent preferences and existing models.
        run("settings", "--ui-language", "fr", "--mode", "translated",
            "--cache-lifetime", "session", "--follow-codex", "true")
        upgrade = [*installer, "-WithoutEngine"] if windows else [*installer, "--without-engine"]
        subprocess.run(upgrade, env=environment, check=True, timeout=300)
        final = json.loads(run("settings").stdout)
        assert final["workflow"] == "chat" and final["message_buttons"]
        assert final["ui_language"] == "fr" and final["mode"] == "translated"
        assert final["cache_lifetime"] == "session"
        assert final["follow_codex"] is True
        assert len(json.loads(run("models", "list").stdout)) == 1
        print(f"{args.platform}: installer, preservation, hooks, UTF-8, tables and Qt passed")


if __name__ == "__main__":
    main()
