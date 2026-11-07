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
from .providers import bing_images, download_image, reddit_images, scan_folder, wallhaven_images
from .quotes import fetch_quote, random_custom_quote
from .overlay import render_quote
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
        self.quote_enabled = bool(self.catalog.get_setting("quote_enabled", False))
        self.quote_text = str(self.catalog.get_setting("quote_text", ""))
        self.quote_author = str(self.catalog.get_setting("quote_author", ""))
        self.quote_font_size = int(self.catalog.get_setting("quote_font_size", 42))
        self.quote_color = str(self.catalog.get_setting("quote_color", "#ffffff"))
        self.quote_bg_opacity = int(self.catalog.get_setting("quote_bg_opacity", 45))
        self.quote_width = int(self.catalog.get_setting("quote_width", 68))
        self.quote_hpos = int(self.catalog.get_setting("quote_hpos", 50))
        self.quote_vpos = int(self.catalog.get_setting("quote_vpos", 78))
        self.quote_source = str(self.catalog.get_setting("quote_source", "quotable"))
        self.quote_tags = str(self.catalog.get_setting("quote_tags", ""))
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
        settings = (("interval", self.interval), ("min_width", self.min_width), ("landscape", self.landscape), ("pattern", self.pattern), ("paused", self.paused), ("quote_enabled", self.quote_enabled), ("quote_text", self.quote_text), ("quote_author", self.quote_author), ("quote_font_size", self.quote_font_size), ("quote_color", self.quote_color), ("quote_bg_opacity", self.quote_bg_opacity), ("quote_width", self.quote_width), ("quote_hpos", self.quote_hpos), ("quote_vpos", self.quote_vpos), ("quote_source", self.quote_source), ("quote_tags", self.quote_tags))
        for key, value in settings:
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
        self._download_items(bing_images, "Bing")

    def download_wallhaven(self, query: str = "anime") -> None:
        self._download_items(lambda: wallhaven_images(query), f"Wallhaven · {query}")

    def download_reddit(self, subreddit: str = "Animewallpaper") -> None:
        self._download_items(lambda: reddit_images(subreddit), f"Reddit · r/{subreddit}")

    def _download_items(self, provider, label: str) -> None:
        def work() -> None:
            try:
                self.events.put(("status", f"Downloading {label} wallpapers…"))
                source_name = label.split(" ", 1)[0].lower()
                for item in provider():
                    safe_name = source_name + "-" + hashlib.sha256(item["url"].encode()).hexdigest()[:20] + ".jpg"
                    path, width, height, origin = download_image(item["url"], self.paths.downloads / safe_name, origin_url=item["origin"])
                    self.catalog.upsert_image(str(path), source_name, width, height, path.stat().st_size, item["title"], origin)
                self.events.put(("status", f"{label} wallpapers are ready"))
            except Exception as exc:
                log.exception("%s download failed", label)
                self.events.put(("error", f"{label} download failed: {exc}"))
        worker = threading.Thread(target=work, name="bing-download", daemon=True)
        self.workers.append(worker)
        worker.start()

    def fetch_quote(self) -> None:
        def work() -> None:
            try:
                quote = random_custom_quote(self.paths.config / "quotes.txt") if self.quote_source == "custom" else fetch_quote(self.quote_source, self.quote_tags)
                self.quote_text, self.quote_author = quote["quote"], quote["author"]
                self.save_settings()
                self.events.put(("quote", f"{self.quote_text} — {self.quote_author}"))
            except Exception as exc:
                self.events.put(("error", f"Quote source failed: {exc}"))
        worker = threading.Thread(target=work, name="quote-fetch", daemon=True)
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
        rows = self.catalog.list_images(["local", "bing", "wallhaven", "reddit"], self.min_width, self.landscape, self.pattern)
        candidates = [Path(row["path"]) for row in rows if Path(row["path"]).is_file() and Path(row["path"]) != self.current]
        if not candidates:
            self.events.put(("error", "No matching wallpapers. Add a folder or change filters."))
            return
        self._apply(random.choice(candidates))

    def _apply(self, path: Path) -> None:
        try:
            wallpaper_path = path
            if self.quote_enabled and self.quote_text.strip():
                rendered = self.paths.cache / "rendered" / (hashlib.sha256(f"{path}|{self.quote_text}|{self.quote_author}|{self.quote_hpos}|{self.quote_vpos}".encode()).hexdigest() + ".jpg")
                wallpaper_path = render_quote(path, rendered, self.quote_text, self.quote_author, font_size=self.quote_font_size, text_color=self.quote_color, background_opacity=self.quote_bg_opacity, width_percent=self.quote_width, hpos=self.quote_hpos, vpos=self.quote_vpos)
            set_wallpaper(wallpaper_path)
            self.current = path
            self.catalog.set_setting("current", str(path))
            self.catalog.record_used(str(path))
            self.events.put(("current", str(path)))
        except Exception as exc:
            log.exception("Could not set wallpaper")
            self.events.put(("error", f"Could not set wallpaper: {exc}"))

    def self_test(self) -> dict[str, str]:
        return {"version": __version__, "database": str(self.paths.database), "status": "ok"}
