"""Install the shared runtime and platform-specific Codex adapter for one user."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def app_root():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "TwinText"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "twintext"


def prepare_plugin(plugin, python, windows=False):
    plugin.mkdir(parents=True, exist_ok=True)
    for name in ("plugin.json", "mcp.json"):
        (plugin / name).unlink(missing_ok=True)
    shutil.copytree(ROOT / "plugins/twintext", plugin, dirs_exist_ok=True)
    if windows:
        path = plugin / ".mcp.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["mcpServers"]["twintext"]["command"] = str(python)
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        path = plugin / "hooks/hooks.json"
        hooks = json.loads(path.read_text(encoding="utf-8"))
        # Use PowerShell explicitly so quoted paths work with either Codex shell.
        # The interpreter is private and never depends on Windows PATH aliases.
        for events in hooks["hooks"].values():
            for event in events:
                for hook in event["hooks"]:
                    script = "capture" if "capture.py" in hook["command"] else "context"
                    executable = str(python).replace("'", "''")
                    hook["commandWindows"] = (
                        "powershell.exe -NoProfile -NonInteractive -Command "
                        f"\"& '{executable}' (Join-Path $env:PLUGIN_ROOT 'hooks/{script}.py')\""
                    )
        path.write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")


def windows_launchers(app):
    scripts = app / "venv/Scripts"
    python = scripts / "python.exe"
    pythonw = scripts / "pythonw.exe"
    (app / "TwinText.cmd").write_text(
        f'@echo off\r\n"{python}" -m twintext.cli %*\r\n', encoding="utf-8"
    )
    (app / "Open TwinText.cmd").write_text(
        f'@echo off\r\nstart "" "{pythonw}" -m twintext.cli desktop\r\n', encoding="utf-8"
    )
    # Per-user Start menu shortcut; no PATH, registry, or machine configuration edits.
    start = Path(os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming")))
    start /= "Microsoft/Windows/Start Menu/Programs"
    start.mkdir(parents=True, exist_ok=True)
    quote = lambda value: "'" + str(value).replace("'", "''") + "'"  # noqa: E731
    command = (
        "$taskShell = New-Object -ComObject WScript.Shell; "
        f"$taskLink = $taskShell.CreateShortcut({quote(start / 'TwinText Desktop.lnk')}); "
        f"$taskLink.TargetPath = {quote(pythonw)}; "
        "$taskLink.Arguments = '-m twintext.cli desktop'; "
        f"$taskLink.WorkingDirectory = {quote(app)}; $taskLink.Save()"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", choices=("chat", "desktop"))
    parser.add_argument("--download-models", action="store_true")
    parser.add_argument("--skip-models", action="store_true", help="Keep existing language models")
    parser.add_argument("--without-engine", action="store_true", help="Install UI/tools only")
    args = parser.parse_args()
    if sys.platform != "win32" and not sys.platform.startswith("linux"):
        parser.error("Only Windows and Linux are released.")
    if not (3, 10) <= sys.version_info[:2] < (3, 14):
        parser.error("Use Python 3.10–3.13 (3.12 recommended), with venv and pip.")
    if args.download_models and args.skip_models:
        parser.error("Choose --download-models or --skip-models.")
    app = app_root()
    app.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        app.chmod(0o700)
    source = app / "source"
    source.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "src", source / "src", dirs_exist_ok=True)
    for name in ("pyproject.toml", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, source / name)
    environment = app / "venv"
    windows = sys.platform == "win32"
    python = environment / ("Scripts/python.exe" if windows else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    run = lambda *command: subprocess.run([str(python), *command], check=True)  # noqa: E731
    if not args.without_engine:
        run(
            "-m",
            "pip",
            "install",
            "--no-input",
            "--index-url",
            "https://download.pytorch.org/whl/cpu",
            "torch",
        )
    extras = "desktop" if args.without_engine else "engine,desktop"
    run("-m", "pip", "install", "--no-input", f"{source}[{extras}]")
    prepare_plugin(app / "plugin", python, windows)
    run(str(ROOT / "scripts/register-plugin.py"), str(app / "plugin"))
    if windows:
        windows_launchers(app)
    else:
        binary = Path.home() / ".local/bin/twintext"
        binary.parent.mkdir(parents=True, exist_ok=True)
        if binary.is_symlink() or not binary.exists():
            binary.unlink(missing_ok=True)
            binary.symlink_to(environment / "bin/twintext")
        else:
            print(f"Preserving existing {binary}; use {environment / 'bin/twintext'}.")
        run(str(ROOT / "scripts/register-desktop.py"), str(app))
    workflow = args.workflow
    release = ROOT / "release.json"
    if workflow is None and release.exists():
        # Packaged style is the first-install default, never an upgrade override.
        from subprocess import PIPE

        settings = subprocess.run(
            [
                str(python),
                "-c",
                "from twintext.config import config_dir; "
                "print((config_dir() / 'settings.json').exists())",
            ],
            stdout=PIPE,
            text=True,
            check=True,
        )
        if settings.stdout.strip() == "False":
            workflow = json.loads(release.read_text())["workflow"]
    if workflow is not None:
        run("-m", "twintext.cli", "settings", "--workflow", workflow)
    if args.download_models:
        print("Downloading third-party Argos packages. See THIRD_PARTY_NOTICES.md for licensing.")
        run("-m", "twintext.cli", "models", "install", "--starter")
    print(
        f"TwinText installed in {app}. "
        "Restart Codex, install/update TwinText, and review its hooks."
    )
    print("Choose Chat or Floating window in settings. Start a new chat after switching.")
    if not args.download_models:
        print(
            "Existing models are preserved. Download language models from TwinText's web settings."
        )


if __name__ == "__main__":
    main()
