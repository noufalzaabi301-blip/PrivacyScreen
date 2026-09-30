"""Switch Windows between duplicated and extended desktop modes."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess


def _display_switch(argument: str) -> None:
    """Start the built-in Windows display-mode switcher without a console."""
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "DisplaySwitch.exe"
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [str(executable), argument],
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def switch_to_extend() -> None:
    _display_switch("/extend")


def switch_to_duplicate() -> None:
    _display_switch("/clone")
