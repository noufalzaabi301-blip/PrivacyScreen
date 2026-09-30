"""Data models used by Privacy Screen."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Monitor:
    """A physical or virtual monitor reported by Windows."""

    device_name: str
    left: int
    top: int
    right: int
    bottom: int
    primary: bool = False

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def label(self) -> str:
        primary = " (Primary)" if self.primary else ""
        return f"{self.device_name}{primary} — {self.width}×{self.height}"
