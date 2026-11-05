from __future__ import annotations

import ctypes
import os
from pathlib import Path

SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


def set_wallpaper(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if os.name != "nt":
        raise OSError("Setting the desktop wallpaper requires Windows")
    result = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, str(path), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    if not result:
        error = ctypes.get_last_error()
        raise OSError(error, f"Windows could not set wallpaper: {path}")


def current_wallpaper() -> str | None:
    if os.name != "nt":
        return None
    buffer = ctypes.create_unicode_buffer(32768)
    if ctypes.windll.user32.SystemParametersInfoW(0x0073, len(buffer), buffer, 0):
        return buffer.value
    return None
