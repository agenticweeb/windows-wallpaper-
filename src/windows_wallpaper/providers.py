from __future__ import annotations

import hashlib
import re
import tempfile
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests
from PIL import Image, UnidentifiedImageError

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def scan_folder(folder: Path, limit: int = 10000):
    count = 0
    if not folder.exists():
        return
    try:
        paths = folder.rglob("*")
        for path in paths:
            if count >= limit:
                break
            try:
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                    with Image.open(path) as image:
                        image.verify()
                    with Image.open(path) as image:
                        yield path, image.width, image.height, path.stat().st_size
                        count += 1
            except (OSError, UnidentifiedImageError):
                continue
    except OSError:
        return


def download_image(url: str, target: Path, timeout: tuple[int, int] = (10, 30), max_bytes: int = 30 * 1024 * 1024, origin_url: str = "") -> tuple[Path, int, int, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise ValueError("Only unauthenticated HTTP(S) image URLs are allowed")
    target.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.max_redirects = 5
    response = session.get(url, stream=True, timeout=timeout, allow_redirects=True, headers={"User-Agent": "WindowsWallpaper/0.1"})
    try:
        response.raise_for_status()
        final = urlparse(response.url)
        if final.scheme not in {"http", "https"} or final.username or final.password:
            raise ValueError("Unsafe redirect target")
        length = int(response.headers.get("Content-Length", "0") or 0)
        if length > max_bytes:
            raise ValueError("Remote image is too large")
        with tempfile.NamedTemporaryFile(prefix="wallpaper-", suffix=".partial", dir=target.parent, delete=False) as handle:
            partial = Path(handle.name)
            total = 0
            for chunk in response.iter_content(1024 * 128):
                total += len(chunk)
                if total > max_bytes:
                    partial.unlink(missing_ok=True)
                    raise ValueError("Remote image is too large")
                handle.write(chunk)
    finally:
        response.close()
        session.close()
    try:
        with Image.open(partial) as image:
            image.verify()
        with Image.open(partial) as image:
            width, height = image.width, image.height
            if width < 200 or height < 200:
                raise ValueError("Image is too small")
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    if target.exists():
        target = target.with_name(f"{target.stem}-{hashlib.sha256(url.encode()).hexdigest()[:8]}{target.suffix}")
    partial.replace(target)
    return target, width, height, origin_url or url


def bing_images() -> list[dict[str, str]]:
    response = requests.get("https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=en-US", timeout=(10, 20), headers={"User-Agent": "WindowsWallpaper/0.1"})
    response.raise_for_status()
    items = []
    for item in response.json().get("images", []):
        if item.get("wp") is False:
            continue
        base = item.get("urlbase")
        if base:
            items.append({"url": "https://www.bing.com" + base + "_UHD.jpg", "origin": "https://www.bing.com" + item.get("url", ""), "title": item.get("copyright", "Bing Photo of the Day")})
    return items
