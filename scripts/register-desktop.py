"""Install the user's app-menu launcher without touching system directories."""

import os
import sys
from pathlib import Path

app = Path(sys.argv[1]).resolve()
if any(char in str(app) for char in "\n\r"):
    sys.exit("The app path must not contain newlines.")
folder = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "applications"
folder.mkdir(parents=True, exist_ok=True)
binary = str(app / "venv/bin/twintext")
for character in ("\\", '"', "`", "$"):
    binary = binary.replace(character, "\\" + character)
binary = binary.replace("%", "%%")
entry = (
    "[Desktop Entry]\nType=Application\nName=TwinText Desktop\n"
    "Comment=Offline floating translation for Codex\n"
    f'Exec="{binary}" desktop\nIcon={app / "plugin/assets/icon.svg"}\n'
    "Terminal=false\nCategories=Utility;\nStartupWMClass=TwinText Desktop\n"
)
(folder / "twintext.desktop").write_text(entry, encoding="utf-8")
print(f"Desktop launcher installed in {folder / 'twintext.desktop'}.")
