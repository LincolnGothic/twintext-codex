"""Azure secrets stay outside settings, MCP, cache identities and logs."""

import json
import os
import re
import stat
import sys

from twintext.config import TwinTextError, config_dir


def _windows_credentials(value=None):
    """Use the per-user Windows Credential Manager, without extra dependencies."""
    import ctypes
    import hashlib
    from ctypes import wintypes

    class Credential(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    pointer = ctypes.POINTER(Credential)
    api.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(pointer),
    ]
    api.CredReadW.restype = wintypes.BOOL
    api.CredWriteW.argtypes = [pointer, wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    target = "TwinText/Azure/" + hashlib.sha256(str(config_dir().resolve()).encode()).hexdigest()
    if value is not None:
        blob = json.dumps(value).encode("utf-8")
        data = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        item = Credential(
            Type=1,
            TargetName=target,
            CredentialBlobSize=len(blob),
            CredentialBlob=data,
            Persist=2,
            UserName="TwinText",
        )
        if not api.CredWriteW(ctypes.byref(item), 0):
            raise TwinTextError("Cannot save Azure credentials in Windows Credential Manager.")
        return None
    item = pointer()
    if not api.CredReadW(target, 1, 0, ctypes.byref(item)):
        if ctypes.get_last_error() == 1168:  # ERROR_NOT_FOUND
            return {}
        raise TwinTextError("Cannot read Azure credentials from Windows Credential Manager.")
    try:
        return json.loads(
            ctypes.string_at(item.contents.CredentialBlob, item.contents.CredentialBlobSize)
        )
    finally:
        api.CredFree(item)


def _private_folder(create=False):
    folder = config_dir() / "private"
    if create:
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = folder.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise TwinTextError("Azure credential directory needs owner-only permissions (chmod 700).")
    return folder


def load_credentials():
    try:
        if sys.platform == "win32":
            value = _windows_credentials()
        else:
            folder = _private_folder()
            path = folder / "azure-credentials.json"
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "r", encoding="utf-8") as stream:
                info = os.fstat(stream.fileno())
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.getuid()
                    or info.st_mode & 0o077
                ):
                    raise TwinTextError(
                        "Azure credentials need owner-only permissions (chmod 600)."
                    )
                value = json.loads(stream.read(8192))
        if not isinstance(value, dict) or not isinstance(value.get("key", ""), str):
            raise ValueError
        return value
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, TypeError):
        raise TwinTextError(
            "Cannot read private Azure credentials. Run twintext azure-configure."
        ) from None


def save_credentials(key, region=""):
    if not isinstance(key, str) or not key.strip() or len(key) > 2048 or "\n" in key or "\r" in key:
        raise TwinTextError("Enter a valid Azure resource key.")
    if not isinstance(region, str) or not re.fullmatch(r"[a-z0-9-]*", region):
        raise TwinTextError("Enter the Azure resource region, for example westus.")
    value = {"key": key.strip(), "region": region}
    try:
        if sys.platform == "win32":
            _windows_credentials(value)
            return
        folder = _private_folder(create=True)
        path = folder / "azure-credentials.json"
        # Refuse links/insecure existing files before opening for replacement.
        if path.exists() or path.is_symlink():
            load_credentials()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise TwinTextError("Azure credentials need owner-only permissions (chmod 600).")
            stream.truncate()
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise TwinTextError(
            "Cannot save private Azure credentials. Check directory permissions."
        ) from None
