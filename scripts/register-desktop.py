"""Install per-user reader and Codex launchers without touching app/system files."""

import os
import shlex
import sys
from pathlib import Path

from twintext.config import config_dir, data_dir


def desktop_quote(value):
    value = str(value)
    for character in ("\\", '"', "`", "$"):
        value = value.replace(character, "\\" + character)
    # Desktop string escapes are decoded before the Exec argument quoting.
    return '"' + value.replace("\\", "\\\\").replace("%", "%%") + '"'


def register(app):
    app = app.resolve()
    settings, data = config_dir().resolve(), data_dir().resolve()
    if any(char in str(path) for path in (app, settings, data) for char in "\n\r"):
        raise ValueError("TwinText paths must not contain newlines.")
    folder = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    folder /= "applications"
    folder.mkdir(parents=True, exist_ok=True)
    binary = desktop_quote(app / "venv/bin/twintext")
    icon = str(app / "plugin/assets/icon.svg").replace("\\", "\\\\")
    entry = (
        "[Desktop Entry]\nType=Application\nName=TwinText Desktop\n"
        "Comment=Floating translation reader for Codex\n"
        f"Exec={binary} desktop\nIcon={icon}\n"
        "Terminal=false\nCategories=Utility;\nStartupWMClass=TwinText Desktop\n"
    )
    (folder / "twintext.desktop").write_text(entry, encoding="utf-8")

    launcher = app / "Open Codex with TwinText.sh"
    launcher.write_text(
        "#!/bin/sh\n"
        "unset TWINTEXT_HOME\n"
        f"export TWINTEXT_CONFIG_DIR={shlex.quote(str(settings))}\n"
        f"export TWINTEXT_DATA_DIR={shlex.quote(str(data))}\n"
        f"{shlex.quote(str(app / 'venv/bin/python'))} -m twintext.cli codex-launch --wait\n"
        "task_status=$?\n"
        'if [ "$task_status" -ne 0 ] && [ "$task_status" -ne 130 ]; then\n'
        "  printf '\\nStartup failed. See the launcher.log path above. Press Enter to close.\\n'\n"
        "  read -r task_reply || :\n"
        "fi\n"
        'exit "$task_status"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o700)
    (folder / "twintext-codex.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Codex with TwinText\n"
        "Comment=Open Codex with Translate / Original buttons beside replies\n"
        f"Exec={desktop_quote(launcher)}\nIcon={icon}\n"
        "Terminal=true\nCategories=Development;\n",
        encoding="utf-8",
    )
    print(f"TwinText reader and Codex launchers installed in {folder}.")


if __name__ == "__main__":
    register(Path(sys.argv[1]))
