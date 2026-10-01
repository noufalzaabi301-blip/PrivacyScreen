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
        """Create the application settings window."""
        frame = ttk.Frame(self.root, padding=20)
        frame.grid(sticky="nsew")

        # Application title
        ttk.Label(
            frame,
            text="Privacy Screen",
            font=("Segoe UI", 16, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 6),
        )

        # Formal application description
        description = (
            "Privacy Screen protects information shown on an external display. "
            "When activated, it moves open windows back to the laptop and places "
            "a black privacy screen over the projector or external monitor."
        )

        ttk.Label(
            frame,
            text=description,
            foreground="#555555",
            justify="left",
            wraplength=560,
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 18),
        )

        # Global hotkey selection
        ttk.Label(
            frame,
            text="Global hotkey:",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=5,
        )

        hotkey_options = [
            "F8",
            "F9",
            "F10",
            "F11",
            "F12",
            "Ctrl+Shift+P",
            "Ctrl+Alt+P",
            "Ctrl+Shift+B",
            "Win+Alt+1",
        ]

        self.hotkey_combo = ttk.Combobox(
            frame,
            textvariable=self.hotkey_var,
            values=hotkey_options,
            width=35,
            state="readonly",
        )
        self.hotkey_combo.grid(
            row=2,
            column=1,
            sticky="ew",
            pady=5,
        )

        # Examples below the global hotkey
        ttk.Label(
            frame,
            text="Available examples: F8, Ctrl+Shift+P, Win+Alt+1",
            foreground="#666666",
        ).grid(
            row=3,
            column=1,
            sticky="w",
            pady=(0, 10),
        )

        # External-screen selection
        ttk.Label(
            frame,
            text="Screen:",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=5,
        )

        self.monitor_combo = ttk.Combobox(
            frame,
            textvariable=self.monitor_var,
            width=35,
            state="readonly",
        )
        self.monitor_combo.grid(
            row=4,
            column=1,
            sticky="ew",
            pady=5,
        )

        # Buttons
        buttons = ttk.Frame(frame)
        buttons.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="e",
            pady=(16, 0),
        )

        ttk.Button(
            buttons,
            text="Refresh Screen",
            command=self.refresh_monitors,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            buttons,
            text="Save Settings",
            command=self.save_settings,
        ).pack(side="left")

        # Status message
        ttk.Label(
            frame,
            textvariable=self.status_var,
            foreground="#444444",
            wraplength=560,
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(18, 0),
        )

    def refresh_monitors(self) -> None:
        """Refresh monitors and keep automatic screen selection enabled."""
        self.monitors = enumerate_monitors()
        self.monitor_combo["values"] = ["Automatic external screen"]
        self.monitor_var.set("Automatic external screen")

    def _selected_device(self) -> str:
        """Always select the external display automatically."""
        return "AUTO"

    def _projector_monitor(self) -> Monitor | None:
        """Find the selected external screen or the first available one."""
        self.monitors = enumerate_monitors()

        selected = next(
            (
                monitor
                for monitor in self.monitors
                if monitor.device_name == self.config.monitor
            ),
            None,
        )

        if selected is not None and not selected.primary:
            return selected

        return next(
            (monitor for monitor in self.monitors if not monitor.primary),
            None,
        )

    def save_settings(self) -> None:
        """Validate and save the selected global hotkey."""
        try:
            parsed = parse_hotkey(self.hotkey_var.get())
            self.hotkey.register(parsed)
        except (ValueError, RuntimeError) as error:
            messagebox.showerror(
                "Invalid hotkey",
                str(error),
                parent=self.root,
            )
            return

        self.config = AppConfig(
            hotkey=parsed.canonical,
            monitor=self._selected_device(),
        )

        self.hotkey_var.set(parsed.canonical)
        self.store.save(self.config)
        self.status_var.set(
            f"Saved. Press {parsed.canonical} to toggle."
        )

    def show_settings(self) -> None:
        """Show and focus the settings window."""
        self.refresh_monitors()
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(
            100,
            lambda: self.root.attributes("-topmost", False),
        )
        self.root.focus_force()

    def hide_settings(self) -> None:
        """Hide the settings window without closing the application."""
        self.root.withdraw()

    def toggle(self) -> None:
        """Enable or disable privacy mode."""
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
                self.status_var.set(
                    "Privacy off. Extended mode remains active."
                )
                self.transitioning = False

            return

        current_monitors = enumerate_monitors()

        # When Windows reports fewer than two desktop monitors, the system is
        # probably using Duplicate mode. Switch to Extend before covering the
        # external screen.
        self.restore_duplicate = len(current_monitors) < 2

        if self.restore_duplicate:
            self.status_var.set("Switching to Extend mode...")
            switch_to_extend()

            # DisplaySwitch returns before Windows finishes rebuilding
            # the extended desktop.
            self.root.after(
                750,
                lambda: self._wait_for_projector(
                    attempts_remaining=24
                ),
            )
        else:
            self._wait_for_projector(attempts_remaining=1)

    def _wait_for_projector(
        self,
        attempts_remaining: int,
    ) -> None:
        """Wait for Windows to publish the external monitor."""
        projector = self._projector_monitor()

        if projector is not None:
            primary = next(
                (
                    monitor
                    for monitor in self.monitors
                    if monitor.primary
                ),
                None,
            )

            moved = (
                move_windows_to_monitor(projector, primary)
                if primary is not None
                else 0
            )

            self.overlay.show([projector])
            self.privacy_active = True
            self.transitioning = False

            self.status_var.set(
                "Privacy active: projector is black; "
                f"{moved} window(s) moved to the laptop."
            )
            return

        if attempts_remaining > 0:
            self.root.after(
                250,
                lambda: self._wait_for_projector(
                    attempts_remaining - 1
                ),
            )
            return

        self.transitioning = False
        self.status_var.set("No external screen was found.")
        self.show_settings()

        messagebox.showerror(
            "Projector not found",
            (
                "Windows switched display mode, but no external screen "
                "was detected. Check the cable and click Refresh screens."
            ),
            parent=self.root,
        )

    def _finish_transition(self) -> None:
        """Allow another hotkey action after a display-mode change."""
        self.transitioning = False

    def _poll_actions(self) -> None:
        """Process actions received from the hotkey and system tray."""
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
        """Close the application and restore Duplicate mode if required."""
        self.overlay.hide()

        if self.privacy_active and self.restore_duplicate:
            switch_to_duplicate()

        self.privacy_active = False
        self.hotkey.close()
        self.tray.stop()
        self.root.destroy()

    def run(self) -> None:
        """Register the hotkey, start the tray icon, and run the app."""
        try:
            parsed = parse_hotkey(self.config.hotkey)
            self.hotkey.register(parsed)
            self.status_var.set(
                f"Ready. Press {parsed.canonical} to toggle."
            )
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
    """Start Privacy Screen."""
    PrivacyScreenApp().run()
