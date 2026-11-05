from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class Catalog:
    def __init__(self, database: Path):
        self.database = database
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(database), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        with self._lock, self.conn:
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS images (
                path TEXT PRIMARY KEY, source TEXT NOT NULL, added REAL NOT NULL,
                width INTEGER NOT NULL DEFAULT 0, height INTEGER NOT NULL DEFAULT 0,
                bytes INTEGER NOT NULL DEFAULT 0, title TEXT NOT NULL DEFAULT '',
                origin_url TEXT NOT NULL DEFAULT '', favorite INTEGER NOT NULL DEFAULT 0,
                bad INTEGER NOT NULL DEFAULT 0, last_used REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT NOT NULL, used_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS history_used_at ON history(used_at DESC);
            """)

    def set_setting(self, key: str, value: Any) -> None:
        encoded = json.dumps(value)
        with self._lock, self.conn:
            self.conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, encoded))

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return default

    def upsert_image(self, path: str, source: str, width: int, height: int, size: int, title: str = "", origin_url: str = "") -> None:
        with self._lock, self.conn:
            self.conn.execute("""INSERT INTO images(path,source,added,width,height,bytes,title,origin_url)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET source=excluded.source,
                width=excluded.width,height=excluded.height,bytes=excluded.bytes,title=excluded.title,
                origin_url=excluded.origin_url,bad=0""", (path, source, time.time(), width, height, size, title, origin_url))

    def mark_bad(self, path: str) -> None:
        with self._lock, self.conn:
            self.conn.execute("UPDATE images SET bad=1 WHERE path=?", (path,))

    def list_images(self, sources: list[str], min_width: int = 0, landscape: bool = False, pattern: str = "", max_bytes: int = 0) -> list[sqlite3.Row]:
        if not sources:
            return []
        clauses = ["bad=0", "source IN (%s)" % ",".join("?" * len(sources))]
        args: list[Any] = list(sources)
        if min_width: clauses.append("width >= ?"); args.append(min_width)
        if landscape: clauses.append("width >= height")
        if max_bytes: clauses.append("bytes <= ?"); args.append(max_bytes)
        if pattern:
            escaped = pattern.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("path LIKE ? ESCAPE '\\'"); args.append(f"%{escaped}%")
        query = "SELECT * FROM images WHERE " + " AND ".join(clauses) + " ORDER BY last_used ASC, RANDOM()"
        with self._lock:
            return list(self.conn.execute(query, args))

    def record_used(self, path: str) -> None:
        now = time.time()
        with self._lock, self.conn:
            self.conn.execute("UPDATE images SET last_used=? WHERE path=?", (now, path))
            self.conn.execute("INSERT INTO history(path,used_at) VALUES(?,?)", (path, now))
            self.conn.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY used_at DESC LIMIT 1000)")

    def history(self, limit: int = 100) -> list[sqlite3.Row]:
        with self._lock:
            return list(self.conn.execute("SELECT h.path,h.used_at,i.title,i.origin_url FROM history h LEFT JOIN images i ON i.path=h.path ORDER BY h.used_at DESC LIMIT ?", (limit,)))

    def set_favorite(self, path: str, value: bool) -> None:
        with self._lock, self.conn:
            self.conn.execute("UPDATE images SET favorite=? WHERE path=?", (int(value), path))

    def favorites(self) -> list[sqlite3.Row]:
        with self._lock:
            return list(self.conn.execute("SELECT * FROM images WHERE favorite=1 ORDER BY last_used DESC"))

    def close(self) -> None:
        with self._lock:
            self.conn.close()
