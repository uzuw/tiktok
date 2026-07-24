"""Playwright-based TikTok extractor — fallback when yt-dlp is blocked."""

import json
import os
import re
import asyncio
from typing import Any

from playwright.async_api import async_playwright, Browser, Page

_browser: Browser | None = None
_playwright = None
_lock = asyncio.Lock()


def _find_video_data(data: dict) -> dict | None:
    """Dig through the universal data blob to find the video item.

    Handles both the single-video page and the API-response-in-page
    layouts TikTok serves.
    """
    scope = data.get("__DEFAULT_SCOPE__") or data

    # Try dotted-key path first (flat format: "webapp.video-detail")
    detail = scope.get("webapp.video-detail") or {}
    if detail and detail.get("statusCode") == 0:
        item = detail.get("itemInfo", {}).get("itemStruct") or detail.get("itemInfo", {}).get("item")
        if item:
            return item

    # Try nested path too
    if not detail:
        detail = scope.get("webapp", {}).get("video-detail", {})
        if detail.get("statusCode") == 0:
            item = detail.get("itemInfo", {}).get("itemStruct") or detail.get("itemInfo", {}).get("item")
            if item:
                return item

    # ForYou / search-page path — try dotted keys
    for flat_key in ("webapp.video-feed", "webapp.search", "webapp.user-posts"):
        feed = scope.get(flat_key) or {}
        items = feed.get("itemList") or feed.get("items") or []
        if items and isinstance(items, list):
            return items[0]
    return None


async def get_browser() -> Browser:
    """Return the singleton Playwright browser instance, launching it if needed."""
    global _browser, _playwright
    async with _lock:
        if _browser and _browser.is_connected():
            return _browser
        # Clean up any stale instance
        if _playwright:
            try:
                await _playwright.stop()
            except Exception:
                pass
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
    return _browser


async def _try_api_fetch(page: "Page", url: str) -> dict | None:
    """Try TikTok's internal API endpoint as fallback for video data."""
    video_id_match = re.search(r"/video/(\d+)", url)
    if not video_id_match:
        return None
    vid = video_id_match.group(1)
    api_url = (
        f"https://www.tiktok.com/api/item/detail/?itemId={vid}&"
        f"aid=1988&app_language=en&app_name=tiktok_web"
    )
    try:
        resp = await page.evaluate(
            f"fetch('{api_url}').then(r => r.text()).then(t => {{ try {{ return JSON.parse(t) }} catch(e) {{ return null }} }})"
        )
        if resp and resp.get("statusCode") == 0:
            item_info = resp.get("itemInfo") or {}
            return item_info.get("itemStruct") or item_info.get("item")
    except Exception:
        pass
    return None


def _parse_netscape_cookies(text: str) -> list[dict]:
    cookies = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) >= 7:
            cookies.append({
                "name": fields[5],
                "value": fields[6],
                "domain": fields[0],
                "path": fields[2],
                "secure": fields[3].lower() == "true",
                "httpOnly": False,
                "sameSite": "Lax",
            })
    return cookies


async def playwright_extract(url: str, cookies_file: str | None = None) -> dict[str, Any]:
    """Extract TikTok video metadata using Playwright (headless Chromium).

    Returns a dict structured like yt-dlp output:
      { "id", "title", "description", "thumbnail", "duration",
        "uploader", "formats": [{ "format_id", "url", "ext", ... }] }

    Raises ValueError on failure.
    """
    browser = await get_browser()
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )

    if cookies_file and os.path.exists(cookies_file):
        with open(cookies_file) as f:
            raw = f.read()
        pw_cookies = _parse_netscape_cookies(raw)
        if pw_cookies:
            await context.add_cookies(pw_cookies)
    page = await context.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait for either universal data or a timeout
        try:
            await page.wait_for_function(
                "() => document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__')",
                timeout=10000,
            )
        except Exception:
            item = await _try_api_fetch(page, url)
            if item:
                return _build_result(item)
            raise ValueError("Video data not found on page")

        # Extract universal data
        universal_raw = await page.evaluate(
            "() => document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__').textContent"
        )
        universal_data = json.loads(universal_raw)
        item = _find_video_data(universal_data)
        if not item:
            # Page data was unavailable (statusCode != 0) — try API directly
            item = await _try_api_fetch(page, url)

        if not item:
            raise ValueError("Could not locate video item in universal data")

        return _build_result(item)

    finally:
        await page.close()
        await context.close()


def _build_result(item: dict) -> dict[str, Any]:
    """Turn a TikTok item struct into the yt-dlp-style output dict."""
    vid = item.get("id", "")
    author = item.get("author", {}) or {}
    music = item.get("music", {}) or {}
    stats = item.get("stats", {}) or {}
    video = item.get("video", {}) or {}

    play_url = (
        video.get("playAddr", "")
        or video.get("playUrl", "")
        or ""
    )
    download_url = (
        video.get("downloadAddr", "")
        or video.get("downloadUrl", "")
        or ""
    )

    # Build a simplified format list with direct URLs
    formats = []
    if play_url:
        formats.append({
            "format_id": "play_addr",
            "url": play_url,
            "ext": "mp4",
            "vcodec": "h264",
            "height": video.get("height", 0),
            "width": video.get("width", 0),
            "filesize": None,
            "format_note": "Playback stream",
        })
    if download_url and download_url != play_url:
        formats.append({
            "format_id": "download_addr",
            "url": download_url,
            "ext": "mp4",
            "vcodec": "h264",
            "height": video.get("height", 0),
            "width": video.get("width", 0),
            "filesize": None,
            "format_note": "Download stream",
        })

    return {
        "id": str(vid),
        "title": item.get("desc", "")[:500],
        "description": item.get("desc", ""),
        "thumbnail": (video.get("cover", "") or video.get("dynamicCover", "") or ""),
        "duration": int(video.get("duration", 0)),
        "uploader": author.get("uniqueId", "") or author.get("nickname", ""),
        "uploader_id": str(author.get("id", "")),
        "formats": formats,
        "_source": "playwright",
    }
