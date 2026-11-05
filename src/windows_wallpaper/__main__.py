from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .app import WallpaperApp
from .paths import get_paths


def _acquire_single_instance():
    if os.name != "nt":
        return None
    import ctypes

    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, "Local\\WindowsWallpaper-0.1")
    if not mutex:
        return None
    if kernel32.GetLastError() == 183:
        kernel32.CloseHandle(mutex)
        return False
    return mutex


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lightweight Windows wallpaper manager")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--portable", action="store_true")
    parser.add_argument("--add-folder", type=Path)
    parser.add_argument("--next", dest="next_wallpaper", action="store_true")
    parser.add_argument("--previous", action="store_true")
    parser.add_argument("--pause", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    instance = _acquire_single_instance()
    if instance is False:
        print("Windows Wallpaper is already running.", file=sys.stderr)
        return 0
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    app = WallpaperApp(get_paths(args.portable))
    try:
        if args.self_test:
            print(json.dumps(app.self_test(), indent=2)); return 0
        if args.add_folder:
            app.add_folder(args.add_folder); print(f"Added folder: {args.add_folder}"); return 0
        if args.next_wallpaper or args.previous or args.pause or args.resume:
            app.start()
            if args.next_wallpaper: app.next()
            if args.previous: app.previous()
            if args.pause: app.set_paused(True)
            if args.resume: app.set_paused(False)
            return 0
        from .ui import MainWindow
        MainWindow(app).run()
        return 0
    finally:
        app.close()
        if instance and os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.CloseHandle(instance)


if __name__ == "__main__":
    raise SystemExit(main())
