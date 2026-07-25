"""yt-dlp wrapper for TikTok extraction."""

import os
import re
from typing import Any

import yt_dlp


def is_video_url(url: str) -> bool:
    """Return True if the URL looks like a single TikTok video."""
    return bool(re.search(r"/video/\d+", url))


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
