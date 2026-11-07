from __future__ import annotations

import json
import random
from pathlib import Path

import requests


def _quote(quote: str, author: str, source: str) -> dict[str, str]:
    return {"quote": quote.strip(), "author": author.strip() or "Unknown", "source": source}


def fetch_quote(source: str = "quotable", tags: str = "") -> dict[str, str]:
    source = source.lower().strip()
    if source == "zenquotes":
        response = requests.get("https://zenquotes.io/api/random", timeout=(8, 15), headers={"User-Agent": "WindowsWallpaper/0.2"})
        response.raise_for_status()
        item = response.json()[0]
        return _quote(item.get("q", ""), item.get("a", ""), "ZenQuotes")
    params = {"maxLength": "240"}
    if tags.strip():
        params["tags"] = tags.strip().split(",")[0].strip()
    response = requests.get("https://api.quotable.io/random", params=params, timeout=(8, 15), headers={"User-Agent": "WindowsWallpaper/0.2"})
    response.raise_for_status()
    item = response.json()
    return _quote(item.get("content", ""), item.get("author", ""), "Quotable")


def load_custom_quotes(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("quotes", [])
        return [_quote(str(item.get("quote", "")), str(item.get("author", "")), "Custom") for item in items if isinstance(item, dict) and item.get("quote")]
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        quote, _, author = line.partition("|")
        result.append(_quote(quote, author, "Custom"))
    return result


def random_custom_quote(path: Path) -> dict[str, str]:
    quotes = load_custom_quotes(path)
    if not quotes:
        raise ValueError("The custom quote file has no usable quotes")
    return random.choice(quotes)
