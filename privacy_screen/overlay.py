"""Black always-on-top windows used to cover selected monitors."""

from __future__ import annotations

import ctypes
import tkinter as tk

from .models import Monitor

HWND_TOPMOST = -1
SWP_SHOWWINDOW = 0x0040


class OverlayController:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.windows: list[tk.Toplevel] = []

    @property
    def visible(self) -> bool:
        return bool(self.windows)

    def show(self, monitors: list[Monitor]) -> None:
        self.hide()
        for monitor in monitors:
            window = tk.Toplevel(self.root)
            window.withdraw()
            window.configure(background="black", cursor="none")
            window.overrideredirect(True)
            window.attributes("-topmost", True)
            window.geometry(f"{monitor.width}x{monitor.height}{monitor.left:+d}{monitor.top:+d}")
            window.update_idletasks()
            hwnd = window.winfo_id()
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                monitor.left,
                monitor.top,
                monitor.width,
                monitor.height,
                SWP_SHOWWINDOW,
            )
            window.deiconify()
            window.lift()
            self.windows.append(window)

    def hide(self) -> None:
        for window in self.windows:
            try:
                window.destroy()
            except tk.TclError:
                pass
        self.windows.clear()

    def toggle(self, monitors: list[Monitor]) -> None:
        self.hide() if self.visible else self.show(monitors)
