"""Persistent download queue with background worker."""

import os
import threading
import uuid
from pathlib import Path

import yt_dlp
from curl_cffi import requests as cffi_requests

from app.cookies import load_cookies
from app.database import (
    claim_pending,
    clear_items as db_clear,
    get_item as db_get_item,
    insert_item,
    list_items as db_list_items,
    remove_item as db_remove,
    reset_stale_downloading,
    update_item,
)

QUEUE_DIR = Path("/tmp/tiktok_queue")
QUEUE_DIR.mkdir(parents=True, exist_ok=True)


def enqueue(url: str, format_id: str, title: str = "") -> dict:
    item = {
        "id": uuid.uuid4().hex[:12],
        "url": url,
        "format_id": format_id or "",
        "title": title or "",
        "status": "pending",
        "video_id": "",
        "file_path": None,
        "error": None,
        "retry_count": 0,
    }
    return insert_item(item)


def list_items() -> list[dict]:
    return db_list_items()


def get_item(item_id: str) -> dict | None:
    return db_get_item(item_id)


def remove_item(item_id: str) -> bool:
    return db_remove(item_id)


def clear_queue() -> int:
    return db_clear()


def _worker():
    while True:
        item = claim_pending()
        if item is None:
            threading.Event().wait(1)
            continue

        item_id = item["id"]
        url = item["url"]
        fmt = item["format_id"]
        dest = str(QUEUE_DIR / f"{item_id}.mp4")

        opts = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": dest,
        }
        if fmt:
            opts["format"] = fmt
        cookiefile = load_cookies()
        if cookiefile:
            opts["cookiefile"] = cookiefile

        try:
            if fmt.startswith("http"):
                resp = cffi_requests.get(fmt, impersonate="chrome")
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    f.write(resp.content)
                info = {"id": item_id}
            else:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
            update_item(item_id, status="completed", video_id=info.get("id", ""), file_path=dest)
        except Exception as e:
            update_item(item_id, status="failed", error=str(e))


reset_stale_downloading()
_thread = threading.Thread(target=_worker, daemon=True)
_thread.start()
