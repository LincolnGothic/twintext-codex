"""Small, atomically updated settings shared by CLI, hooks and the local UI."""

import fcntl
import json
import os
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path

LANGUAGES = {"en": "English", "zh": "Chinese", "ja": "Japanese", "fr": "French", "es": "Spanish"}
MODES = ("bilingual", "translated", "original")


class TwinTextError(Exception):
    """An actionable problem that can be shown without a traceback."""


def data_dir() -> Path:
    override = os.environ.get("TWINTEXT_HOME")
    return (
        Path(override).expanduser()
        if override
        else Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "twintext"
    )


def config_dir() -> Path:
    override = os.environ.get("TWINTEXT_HOME")
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

    def validate(self):
        if self.source not in ("auto", *LANGUAGES):
            raise TwinTextError("Source must be auto, en, zh, ja, fr, or es.")
        if self.target not in LANGUAGES:
            raise TwinTextError("Target must be en, zh, ja, fr, or es.")
        if self.mode not in MODES:
            raise TwinTextError("Mode must be bilingual, translated, or original.")
        if self.ui_language not in ("auto", *LANGUAGES):
            raise TwinTextError("UI language must be auto, en, zh, ja, fr, or es.")
        if type(self.enabled) is not bool or type(self.cache) is not bool:
            raise TwinTextError("Enabled and cache must be true or false.")
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
        return Settings(**value).validate()
    except (OSError, ValueError, TypeError) as exc:
        raise TwinTextError(f"Cannot read {path}: {exc}") from exc


def update_settings(**changes) -> Settings:
    folder = private_dir(config_dir())
    with (folder / "settings.lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        settings = replace(load_settings(), **changes).validate()
        fd, temporary = tempfile.mkstemp(prefix="settings-", suffix=".tmp", dir=folder)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(settings.as_dict(), stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, folder / "settings.json")
        finally:
            Path(temporary).unlink(missing_ok=True)
        return settings
