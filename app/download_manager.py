"""Persistent download queue with background worker."""

import os
import threading
import uuid
from pathlib import Path

import yt_dlp

from app.cookies import load_cookies
from app.net import BlockedTarget, cdn_get, check_outbound_url, pace_outbound, stream_to_file
from app.playwright_extractor import get_session_cookies
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

# Set on enqueue so the worker starts a job immediately instead of waiting out
# its poll interval.
_wake = threading.Event()


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
    stored = insert_item(item)
    _wake.set()
    return stored


def list_items() -> list[dict]:
    return db_list_items()


def get_item(item_id: str) -> dict | None:
    return db_get_item(item_id)


def remove_item(item_id: str) -> bool:
    return db_remove(item_id)


def clear_queue() -> int:
    return db_clear()


def process_item(item: dict) -> None:
    """Run one queue item to completion, recording the outcome in the DB."""
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
            # Second layer of the same check /queue applies: never fetch a
            # caller-supplied URL that is not TikTok media.
            check_outbound_url(fmt)
            resp = cdn_get(fmt, cookies=get_session_cookies(), stream=True)
            resp.raise_for_status()
            stream_to_file(resp, dest)
            info = {"id": item_id}
        else:
            pace_outbound()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        update_item(item_id, status="completed", video_id=info.get("id", ""), file_path=dest)
    except Exception as e:
        update_item(item_id, status="failed", error=str(e))


def _worker():
    while True:
        item = claim_pending()
        if item is None:
            _wake.wait(timeout=1.0)
            _wake.clear()
            continue
        process_item(item)


reset_stale_downloading()
_thread = threading.Thread(target=_worker, daemon=True)
_thread.start()
