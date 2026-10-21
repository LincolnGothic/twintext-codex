"""Small, atomically updated settings shared by CLI, hooks and the local UI."""

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

from twintext.locking import file_lock

LANGUAGES = {"en": "English", "zh": "Chinese", "ja": "Japanese", "fr": "French", "es": "Spanish"}
TRANSLATION_LANGUAGES = {**LANGUAGES, "zh-TW": "Chinese (Traditional)"}
MODES = ("bilingual", "translated", "original")
WORKFLOWS = ("desktop", "chat")
RESPONSE_SCOPES = ("final", "all")
CHAT_PRESENTATIONS = ("inline", "floating")
CACHE_LIFETIMES = ("disk", "session")
PROVIDERS = ("offline", "azure", "google-free")


class TwinTextError(Exception):
    """An actionable problem that can be shown without a traceback."""


def data_dir() -> Path:
    override = os.environ.get("TWINTEXT_HOME") or os.environ.get("TWINTEXT_DATA_DIR")
    if not override and sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "TwinText"
    return (
        Path(override).expanduser()
        if override
        else Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "twintext"
    )


def config_dir() -> Path:
    override = os.environ.get("TWINTEXT_HOME") or os.environ.get("TWINTEXT_CONFIG_DIR")
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
    provider: str = "offline"
    source: str = "auto"
    target: str = "en"
    mode: str = "bilingual"
    enabled: bool = True
    cache: bool = True
    cache_lifetime: str = "disk"
    ui_language: str = "auto"
    host_locale: str = "auto"
    desktop_auto_start: bool = True
    always_on_top: bool = True
    follow_codex: bool = False
    workflow: str = "desktop"
    response_scope: str = "final"
    translate_questions: bool = True
    chat_presentation: str = "inline"
    message_buttons: bool = False

    @property
    def floating_chat(self):
        return self.workflow == "chat" and self.chat_presentation == "floating"

    @property
    def manual_reader(self):
        return self.floating_chat and self.message_buttons

    def validate(self):
        if self.provider not in PROVIDERS:
            raise TwinTextError("Provider must be offline, azure or google-free.")
        if self.cache_lifetime not in CACHE_LIFETIMES:
            raise TwinTextError("Cache lifetime must be disk or session.")
        if self.workflow not in WORKFLOWS:
            raise TwinTextError("Workflow must be desktop or chat.")
        if self.response_scope not in RESPONSE_SCOPES:
            raise TwinTextError("Response scope must be final or all.")
        if self.chat_presentation not in CHAT_PRESENTATIONS:
            raise TwinTextError("Chat presentation must be inline or floating.")
        if self.source not in ("auto", *TRANSLATION_LANGUAGES):
            raise TwinTextError("Choose a supported source language.")
        if self.target not in TRANSLATION_LANGUAGES:
            raise TwinTextError("Choose a supported target language.")
        if self.provider != "google-free" and "zh-TW" in (self.source, self.target):
            raise TwinTextError(
                "Traditional Chinese requires Google Free; choose Chinese (zh) first."
            )
        if self.mode not in MODES:
            raise TwinTextError("Mode must be bilingual, translated, or original.")
        if self.ui_language not in ("auto", *LANGUAGES):
            raise TwinTextError("UI language must be auto, en, zh, ja, fr, or es.")
        if self.host_locale not in ("auto", *LANGUAGES):
            raise TwinTextError("Host locale must be auto, en, zh, ja, fr, or es.")
        if any(
            type(value) is not bool
            for value in (self.enabled, self.cache, self.desktop_auto_start, self.always_on_top,
                          self.translate_questions, self.follow_codex, self.message_buttons)
        ):
            raise TwinTextError(
                "Enabled, cache, auto-start, always-on-top, follow and questions must be booleans."
            )
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
