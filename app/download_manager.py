"""In-memory download queue with background worker."""

import os
import threading
import uuid
from pathlib import Path

import yt_dlp

from app.cookies import load_cookies

QUEUE_DIR = Path("/tmp/tiktok_queue")
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
_items: list[dict] = []  # newest last
_next_id = 0


def _worker():
    while True:
        item = None
        with _lock:
            for i in _items:
                if i["status"] == "pending":
                    i["status"] = "downloading"
                    item = i
                    break
        if item is None:
            threading.Event().wait(1)
            continue

        url = item["url"]
        fmt = item["format_id"]
        dest = str(QUEUE_DIR / f"{item['id']}.mp4")

        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": fmt,
            "outtmpl": dest,
        }
        cookiefile = load_cookies()
        if cookiefile:
            opts["cookiefile"] = cookiefile

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            with _lock:
                item["status"] = "completed"
                item["video_id"] = info.get("id", "")
                item["file"] = dest
        except Exception as e:
            with _lock:
                item["status"] = "failed"
                item["error"] = str(e)


_thread = threading.Thread(target=_worker, daemon=True)
_thread.start()


def enqueue(url: str, format_id: str, title: str = "") -> dict:
    global _next_id
    with _lock:
        item = {
            "id": str(_next_id),
            "url": url,
            "format_id": format_id,
            "title": title,
            "status": "pending",
            "video_id": "",
            "file": None,
            "error": None,
        }
        _items.append(item)
        _next_id += 1
    return item


def list_items() -> list[dict]:
    with _lock:
        return list(_items)


def get_item(item_id: str) -> dict | None:
    with _lock:
        for i in _items:
            if i["id"] == item_id:
                return dict(i)
    return None


def remove_item(item_id: str) -> bool:
    with _lock:
        for i, item in enumerate(_items):
            if item["id"] == item_id:
                if item["status"] in ("pending",):
                    _items.pop(i)
                    return True
    return False
