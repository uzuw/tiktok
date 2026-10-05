"""yt-dlp wrapper for TikTok extraction."""

import os
import re
from typing import Any
from urllib.parse import urlparse

import yt_dlp

from app.net import pace_outbound

# Only TikTok hosts are handed to the extractor. Without the host check any
# site's /video/123 path would pass, and the extractor fetches server-side.
_TIKTOK_HOST_RE = re.compile(r"^(?:[a-z0-9-]+\.)*tiktok\.com$", re.IGNORECASE)


def is_video_url(url: str) -> bool:
    """Return True if the URL is a single-video page on a TikTok host."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if not _TIKTOK_HOST_RE.match(parsed.hostname or ""):
        return False
    return bool(re.search(r"/video/\d+", parsed.path))


def extract_info(url: str, cookiefile: str | None = None) -> dict[str, Any]:
    """Extract full video metadata and formats via yt-dlp.

    Returns the raw yt-dlp info dict. Raises on failure.
    Note: no custom http_headers — they interfere with curl_cffi impersonation.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
    }
    if cookiefile and os.path.exists(cookiefile):
        opts["cookiefile"] = cookiefile
    pace_outbound()
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)
