#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  printf 'TwinText currently supports Linux.\n' >&2
  exit 1
fi
task_repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_app="${XDG_DATA_HOME:-$HOME/.local/share}/twintext"
task_python="${TWINTEXT_PYTHON:-}"
task_models=true
for task_argument in "$@"; do
  case "$task_argument" in
    --skip-models) task_models=false ;;
    *) printf 'Unknown option: %s\n' "$task_argument" >&2; exit 2 ;;
  esac
done
if [[ -z "$task_python" ]]; then
  for task_candidate in python3 python3.13 python3.12 python3.11 python3.10; do
    if command -v "$task_candidate" >/dev/null 2>&1 && "$task_candidate" -c 'import sys; sys.exit(not ((3, 10) <= sys.version_info[:2] < (3, 14)))' 2>/dev/null; then
      task_python="$(command -v "$task_candidate")"
      break
    fi
  done
fi
if [[ -z "$task_python" ]] || ! "$task_python" -c 'import sys; sys.exit(not ((3, 10) <= sys.version_info[:2] < (3, 14)))'; then
  printf 'Install Python 3.10–3.13 with venv, or set TWINTEXT_PYTHON to a supported interpreter.\n' >&2
  exit 1
fi
mkdir -p "$task_app" "$task_app/source" "$HOME/.local/bin"
chmod 700 "$task_app"
cp -R "$task_repo/src" "$task_app/source/"
cp "$task_repo/pyproject.toml" "$task_repo/README.md" "$task_repo/LICENSE" "$task_app/source/"
if [[ ! -x "$task_app/venv/bin/python" ]]; then
  "$task_python" -m venv "$task_app/venv"
fi
# Argos depends on Stanza/PyTorch. Install CPU wheels first to avoid CUDA packages.
"$task_app/venv/bin/python" -m pip install --no-input --index-url https://download.pytorch.org/whl/cpu torch
"$task_app/venv/bin/python" -m pip install --no-input "$task_app/source[engine,desktop]"
task_binary="$HOME/.local/bin/twintext"
if [[ -e "$task_binary" && ! -L "$task_binary" ]]; then
  printf 'Leaving existing %s untouched. Use %s instead.\n' "$task_binary" "$task_app/venv/bin/twintext"
else
  ln -sfn "$task_app/venv/bin/twintext" "$task_binary"
fi
# Hook scripts resolve the same private runtime after Codex caches the plugin.
mkdir -p "$task_app/plugin"
cp -R "$task_repo/plugins/twintext/." "$task_app/plugin/"
"$task_app/venv/bin/python" "$task_repo/scripts/register-plugin.py" "$task_app/plugin"
"$task_app/venv/bin/python" "$task_repo/scripts/register-desktop.py" "$task_app"
if $task_models; then
  "$task_app/venv/bin/twintext" models install --starter
fi
printf '\nTwinText Desktop installed. Open the floating reader with:\n  %s desktop\n' "$task_app/venv/bin/twintext"
printf 'Restart Codex, select the TwinText Linux marketplace, and install/enable TwinText.\n'
printf 'Review and trust its Stop hook to receive completed replies outside the conversation.\n'
