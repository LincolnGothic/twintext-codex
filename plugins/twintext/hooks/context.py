"""Supply current preferences for each new reply; never read chat history."""

import json
import subprocess
import sys
import uuid
from pathlib import Path

try:
    request = json.load(sys.stdin)
    event = request.get("hook_event_name", "UserPromptSubmit")
    runner = Path(__file__).resolve().parents[1] / "scripts/launch.py"
    result = subprocess.run(
        [sys.executable, str(runner), "context", "--session-id",
         str(request.get("session_id") or "codex")[:256], "--turn-id",
         str(request.get("turn_id") or uuid.uuid4().hex)[:256]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=8,
        check=False,
    )
    if result.returncode:
        print(json.dumps({"systemMessage": "TwinText needs setup. Run its installer."}))
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
