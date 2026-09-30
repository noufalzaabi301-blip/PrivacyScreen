"""Persistent JSON configuration."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppConfig:
    hotkey: str = "F8"
    monitor: str = "AUTO"


class ConfigStore:
    """Loads and atomically saves settings in the user's AppData folder."""

    def __init__(self) -> None:
        appdata = Path(os.environ.get("APPDATA", Path.home()))
        self.path = appdata / "PrivacyScreen" / "settings.json"

    def load(self) -> AppConfig:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return AppConfig(
                hotkey=str(data.get("hotkey", "F8")),
                monitor=str(data.get("monitor", "AUTO")),
            )
        except (OSError, ValueError, TypeError):
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
        temporary.replace(self.path)
