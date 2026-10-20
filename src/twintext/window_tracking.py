"""Read Codex window identity, bounds and focus. Never read window contents.

Windows uses Win32; Linux uses EWMH through X11/XWayland. Native Wayland
does not expose other applications' positions, so it keeps the manual reader.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import PureWindowsPath


@dataclass(frozen=True)
class TargetWindow:
    id: int
    x: int
    y: int
    width: int
    height: int
    visible: bool = True
    # Windows physical monitor origin, used for per-monitor DPI conversion.
    monitor: tuple = ()
    screen_name: str = ""


@dataclass(frozen=True)
class Snapshot:
    target: TargetWindow | None = None
    foreground: int = 0


def codex_wm_class(classes):
    names = [name.casefold() for name in classes]
    if any(name in ("codex", "codex-linux", "com.openai.codex") for name in names):
        return True
    # Some Linux Codex builds retain Electron's Chatgpt class, with Codex's
    # user-data directory in the instance. Do not match an ordinary ChatGPT window.
    return ("chatgpt" in names and any(
        name.startswith("chatgpt (") and name.endswith("/codex)") for name in names))


class X11Tracker:
    def __init__(self):
        from Xlib import display

        self.display = display.Display()
        self.root = self.display.screen().root
        self.atoms = {}
        self.selected = None

    def prop(self, window, name):
        from Xlib import X

        if name not in self.atoms:
            self.atoms[name] = self.display.intern_atom(name)
        atom = self.atoms[name]
        result = window.get_full_property(atom, X.AnyPropertyType)
        return list(result.value) if result else []

    def read(self):
        from Xlib import error

        active = self.prop(self.root, "_NET_ACTIVE_WINDOW")
        foreground = int(active[0]) if active else 0
        current = self.prop(self.root, "_NET_CURRENT_DESKTOP")
        hidden = self.display.intern_atom("_NET_WM_STATE_HIDDEN")
        ids = self.prop(self.root, "_NET_CLIENT_LIST_STACKING")
        if not ids:
            ids = self.prop(self.root, "_NET_CLIENT_LIST")
        candidates = []
        for wid in reversed(ids):
            try:
                window = self.display.create_resource_object("window", int(wid))
                classes = window.get_wm_class() or ()
                if not codex_wm_class(classes):
                    continue
                geometry = window.get_geometry()
                if geometry.width < 300 or geometry.height < 200:
                    continue
                position = self.root.translate_coords(window, 0, 0)
                desktop = self.prop(window, "_NET_WM_DESKTOP")
                visible = hidden not in self.prop(window, "_NET_WM_STATE")
                if current and desktop and desktop[0] not in (current[0], 0xFFFFFFFF):
                    visible = False
                candidates.append(TargetWindow(int(wid), position.x, position.y,
                                               geometry.width, geometry.height, visible))
            except error.XError:
                # A window may close between enumeration and a property read.
                continue
        target = next((item for item in candidates if item.id == foreground), None)
        target = target or next((item for item in candidates if item.id == self.selected), None)
        target = target or next(iter(candidates), None)
        self.selected = target.id if target else None
        return Snapshot(target, foreground)

    def close(self):
        self.display.close()


class WindowsTracker:
    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w

        self.c, self.w = c, w
        self.user = c.WinDLL("user32", use_last_error=True)
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.callback = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        signatures = {
            "EnumWindows": ([self.callback, w.LPARAM], w.BOOL),
            "GetForegroundWindow": ([], w.HWND),
            "IsWindowVisible": ([w.HWND], w.BOOL),
            "IsIconic": ([w.HWND], w.BOOL),
            "GetWindowRect": ([w.HWND, c.POINTER(w.RECT)], w.BOOL),
            "GetWindowThreadProcessId": ([w.HWND, c.POINTER(w.DWORD)], w.DWORD),
            "GetClassNameW": ([w.HWND, w.LPWSTR, c.c_int], c.c_int),
            "MonitorFromWindow": ([w.HWND, w.DWORD], w.HMONITOR),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.user, name)
            function.argtypes, function.restype = args, result
        for name, args, result in (
            ("OpenProcess", [w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            ("QueryFullProcessImageNameW", [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)],
             w.BOOL),
            ("CloseHandle", [w.HANDLE], w.BOOL),
        ):
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = args, result

        class MonitorInfo(c.Structure):
            _fields_ = [("size", w.DWORD), ("bounds", w.RECT), ("work", w.RECT),
                        ("flags", w.DWORD), ("device", w.WCHAR * 32)]

        self.MonitorInfo = MonitorInfo
        self.user.GetMonitorInfoW.argtypes = [w.HMONITOR, c.POINTER(MonitorInfo)]
        self.user.GetMonitorInfoW.restype = w.BOOL
        self.selected = None

    def is_codex(self, hwnd):
        c, w = self.c, self.w
        name = c.create_unicode_buffer(256)
        self.user.GetClassNameW(hwnd, name, len(name))
        if not name.value.startswith("Chrome_WidgetWin_"):
            return False
        pid = w.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
        process = self.kernel.OpenProcess(0x1000, False, pid.value)
        if not process:
            return False
        try:
            size = w.DWORD(32768)
            path = c.create_unicode_buffer(size.value)
            return (self.kernel.QueryFullProcessImageNameW(process, 0, path, c.byref(size))
                    and PureWindowsPath(path.value).name.casefold() == "codex.exe")
        finally:
            self.kernel.CloseHandle(process)

    def read(self):
        candidates = []

        @self.callback
        def visit(hwnd, _parameter):
            if not self.user.IsWindowVisible(hwnd) or not self.is_codex(hwnd):
                return True
            rect = self.w.RECT()
            if not self.user.GetWindowRect(hwnd, self.c.byref(rect)):
                return True
            minimized = bool(self.user.IsIconic(hwnd))
            if not minimized and (rect.right - rect.left < 300 or rect.bottom - rect.top < 200):
                return True
            info = self.MonitorInfo()
            info.size = self.c.sizeof(info)
            monitor, name = (), ""
            if self.user.GetMonitorInfoW(self.user.MonitorFromWindow(hwnd, 2), self.c.byref(info)):
                monitor, name = (info.bounds.left, info.bounds.top), info.device
            candidates.append(TargetWindow(int(hwnd), rect.left, rect.top,
                                           rect.right - rect.left, rect.bottom - rect.top,
                                           not minimized, monitor, name))
            return True

        self.user.EnumWindows(visit, 0)
        foreground = int(self.user.GetForegroundWindow() or 0)
        target = next((item for item in candidates if item.id == foreground), None)
        target = target or next((item for item in candidates if item.id == self.selected), None)
        target = target or next(iter(candidates), None)
        self.selected = target.id if target else None
        return Snapshot(target, foreground)

    def close(self):
        pass


def create_tracker():
    if sys.platform == "win32":
        return WindowsTracker()
    if sys.platform.startswith("linux") and os.environ.get("DISPLAY"):
        return X11Tracker()
    raise OSError("Window following requires Windows or X11/XWayland.")
