"""yt-dlp wrapper for TikTok extraction."""

import os
import re
from typing import Any

import yt_dlp


def is_video_url(url: str) -> bool:
    """Return True if the URL looks like a single TikTok video."""
    return bool(re.search(r"/video/\d+", url))


def is_profile_url(url: str) -> bool:
    """Return True if the URL looks like a TikTok profile."""
    return bool(re.search(r"tiktok\.com/@[\w.]+", url)) and not is_video_url(url)


def extract_info(url: str, cookiefile: str | None = None) -> dict[str, Any]:
    """Extract full video metadata and formats via yt-dlp.

    Returns the raw yt-dlp info dict. Raises ExtractError on failure.
    Note: no custom http_headers — they interfere with curl_cffi impersonation.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
    }
    if cookiefile and os.path.exists(cookiefile):
        opts["cookiefile"] = cookiefile
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def extract_profile(url: str, cookiefile: str | None = None, max_entries: int = 30) -> dict[str, Any]:
    """Extract video list from a TikTok profile (playlist) via yt-dlp."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": max_entries,
    }
    if cookiefile and os.path.exists(cookiefile):
        opts["cookiefile"] = cookiefile
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = []
    for e in (info.get("entries") or []):
        thumb = ""
        thumbs = e.get("thumbnails") or []
        if thumbs:
            thumb = thumbs[0].get("url", "")
        entries.append({
            "id": e.get("id", ""),
            "url": e.get("url", ""),
            "title": (e.get("title") or "")[:200],
            "duration": e.get("duration") or 0,
            "thumbnail": thumb,
        })
    return {
        "type": "profile",
        "author": info.get("title") or info.get("uploader", ""),
        "total": info.get("playlist_count", len(entries)),
        "entries": entries,
    }
