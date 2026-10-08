"""Small, atomically updated settings shared by CLI, hooks and the local UI."""

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

from twintext.locking import file_lock

LANGUAGES = {"en": "English", "zh": "Chinese", "ja": "Japanese", "fr": "French", "es": "Spanish"}
MODES = ("bilingual", "translated", "original")
WORKFLOWS = ("desktop", "chat")


class TwinTextError(Exception):
    """An actionable problem that can be shown without a traceback."""


def data_dir() -> Path:
    override = os.environ.get("TWINTEXT_HOME")
    if not override and sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "TwinText"
    return (
        Path(override).expanduser()
        if override
        else Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "twintext"
    )


def config_dir() -> Path:
    override = os.environ.get("TWINTEXT_HOME")
    if not override and sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming"))) / "TwinText"
    return (
        Path(override).expanduser()
        if override
        else Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "twintext"
    )


def private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


@dataclass(frozen=True)
class Settings:
    source: str = "auto"
    target: str = "en"
    mode: str = "bilingual"
    enabled: bool = True
    cache: bool = True
    ui_language: str = "auto"
    host_locale: str = "auto"
    desktop_auto_start: bool = True
    always_on_top: bool = True
    workflow: str = "desktop"

    def validate(self):
        if self.workflow not in WORKFLOWS:
            raise TwinTextError("Workflow must be desktop or chat.")
        if self.source not in ("auto", *LANGUAGES):
            raise TwinTextError("Source must be auto, en, zh, ja, fr, or es.")
        if self.target not in LANGUAGES:
            raise TwinTextError("Target must be en, zh, ja, fr, or es.")
        if self.mode not in MODES:
            raise TwinTextError("Mode must be bilingual, translated, or original.")
        if self.ui_language not in ("auto", *LANGUAGES):
            raise TwinTextError("UI language must be auto, en, zh, ja, fr, or es.")
        if self.host_locale not in ("auto", *LANGUAGES):
            raise TwinTextError("Host locale must be auto, en, zh, ja, fr, or es.")
        if any(
            type(value) is not bool
            for value in (self.enabled, self.cache, self.desktop_auto_start, self.always_on_top)
        ):
            raise TwinTextError("Enabled, cache, auto-start and always-on-top must be booleans.")
        return self

    def as_dict(self):
        return asdict(self)


def load_settings() -> Settings:
    path = config_dir() / "settings.json"
    if not path.exists():
        return Settings()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("expected an object")
        known = {field.name for field in fields(Settings)}
        return Settings(**{key: item for key, item in value.items() if key in known}).validate()
    except (OSError, ValueError, TypeError) as exc:
        raise TwinTextError(f"Cannot read {path}: {exc}") from exc


def update_settings(**changes) -> Settings:
    folder = private_dir(config_dir())
    with file_lock(folder / "settings.lock"):
        settings = replace(load_settings(), **changes).validate()
        path = folder / "settings.json"
        previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        fd, temporary = tempfile.mkstemp(prefix="settings-", suffix=".tmp", dir=folder)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({**previous, **settings.as_dict()}, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, folder / "settings.json")
        finally:
            Path(temporary).unlink(missing_ok=True)
        return settings
