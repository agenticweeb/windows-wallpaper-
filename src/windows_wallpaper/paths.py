from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    config: Path
    cache: Path
    logs: Path
    downloads: Path
    favorites: Path
    database: Path

    def create(self) -> "AppPaths":
        for path in (self.config, self.cache, self.logs, self.downloads, self.favorites):
            path.mkdir(parents=True, exist_ok=True)
        return self


def get_paths(portable: bool | None = None) -> AppPaths:
    if portable is None:
        portable = "--portable" in sys.argv or (Path(sys.executable).parent / "portable.flag").exists()
    if portable:
        root = Path(sys.executable).resolve().parent / "data"
    else:
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local"))
        root = local / "WindowsWallpaper"
    return AppPaths(
        root=root,
        config=root / "config",
        cache=root / "cache",
        logs=root / "logs",
        downloads=Path.home() / "Pictures" / "Windows Wallpaper" / "Downloads",
        favorites=Path.home() / "Pictures" / "Windows Wallpaper" / "Favorites",
        database=root / "wallpapers.sqlite3",
    )
