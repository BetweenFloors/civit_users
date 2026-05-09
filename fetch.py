"""Fetch user data from Civitai official REST API only."""

from __future__ import annotations
import requests

_API = "https://civitai.com/api/v1"


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


def fetch_all_images(token: str, username: str, browsing_level: int = 31) -> list[dict]:
    images, cursor = [], None
    while True:
        params: dict = {
            "username": username,
            "limit": 200,
            "sort": "Newest",
            "browsingLevel": browsing_level,
        }
        if cursor:
            params["cursor"] = cursor
        data = _get(token, "images", params)
        items = data.get("items", [])
        images.extend(items)
        cursor = data.get("metadata", {}).get("nextCursor")
        if not cursor or not items:
            break
    return images


def fetch_all(token: str, username: str, browsing_level: int = 31) -> dict:
    print("  Profile…")
    profile = fetch_profile(token, username)

    print("  Images…")
    images = fetch_all_images(token, username, browsing_level)
    print(f"  {len(images)} images fetched")

    # Group by postId and collect unique posts
    images_by_post: dict[int, list[dict]] = {}
    for img in images:
        pid = img.get("postId")
        if pid:
            images_by_post.setdefault(pid, []).append(img)

    return {
        "profile":       profile,
        "images":        images,
        "images_by_post": images_by_post,
    }
