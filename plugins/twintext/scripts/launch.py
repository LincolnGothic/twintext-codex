"""Resolve the installed private Python environment across plugin cache copies."""

import os
import sys
from pathlib import Path

override = os.environ.get("TWINTEXT_PYTHON")
if sys.platform == "win32":
    data_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    installed = data_root / "TwinText/venv/Scripts/python.exe"
else:
    data_root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    installed = data_root / "twintext/venv/bin/python"
python = Path(override).expanduser() if override else installed
if not python.is_file():
    print(
        "TwinText is not installed. Run the Windows or Linux installer from its repository.",
        file=sys.stderr,
    )
    sys.exit(1)
os.execv(str(python), [str(python), "-m", "twintext.cli", *sys.argv[1:]])
