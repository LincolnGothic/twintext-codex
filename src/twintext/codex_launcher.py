"""Explicit Windows/Linux launcher for message buttons; never closes Codex."""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from twintext import __version__
from twintext.bridge import launch_desktop
from twintext.config import TwinTextError, config_dir, data_dir, load_settings, private_dir
from twintext.message_adapter import PORT, discover


def linux_running(executable, proc_root=Path("/proc")):
    """Match this user's GUI executable, never the unrelated Codex CLI by name."""
    try:
        processes = list(proc_root.iterdir())
    except OSError as exc:
        raise TwinTextError("Cannot check running Codex apps through /proc.") from exc
    for process in processes:
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            # An app upgrade can unlink an executable that is still running.
            target = str((process / "exe").readlink()).removesuffix(" (deleted)")
            if Path(target) == executable:
                return True
        except OSError:
            continue  # Other users, protected helpers, and processes that just exited.
    return False


def linux_app():
    override = os.environ.get("TWINTEXT_CODEX_EXECUTABLE")
    if override:
        candidates = [Path(override).expanduser()]
    else:
        candidates = [Path("/usr/lib/chatgpt/ChatGPT"), Path("/usr/lib/codex/Codex")]
        for name in ("chatgpt", "codex"):
            located = shutil.which(name)
            if located:
                candidate = Path(located).resolve()
                # The native package's shell launcher execs its sibling ChatGPT.
                candidates.extend([candidate, *(candidate.parent / binary
                                                for binary in ("ChatGPT", "Codex", "codex"))])
    for candidate in candidates:
        executable = candidate.resolve()
        if (executable.name.lower() in ("chatgpt", "codex")
                and executable.is_file() and os.access(executable, os.X_OK)
                and (executable.parent / "resources/app.asar").is_file()):
            return executable, linux_running(executable)
    raise TwinTextError(
        "Cannot locate the installed Linux Codex desktop app. "
        "Set TWINTEXT_CODEX_EXECUTABLE to its ChatGPT/Codex executable "
        "beside resources/app.asar, not the Codex command-line tool."
    )


def windows_app():
    # Read only. Do not stop processes, change Appx registrations or edit app files.
    script = """
$ErrorActionPreference = 'Stop'
$taskPackage = Get-AppxPackage -Name OpenAI.Codex |
    Sort-Object Version -Descending | Select-Object -First 1
if (-not $taskPackage) { throw 'Codex is not installed for this user.' }
$taskFolder = Join-Path $taskPackage.InstallLocation 'app'
$taskExecutable = Join-Path $taskFolder 'ChatGPT.exe'
if (-not (Test-Path -LiteralPath $taskExecutable -PathType Leaf)) {
    $taskExecutable = Join-Path $taskFolder 'Codex.exe'
}
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
        if (not executable.is_file()
                or executable.name.lower() not in ("codex.exe", "chatgpt.exe")):
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


def wait_for_debugging(process):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise TwinTextError(f"Codex exited during startup (exit code {code}).")
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise TwinTextError(
        f"Codex did not open its debugging port on 127.0.0.1:{PORT} within 20 seconds. "
        "It may reject debugging or still have another instance running. "
        "Exit Codex/ChatGPT normally before retrying; TwinText has not closed it."
    )


def launch(wait=False):
    if sys.platform != "win32" and not sys.platform.startswith("linux"):
        raise TwinTextError(
            "The experimental per-message launcher supports Windows and Linux."
        )
    path = private_dir(data_dir() / "desktop") / "launcher.log"
    with path.open("a", encoding="utf-8") as log:
        path.chmod(0o600)
        log.write(f"\n{datetime.now(timezone.utc).isoformat()} TwinText {__version__}\n")

        def report(message):
            print(message, file=sys.stderr, flush=True)
            print(message, file=log, flush=True)

        report(f"Startup log: {path.resolve()}")
        report(f"Python: {sys.executable}")
        try:
            return _launch(wait, report)
        except KeyboardInterrupt:
            report("Launcher cancelled. No running app was closed.")
            raise
        except (TwinTextError, OSError, ValueError, RuntimeError) as exc:
            report(f"Startup failed: {exc}")
            raise


def _launch(wait, report):
    settings = load_settings()
    report(f"Settings file: {(config_dir() / 'settings.json').resolve()}")
    report(f"enabled={settings.enabled}, workflow={settings.workflow}, "
           f"chat_presentation={settings.chat_presentation}, "
           f"message_buttons={settings.message_buttons}")
    if not settings.enabled:
        raise TwinTextError(
            "Enable Translate buttons in TwinText settings before starting Codex."
        )
    inspect_app = windows_app if sys.platform == "win32" else linux_app
    executable, running = inspect_app()
    if running:
        try:
            debugging = discover()
        except (OSError, ValueError, TwinTextError):
            debugging = None
        if debugging:
            report(f"Reusing the running Codex connection on 127.0.0.1:{PORT}.")
            launch_desktop()
            report("TwinText reader launch requested. Codex was not restarted.")
            return {"launched": True, "experimental": True, "port": PORT, "reused": True}
    if running and not wait:
        raise TwinTextError(
            "Exit Codex and its shared ChatGPT app, including any background/tray instance, "
            "then run this launcher again. Pressing a key only closes this error window. "
            "TwinText will not close an active conversation."
        )
    if running:
        report(
            "Waiting for Codex/ChatGPT to exit normally. Leave this terminal open, "
            "then choose Quit/Exit in Codex and the shared ChatGPT app, including its tray icon. "
            "Startup continues automatically after the app exits. Press Ctrl+C to cancel."
        )
        while running:
            time.sleep(2)
            executable, running = inspect_app()
    check_port()
    report(f"Starting: {executable}")
    if sys.platform == "win32":
        options = {"creationflags": (getattr(subprocess, "DETACHED_PROCESS", 0)
                                     | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))}
    else:
        environment = os.environ.copy()
        environment.pop("ELECTRON_RUN_AS_NODE", None)
        options = {"start_new_session": True, "env": environment}
    process = subprocess.Popen(
        [str(executable), "--remote-debugging-address=127.0.0.1",
         f"--remote-debugging-port={PORT}"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        **options,
    )
    wait_for_debugging(process)
    report(f"Debugging port ready: 127.0.0.1:{PORT}")
    launch_desktop()
    report("TwinText reader launch requested.")
    return {"launched": True, "experimental": True, "port": PORT}
