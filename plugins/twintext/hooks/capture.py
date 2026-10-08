"""Forward Stop payload on stdin; never add translation or instructions to context."""

import subprocess
import sys
from pathlib import Path

try:
    raw = sys.stdin.buffer.read(1_100_001)
    if len(raw) <= 1_100_000:
        runner = Path(__file__).resolve().parents[1] / "scripts/launch.py"
        subprocess.run(
            [sys.executable, str(runner), "capture"],
            input=raw,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
except (OSError, subprocess.TimeoutExpired):
    pass
print("{}")
