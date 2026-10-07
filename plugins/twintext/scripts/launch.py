"""Resolve the installed private Python environment across plugin cache copies."""

import os
import sys
from pathlib import Path

override = os.environ.get("TWINTEXT_PYTHON")
data_root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
python = Path(override).expanduser() if override else data_root / "twintext/venv/bin/python"
if not python.is_file():
    print(
        "TwinText is not installed. Run scripts/install-linux.sh from its repository.",
        file=sys.stderr,
    )
    sys.exit(1)
os.execv(str(python), [str(python), "-m", "twintext.cli", *sys.argv[1:]])
