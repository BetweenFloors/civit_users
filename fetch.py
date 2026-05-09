"""Fetch user data from Civitai official REST API only."""

from __future__ import annotations
import json
import time
import requests
from pathlib import Path

_API        = "https://civitai.com/api/v1"
_CACHE_DIR  = Path(__file__).parent / "cache"
_CACHE_TTL  = 12 * 3600  # 12 hours


def _cache_path(username: str, browsing_level: int) -> Path:
    return _CACHE_DIR / f"{username}_{browsing_level}.json"


def _load_cache(username: str, browsing_level: int) -> dict | None:
    path = _cache_path(username, browsing_level)
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > _CACHE_TTL:
        return None
    with path.open() as f:
        return json.load(f)


def _save_cache(username: str, browsing_level: int, data: dict):
    _CACHE_DIR.mkdir(exist_ok=True)
    with _cache_path(username, browsing_level).open("w") as f:
        json.dump(data, f)


def _get(token: str, path: str, params: dict) -> dict:
    r = requests.get(
        f"{_API}/{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def fetch_profile(token: str, username: str) -> dict:
    data = _get(token, "creators", {"query": username, "limit": 1})
    items = data.get("items", [])
    return items[0] if items else {"username": username}


def fetch_all_images(token: str, username: str, browsing_level: int = 31) -> tuple[list[dict], bool]:
    images, cursor, truncated = [], None, False
    while True:
        params: dict = {
            "username": username,
            "limit": 200,
            "sort": "Newest",
            "browsingLevel": browsing_level,
        }
        if cursor:
            params["cursor"] = cursor
        try:
            data = _get(token, "images", params)
        except Exception as e:
            print(f"  API error (stopping pagination): {e}")
            truncated = True
            break
        items = data.get("items", [])
        images.extend(items)
        cursor = data.get("metadata", {}).get("nextCursor")
        if not cursor or not items:
            break
    return images, truncated


def fetch_all(token: str, username: str, browsing_level: int = 31,
              force_refresh: bool = False) -> dict:
    if not force_refresh:
        cached = _load_cache(username, browsing_level)
        if cached:
            print(f"  Loaded from cache ({len(cached['images'])} images)")
            return cached

    print("  Profile…")
    profile = fetch_profile(token, username)

    print("  Images…")
    images, truncated = fetch_all_images(token, username, browsing_level)
    print(f"  {len(images)} images fetched{' (truncated)' if truncated else ''}")

    images_by_post: dict[int, list[dict]] = {}
    for img in images:
        pid = img.get("postId")
        if pid:
            images_by_post.setdefault(pid, []).append(img)

    result = {
        "profile":        profile,
        "images":         images,
        "images_by_post": images_by_post,
        "truncated":      truncated,
    }

    if not truncated:
        _save_cache(username, browsing_level, result)

    return result
