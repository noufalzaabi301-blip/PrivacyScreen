"""Small, dependency-free wrappers around the Windows API."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Thread
from typing import Callable

from .models import Monitor

user32 = ctypes.windll.user32

MONITORINFOF_PRIMARY = 1
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_NOZORDER = 0x0004


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.UINT),
        ("flags", wintypes.UINT),
        ("showCmd", wintypes.UINT),
        ("ptMinPosition", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT),
        ("rcNormalPosition", wintypes.RECT),
    ]


def enable_per_monitor_dpi_awareness() -> None:
    """Keep Tk coordinates aligned with physical pixels on mixed-DPI displays."""
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def enumerate_monitors() -> list[Monitor]:
    """Return all active Windows monitors, including negative coordinates."""
    monitors: list[Monitor] = []
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
    )

    def callback(handle, _dc, _rect, _data):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(handle, ctypes.byref(info)):
            rect = info.rcMonitor
            monitors.append(
                Monitor(
                    device_name=info.szDevice,
                    left=rect.left,
                    top=rect.top,
                    right=rect.right,
                    bottom=rect.bottom,
                    primary=bool(info.dwFlags & MONITORINFOF_PRIMARY),
                )
            )
        return True

    callback_ref = callback_type(callback)
    user32.EnumDisplayMonitors(None, None, callback_ref, 0)
    return monitors


def move_windows_to_monitor(source: Monitor, target: Monitor) -> int:
    """Move normal application windows from one monitor to another.

    Minimized windows are moved by changing their restore rectangle. Windows
    owned by elevated processes may reject the request because of Windows UIPI.
    """
    moved = 0
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _data):
        nonlocal moved
        if not user32.IsWindowVisible(hwnd) or user32.GetWindowTextLengthW(hwnd) == 0:
            return True

        placement = WINDOWPLACEMENT()
        placement.length = ctypes.sizeof(placement)
        if not user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
            return True

        rect = placement.rcNormalPosition if user32.IsIconic(hwnd) else wintypes.RECT()
        if not user32.IsIconic(hwnd) and not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True

        center_x = (rect.left + rect.right) // 2
        center_y = (rect.top + rect.bottom) // 2
        if not (source.left <= center_x < source.right and source.top <= center_y < source.bottom):
            return True

        width = min(max(1, rect.right - rect.left), target.width)
        height = min(max(1, rect.bottom - rect.top), target.height)
        relative_x = rect.left - source.left
        relative_y = rect.top - source.top
        new_x = target.left + min(max(0, relative_x), max(0, target.width - width))
        new_y = target.top + min(max(0, relative_y), max(0, target.height - height))

        if user32.IsIconic(hwnd):
            placement.rcNormalPosition = wintypes.RECT(new_x, new_y, new_x + width, new_y + height)
            success = user32.SetWindowPlacement(hwnd, ctypes.byref(placement))
        else:
            success = user32.SetWindowPos(
                hwnd, None, new_x, new_y, width, height, SWP_NOZORDER | SWP_NOACTIVATE
            )
        if success:
            moved += 1
        return True

    callback_ref = callback_type(callback)
    user32.EnumWindows(callback_ref, 0)
    return moved


@dataclass(frozen=True)
class ParsedHotkey:
    modifiers: int
    virtual_key: int
    canonical: str


_MODIFIERS = {"CTRL": MOD_CONTROL, "ALT": MOD_ALT, "SHIFT": MOD_SHIFT, "WIN": MOD_WIN}
_SPECIAL_KEYS = {
    "SPACE": 0x20,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "HOME": 0x24,
    "END": 0x23,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
}


def parse_hotkey(text: str) -> ParsedHotkey:
    """Parse forms such as F8, Ctrl+Shift+P, or Win+Alt+1."""
    parts = [part.strip().upper() for part in text.split("+") if part.strip()]
    if not parts:
        raise ValueError("Enter a hotkey, for example F8 or Ctrl+Shift+P.")

    modifiers = 0
    modifier_names: list[str] = []
    key_name: str | None = None
    for part in parts:
        if part in _MODIFIERS:
            if part in modifier_names:
                raise ValueError(f"Duplicate modifier: {part.title()}.")
            modifiers |= _MODIFIERS[part]
            modifier_names.append(part)
        elif key_name is None:
            key_name = part
        else:
            raise ValueError("A hotkey must contain exactly one main key.")

    if key_name is None:
        raise ValueError("Add a main key, for example P or F8.")

    if len(key_name) == 1 and key_name.isalnum():
        virtual_key = ord(key_name)
    elif key_name.startswith("F") and key_name[1:].isdigit() and 1 <= int(key_name[1:]) <= 24:
        virtual_key = 0x70 + int(key_name[1:]) - 1
    elif key_name in _SPECIAL_KEYS:
        virtual_key = _SPECIAL_KEYS[key_name]
        key_name = "Esc" if key_name == "ESCAPE" else key_name.title()
    else:
        raise ValueError("Supported keys: A-Z, 0-9, F1-F24, Space, Tab, Enter, Esc, Home, End, Insert, Delete, PageUp, PageDown.")

    order = [name.title() for name in ("CTRL", "ALT", "SHIFT", "WIN") if name in modifier_names]
    display_key = key_name if key_name.startswith("F") else key_name.title()
    return ParsedHotkey(modifiers, virtual_key, "+".join([*order, display_key]))


class GlobalHotkey:
    """Registers a global Windows hotkey on a dedicated message thread."""

    HOTKEY_ID = 1

    def __init__(self, on_pressed: Callable[[], None]) -> None:
        self._on_pressed = on_pressed
        self._commands: Queue[tuple[str, ParsedHotkey | None, Queue | None]] = Queue()
        self._stop = Event()
        self._thread = Thread(target=self._run, name="PrivacyScreenHotkey", daemon=True)
        self._thread.start()

    def register(self, parsed: ParsedHotkey) -> None:
        result: Queue[Exception | None] = Queue(maxsize=1)
        self._commands.put(("register", parsed, result))
        error = result.get(timeout=3)
        if error:
            raise error

    def close(self) -> None:
        self._commands.put(("stop", None, None))
        self._thread.join(timeout=2)

    def _run(self) -> None:
        registered = False
        message = wintypes.MSG()
        while not self._stop.is_set():
            try:
                command, hotkey, result = self._commands.get(timeout=0.02)
                if command == "stop":
                    self._stop.set()
                    continue
                if command == "register" and hotkey is not None:
                    if registered:
                        user32.UnregisterHotKey(None, self.HOTKEY_ID)
                    ok = user32.RegisterHotKey(
                        None, self.HOTKEY_ID, hotkey.modifiers | MOD_NOREPEAT, hotkey.virtual_key
                    )
                    registered = bool(ok)
                    error = None if ok else RuntimeError(
                        "Windows could not register this hotkey. It may be used by another application."
                    )
                    if result is not None:
                        result.put(error)
            except Empty:
                pass

            while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, PM_REMOVE):
                if message.message == WM_HOTKEY and message.wParam == self.HOTKEY_ID:
                    self._on_pressed()

        if registered:
            user32.UnregisterHotKey(None, self.HOTKEY_ID)
