"""Explicit Windows launcher for the optional message adapter; never closes Codex."""

import json
import socket
import subprocess
import sys
from pathlib import Path

from twintext.bridge import launch_desktop
from twintext.config import TwinTextError, load_settings
from twintext.message_adapter import PORT


def windows_app():
    # Read only. Do not stop processes, change Appx registrations or edit app files.
    script = """
$ErrorActionPreference = 'Stop'
$taskPackage = Get-AppxPackage -Name OpenAI.Codex |
    Sort-Object Version -Descending | Select-Object -First 1
if (-not $taskPackage) { throw 'Codex is not installed for this user.' }
$taskFolder = Join-Path $taskPackage.InstallLocation 'app'
$taskExecutable = Join-Path $taskFolder 'Codex.exe'
$taskRunning = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -in @('Codex.exe', 'ChatGPT.exe') -and $_.ExecutablePath -and
    $_.ExecutablePath.StartsWith($taskFolder + '\\', [StringComparison]::OrdinalIgnoreCase)
}).Count -gt 0
@{executable=$taskExecutable; running=$taskRunning} | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, check=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        value = json.loads(result.stdout)
        executable = Path(value["executable"])
        if not executable.is_file() or executable.name.lower() != "codex.exe":
            raise ValueError("Codex executable not found")
        return executable, bool(value["running"])
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        raise TwinTextError("Cannot locate the installed Windows Codex app.") from exc


def check_port():
    try:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", PORT))
    except OSError as exc:
        raise TwinTextError(
            f"Port {PORT} is already in use. Exit the previous debugging instance before retrying."
        ) from exc


def launch():
    if sys.platform != "win32":
        raise TwinTextError(
            "The experimental per-message launcher currently supports Windows only."
        )
    settings = load_settings()
    if not settings.manual_reader or not settings.enabled:
        raise TwinTextError(
            "In TwinText settings choose Floating reader beside Codex, enable translation "
            "and Per-reply Translate buttons first."
        )
    executable, running = windows_app()
    if running:
        raise TwinTextError(
            "Exit Codex (and its shared ChatGPT window, if open), then run this launcher again. "
            "TwinText will not close an active conversation."
        )
    check_port()
    subprocess.Popen(
        [str(executable), "--remote-debugging-address=127.0.0.1",
         f"--remote-debugging-port={PORT}"],
        creationflags=(getattr(subprocess, "DETACHED_PROCESS", 0)
                       | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    launch_desktop()
    return {"launched": True, "experimental": True, "port": PORT}
