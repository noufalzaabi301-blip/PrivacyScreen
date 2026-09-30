"""Main application coordinator and settings UI."""

from __future__ import annotations

from queue import Empty, Queue
import tkinter as tk
from tkinter import messagebox, ttk

from .config import AppConfig, ConfigStore
from .display_mode import switch_to_duplicate, switch_to_extend
from .models import Monitor
from .overlay import OverlayController
from .tray import TrayController
from .windows_api import (
    GlobalHotkey,
    enable_per_monitor_dpi_awareness,
    enumerate_monitors,
    move_windows_to_monitor,
    parse_hotkey,
)


class PrivacyScreenApp:
    POLL_MS = 30

    def __init__(self) -> None:
        enable_per_monitor_dpi_awareness()
        self.root = tk.Tk()
        self.root.title("Privacy Screen Settings")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_settings)

        self.store = ConfigStore()
        self.first_run = not self.store.path.exists()
        self.config = self.store.load()
        self.actions: Queue[str] = Queue()
        self.monitors: list[Monitor] = []
        self.privacy_active = False
        self.transitioning = False
        self.restore_duplicate = False
        self.overlay = OverlayController(self.root)
        self.hotkey = GlobalHotkey(lambda: self.actions.put("toggle"))
        self.tray = TrayController(
            lambda: self.actions.put("toggle"),
            lambda: self.actions.put("settings"),
            lambda: self.actions.put("exit"),
        )

        self.hotkey_var = tk.StringVar(value=self.config.hotkey)
        self.monitor_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self._build_settings()
        self.refresh_monitors()

    def _build_settings(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="Privacy Screen", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
        )
        ttk.Label(frame, text="Global hotkey:").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Entry(frame, textvariable=self.hotkey_var, width=28).grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Label(frame, text="Screen:").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=5)
        self.monitor_combo = ttk.Combobox(frame, textvariable=self.monitor_var, width=35, state="readonly")
        self.monitor_combo.grid(row=2, column=1, sticky="ew", pady=5)

        note = (
            "Examples: F8, Ctrl+Shift+P, Win+Alt+1\n"
            "Moves external windows to the laptop, then blacks the projector."
        )
        ttk.Label(frame, text=note, foreground="#555555", justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 14)
        )
        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Refresh screens", command=self.refresh_monitors).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Save", command=self.save_settings).pack(side="left")
        ttk.Label(frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=2, sticky="w", pady=(14, 0))

    def refresh_monitors(self) -> None:
        previous_device = self._selected_device()
        self.monitors = enumerate_monitors()
values = ["Automatic external screen"]
        self.monitor_combo["values"] = values
       self.monitor_var.set("Automatic external screen")
       
    def _selected_device(self) -> str:
    return "AUTO"

    def _projector_monitor(self) -> Monitor | None:
        self.monitors = enumerate_monitors()
        selected = next((m for m in self.monitors if m.device_name == self.config.monitor), None)
        if selected is not None and not selected.primary:
            return selected
        return next((m for m in self.monitors if not m.primary), None)

    def save_settings(self) -> None:
        try:
            parsed = parse_hotkey(self.hotkey_var.get())
            self.hotkey.register(parsed)
        except (ValueError, RuntimeError) as error:
            messagebox.showerror("Invalid hotkey", str(error), parent=self.root)
            return

        self.config = AppConfig(hotkey=parsed.canonical, monitor=self._selected_device())
        self.hotkey_var.set(parsed.canonical)
        self.store.save(self.config)
        self.status_var.set(f"Saved. Press {parsed.canonical} to toggle.")

    def show_settings(self) -> None:
        self.refresh_monitors()
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(100, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

    def hide_settings(self) -> None:
        self.root.withdraw()

    def toggle(self) -> None:
        """Enter private mode, or restore duplicated output on the next press."""
        if self.transitioning:
            return
        self.transitioning = True

        if self.privacy_active:
            self.overlay.hide()
            self.privacy_active = False
            if self.restore_duplicate:
                switch_to_duplicate()
                self.status_var.set("Duplicate mode restored.")
                self.root.after(1200, self._finish_transition)
            else:
                self.status_var.set("Privacy off. Extended mode remains active.")
                self.transitioning = False
            return

        current_monitors = enumerate_monitors()
        self.restore_duplicate = len(current_monitors) < 2
        if self.restore_duplicate:
            self.status_var.set("Switching to Extend mode…")
            switch_to_extend()
            # DisplaySwitch returns before Windows finishes rebuilding the desktop.
            self.root.after(750, lambda: self._wait_for_projector(attempts_remaining=24))
        else:
            self._wait_for_projector(attempts_remaining=1)

    def _wait_for_projector(self, attempts_remaining: int) -> None:
        """Wait for Windows to publish the external monitor after mode change."""
        projector = self._projector_monitor()
        if projector is not None:
            primary = next((monitor for monitor in self.monitors if monitor.primary), None)
            moved = move_windows_to_monitor(projector, primary) if primary is not None else 0
            self.overlay.show([projector])
            self.privacy_active = True
            self.transitioning = False
            self.status_var.set(
                f"Privacy active: projector is black; {moved} window(s) moved to the laptop."
            )
            return
        if attempts_remaining > 0:
            self.root.after(250, lambda: self._wait_for_projector(attempts_remaining - 1))
            return

        self.transitioning = False
        self.status_var.set("No external screen was found.")
        self.show_settings()
        messagebox.showerror(
            "Projector not found",
            "Windows switched display mode, but no external screen was detected. Check the cable and click Refresh screens.",
            parent=self.root,
        )

    def _finish_transition(self) -> None:
        self.transitioning = False

    def _poll_actions(self) -> None:
        try:
            while True:
                action = self.actions.get_nowait()
                if action == "toggle":
                    self.toggle()
                elif action == "settings":
                    self.show_settings()
                elif action == "exit":
                    self.shutdown()
                    return
        except Empty:
            pass
        self.root.after(self.POLL_MS, self._poll_actions)

    def shutdown(self) -> None:
        self.overlay.hide()
        if self.privacy_active and self.restore_duplicate:
            switch_to_duplicate()
        self.privacy_active = False
        self.hotkey.close()
        self.tray.stop()
        self.root.destroy()

    def run(self) -> None:
        try:
            parsed = parse_hotkey(self.config.hotkey)
            self.hotkey.register(parsed)
            self.status_var.set(f"Ready. Press {parsed.canonical} to toggle.")
        except (ValueError, RuntimeError) as error:
            self.status_var.set(str(error))
            self.root.deiconify()
        else:
            if self.first_run:
                self.root.deiconify()
            else:
                self.root.withdraw()
        self.tray.start()
        self.root.after(self.POLL_MS, self._poll_actions)
        self.root.mainloop()


def main() -> None:
    PrivacyScreenApp().run()
