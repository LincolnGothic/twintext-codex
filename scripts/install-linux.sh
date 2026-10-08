#!/usr/bin/env bash
set -euo pipefail
if [[ "$(uname -s)" != "Linux" ]]; then
  printf 'Use install-windows.ps1 on Windows. No macOS release is provided.\n' >&2
  exit 1
fi
task_repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_python="${TWINTEXT_PYTHON:-}"
if [[ -z "$task_python" ]]; then
  for task_candidate in python3.12 python3.13 python3.11 python3.10 python3; do
    if command -v "$task_candidate" >/dev/null 2>&1 && "$task_candidate" -c 'import sys; sys.exit(not ((3,10) <= sys.version_info[:2] < (3,14)))' 2>/dev/null; then
      task_python="$(command -v "$task_candidate")"
      break
    fi
  done
fi
if [[ -z "$task_python" ]]; then
  printf 'Install Python 3.10–3.13 with pip and venv, or set TWINTEXT_PYTHON.\n' >&2
  exit 1
fi
exec "$task_python" "$task_repo/scripts/install.py" "$@"
