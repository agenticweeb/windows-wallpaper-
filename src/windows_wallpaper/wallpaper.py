from __future__ import annotations

import os
from pathlib import Path


def set_wallpaper(path: Path) -> None:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if os.name != "nt":
        raise RuntimeError("Changing the desktop wallpaper requires Windows")
    import ctypes
    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    ok = ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, str(path), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
    if not ok:
        raise ctypes.WinError()
