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
        for path in (self.root, self.config, self.cache, self.logs, self.downloads, self.favorites):
            path.mkdir(parents=True, exist_ok=True)
        return self


def get_paths(portable: bool = False) -> AppPaths:
    executable_dir = Path(sys.executable).resolve().parent
    flag = executable_dir / "portable.flag"
    if portable or flag.exists():
        root = executable_dir / "data"
    else:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local"))
        root = base / "WindowsWallpaper"
    config = root / "config"
    return AppPaths(root, config, root / "cache", root / "logs", root / "downloads", root / "favorites", root / "wallpapers.sqlite3")
