from pathlib import Path

import pytest

from windows_wallpaper.paths import get_paths
from windows_wallpaper.overlay import render_quote
from windows_wallpaper.providers import download_image
from windows_wallpaper.storage import Catalog
from PIL import Image


def test_portable_paths(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.executable", str(tmp_path / "WindowsWallpaper.exe"))
    paths = get_paths(True)
    assert paths.database == tmp_path / "data" / "wallpapers.sqlite3"


def test_catalog_persists_settings(tmp_path):
    catalog = Catalog(tmp_path / "db.sqlite3")
    catalog.set_setting("interval", 123)
    assert catalog.get_setting("interval") == 123
    catalog.upsert_image(str(tmp_path / "a.jpg"), "local", 1920, 1080, 100)
    assert len(catalog.list_images(["local"], 1000, True)) == 1
    catalog.close()


def test_catalog_persists_current_wallpaper(tmp_path):
    database = tmp_path / "db.sqlite3"
    catalog = Catalog(database)
    catalog.set_setting("current", str(tmp_path / "wallpaper.jpg"))
    catalog.close()
    reopened = Catalog(database)
    assert reopened.get_setting("current") == str(tmp_path / "wallpaper.jpg")
    reopened.close()


def test_download_rejects_unsafe_urls(tmp_path):
    with pytest.raises(ValueError):
        download_image("file:///etc/passwd", tmp_path / "x.jpg")
    with pytest.raises(ValueError):
        download_image("https://user:pass@example.com/x.jpg", tmp_path / "x.jpg")


def test_catalog_reconciles_deleted_local_images(tmp_path):
    catalog = Catalog(tmp_path / "db.sqlite3")
    image = tmp_path / "Summer.JPG"
    catalog.upsert_image(str(image), "local", 1920, 1080, 100)
    assert len(catalog.list_images(["local"], pattern="summer")) == 1
    assert catalog.reconcile_local(set()) == 1
    assert catalog.list_images(["local"]) == []
    catalog.close()


def test_quote_overlay_writes_a_new_wallpaper_copy(tmp_path):
    source = tmp_path / "original.jpg"
    rendered = tmp_path / "cache" / "rendered.jpg"
    Image.new("RGB", (1280, 720), "#345").save(source)
    render_quote(source, rendered, "Keep going", "Variety", font_size=42, hpos=50, vpos=78)
    assert rendered.exists()
    assert Image.open(source).size == Image.open(rendered).size
    assert source.read_bytes() != rendered.read_bytes()
