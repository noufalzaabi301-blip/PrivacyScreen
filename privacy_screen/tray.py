"""System tray icon and menu."""

from __future__ import annotations

from collections.abc import Callable

from PIL import Image, ImageDraw
import pystray


def create_icon() -> Image.Image:
    """Create a crisp icon at runtime so no binary asset is required."""
    image = Image.new("RGBA", (64, 64), (20, 24, 32, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 12, 56, 48), radius=5, outline=(245, 245, 245), width=4)
    draw.rectangle((15, 19, 49, 41), fill=(0, 0, 0))
    draw.line((24, 55, 40, 55), fill=(245, 245, 245), width=4)
    draw.line((32, 48, 32, 55), fill=(245, 245, 245), width=4)
    return image


class TrayController:
    def __init__(self, on_toggle: Callable[[], None], on_settings: Callable[[], None], on_exit: Callable[[], None]) -> None:
        self.icon = pystray.Icon(
            "Privacy Screen",
            create_icon(),
            "Privacy Screen",
            menu=pystray.Menu(
                pystray.MenuItem("Toggle privacy screen", lambda _icon, _item: on_toggle(), default=True),
                pystray.MenuItem("Settings…", lambda _icon, _item: on_settings()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", lambda _icon, _item: on_exit()),
            ),
        )

    def start(self) -> None:
        self.icon.run_detached()

    def stop(self) -> None:
        self.icon.stop()
