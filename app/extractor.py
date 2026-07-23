"""yt-dlp wrapper for TikTok extraction."""

import re
from typing import Any

import yt_dlp


def is_video_url(url: str) -> bool:
    """Return True if the URL looks like a single TikTok video."""
    return bool(re.search(r"/video/\d+", url))


def is_profile_url(url: str) -> bool:
    """Return True if the URL looks like a TikTok profile."""
    return bool(re.search(r"tiktok\.com/@[\w.]+", url)) and not is_video_url(url)


def extract_info(url: str) -> dict[str, Any]:
    """Extract full video metadata and formats via yt-dlp.

    Returns the raw yt-dlp info dict. Raises ExtractError on failure.
    Note: no custom http_headers — they interfere with curl_cffi impersonation.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def resolve_video(url: str) -> dict[str, Any]:
    """Resolve a TikTok video URL into a clean metadata + format response.

    Returns a dict suitable for the /resolve API:
        {
            "id": str,
            "thumbnail": str,
            "author": str,
            "caption": str,
            "duration": int,
            "formats": { "sd": {...}, "hd": {...} }
        }
    """
    if not is_video_url(url):
        if is_profile_url(url):
            raise ValueError("Profile URLs are not supported yet (Phase 3)")
        raise ValueError("Not a valid TikTok video URL")

    info = extract_info(url)

    # Extract the first non-empty description (yt-dlp puts it in title or description)
    caption = info.get("description") or info.get("title") or ""

    return {
        "id": info.get("id", ""),
        "thumbnail": info.get("thumbnail", ""),
        "author": info.get("uploader", info.get("channel", "")),
        "caption": caption[:500],  # trim long captions
        "duration": info.get("duration", 0),
    }
