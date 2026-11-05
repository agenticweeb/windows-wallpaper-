from pathlib import Path

import pytest

from windows_wallpaper.paths import get_paths
from windows_wallpaper.providers import download_image
from windows_wallpaper.storage import Catalog


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
