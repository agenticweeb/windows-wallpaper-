from __future__ import annotations

import hashlib
import logging
import queue
import random
import shutil
import threading
import time
from pathlib import Path

from . import __version__
from .paths import AppPaths, get_paths
from .providers import bing_images, download_image, scan_folder
from .storage import Catalog
from .wallpaper import set_wallpaper

log = logging.getLogger("windows_wallpaper")


class WallpaperApp:
    def __init__(self, paths: AppPaths | None = None):
        self.paths = (paths or get_paths()).create()
        self.catalog = Catalog(self.paths.database)
        self.folders: list[Path] = [Path(p) for p in self.catalog.get_setting("folders", [])]
        self.interval = max(30, int(self.catalog.get_setting("interval", 300)))
        self.min_width = int(self.catalog.get_setting("min_width", 0))
        self.landscape = bool(self.catalog.get_setting("landscape", True))
        self.pattern = str(self.catalog.get_setting("pattern", ""))
        self.paused = bool(self.catalog.get_setting("paused", True))
        saved_current = self.catalog.get_setting("current", "")
        self.current: Path | None = Path(saved_current) if saved_current and Path(saved_current).is_file() else None
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self.thread = threading.Thread(target=self._rotation_loop, name="rotation", daemon=True)
        self.workers: list[threading.Thread] = []

    def start(self) -> None:
        self.scan()
        if not self.thread.is_alive():
            if self.thread.ident is not None:
                self.thread = threading.Thread(target=self._rotation_loop, name="rotation", daemon=True)
            self.thread.start()

    def close(self) -> None:
        self.stop_event.set()
        self.wake_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=10)
        for worker in self.workers:
            worker.join(timeout=10)
        self.catalog.close()

    def save_settings(self) -> None:
        self.catalog.set_setting("folders", [str(p) for p in self.folders])
        for key, value in (("interval", self.interval), ("min_width", self.min_width), ("landscape", self.landscape), ("pattern", self.pattern), ("paused", self.paused)):
            self.catalog.set_setting(key, value)

    def add_folder(self, folder: Path) -> None:
        folder = folder.expanduser().resolve()
        if folder.is_dir() and folder not in self.folders:
            self.folders.append(folder)
            self.save_settings()
            self.scan()

    def remove_folder(self, folder: Path) -> None:
        self.folders = [p for p in self.folders if p != folder]
        self.save_settings()
        self.scan()

    def scan(self) -> int:
        count = 0
        valid_paths: set[str] = set()
        for folder in self.folders:
            for path, width, height, size in scan_folder(folder):
                resolved = str(path.resolve())
                valid_paths.add(resolved)
                self.catalog.upsert_image(resolved, "local", width, height, size)
                count += 1
        self.catalog.reconcile_local(valid_paths)
        self.events.put(("status", f"Cataloged {count} image(s)"))
        return count

    def download_bing(self) -> None:
        def work() -> None:
            try:
                self.events.put(("status", "Downloading Bing wallpapers…"))
                for item in bing_images():
                    safe_name = "bing-" + hashlib.sha256(item["url"].encode()).hexdigest()[:20] + ".jpg"
                    path, width, height, origin = download_image(item["url"], self.paths.downloads / safe_name, origin_url=item["origin"])
                    self.catalog.upsert_image(str(path), "bing", width, height, path.stat().st_size, item["title"], origin)
                self.events.put(("status", "Bing wallpapers are ready"))
            except Exception as exc:
                log.exception("Bing download failed")
                self.events.put(("error", f"Bing download failed: {exc}"))
        worker = threading.Thread(target=work, name="bing-download", daemon=True)
        self.workers.append(worker)
        worker.start()

    def set_interval(self, seconds: int) -> None:
        self.interval = max(30, int(seconds))
        self.save_settings()
        self.wake_event.set()

    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        self.save_settings()
        self.events.put(("state", paused))
        self.wake_event.set()

    def next(self) -> None:
        self._change_wallpaper()

    def previous(self) -> None:
        history = self.catalog.history(20)
        paths = [Path(row[0]) for row in history if Path(row[0]).exists()]
        if len(paths) > 1:
            self._apply(paths[1])
        else:
            self.events.put(("status", "No previous wallpaper is available"))

    def favorite(self) -> None:
        if not self.current or not self.current.exists():
            return
        target = self.paths.favorites / self.current.name
        if target.exists():
            target = target.with_name(f"{target.stem}-{int(time.time())}{target.suffix}")
        try:
            shutil.copy2(self.current, target)
            self.catalog.set_favorite(str(self.current), True)
            self.events.put(("status", f"Saved favorite: {target.name}"))
        except OSError as exc:
            log.exception("Could not save favorite")
            self.events.put(("error", f"Could not save favorite: {exc}"))

    def _rotation_loop(self) -> None:
        while not self.stop_event.is_set():
            if self.paused:
                self.wake_event.wait(1)
                self.wake_event.clear()
                continue
            self._change_wallpaper()
            self.wake_event.wait(self.interval)
            self.wake_event.clear()

    def _change_wallpaper(self) -> None:
        rows = self.catalog.list_images(["local", "bing"], self.min_width, self.landscape, self.pattern)
        candidates = [Path(row["path"]) for row in rows if Path(row["path"]).is_file() and Path(row["path"]) != self.current]
        if not candidates:
            self.events.put(("error", "No matching wallpapers. Add a folder or change filters."))
            return
        self._apply(random.choice(candidates))

    def _apply(self, path: Path) -> None:
        try:
            set_wallpaper(path)
            self.current = path
            self.catalog.set_setting("current", str(path))
            self.catalog.record_used(str(path))
            self.events.put(("current", str(path)))
        except Exception as exc:
            log.exception("Could not set wallpaper")
            self.events.put(("error", f"Could not set wallpaper: {exc}"))

    def self_test(self) -> dict[str, str]:
        return {"version": __version__, "database": str(self.paths.database), "status": "ok"}
