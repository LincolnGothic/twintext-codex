"""Supply current preferences for each new reply; never read chat history."""

import json
import subprocess
import sys
from pathlib import Path

try:
    request = json.load(sys.stdin)
    event = request.get("hook_event_name", "UserPromptSubmit")
    runner = Path(__file__).resolve().parents[1] / "scripts/launch.py"
    result = subprocess.run(
        [sys.executable, str(runner), "context"],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    if result.returncode:
        print(json.dumps({"systemMessage": "TwinText needs setup. Run its Linux install script."}))
    elif result.stdout.strip():
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": result.stdout.strip(),
                    }
                }
            )
        )
    else:
        print("{}")
except (ValueError, OSError, subprocess.TimeoutExpired):
    print(json.dumps({"systemMessage": "TwinText could not load preferences. Check its setup."}))
