"""Tests for the pure helpers in app.playwright_extractor.

These do not launch a browser: only the universal-data parser, the netscape
cookie parser and the item -> result mapper are exercised.
"""

import asyncio

import app.playwright_extractor as playwright_extractor
from app.playwright_extractor import (
    _build_result,
    _find_video_data,
    _parse_netscape_cookies,
)


class _CtxWith:
    """Minimal browser-context stand-in returning a fixed cookie jar."""

    def __init__(self, jar):
        self._jar = jar

    async def cookies(self):
        return [{"name": k, "value": v} for k, v in self._jar.items()]

ITEM = {"id": "123", "desc": "hello"}


def test_find_video_data_flat_dotted_key():
    data = {
        "__DEFAULT_SCOPE__": {
            "webapp.video-detail": {
                "statusCode": 0,
                "itemInfo": {"itemStruct": ITEM},
            }
        }
    }
    assert _find_video_data(data) == ITEM


def test_find_video_data_nested_path():
    data = {
        "__DEFAULT_SCOPE__": {
            "webapp": {"video-detail": {"statusCode": 0, "itemInfo": {"item": ITEM}}}
        }
    }
    assert _find_video_data(data) == ITEM


def test_find_video_data_nonzero_status_ignored():
    data = {
        "__DEFAULT_SCOPE__": {
            "webapp.video-detail": {
                "statusCode": 10216,
                "itemInfo": {"itemStruct": ITEM},
            }
        }
    }
    assert _find_video_data(data) is None


def test_find_video_data_feed_item_list():
    data = {"__DEFAULT_SCOPE__": {"webapp.video-feed": {"itemList": [ITEM, {"id": "2"}]}}}
    assert _find_video_data(data) == ITEM


def test_find_video_data_scopeless_payload():
    assert _find_video_data({"webapp.search": {"items": [ITEM]}}) == ITEM


def test_find_video_data_absent():
    assert _find_video_data({"__DEFAULT_SCOPE__": {}}) is None


def test_parse_netscape_cookies():
    text = "\n".join(
        [
            "# Netscape HTTP Cookie File",
            "",
            ".tiktok.com\tTRUE\t/\tTRUE\t0\tsessionid\tsecret",
            "#HttpOnly_.tiktok.com\tTRUE\t/\tFALSE\t0\tmsToken\tabc",
        ]
    )
    cookies = _parse_netscape_cookies(text)
    assert cookies == [
        {
            "name": "sessionid",
            "value": "secret",
            "domain": ".tiktok.com",
            "path": "/",
            "secure": True,
            "httpOnly": False,
            "sameSite": "Lax",
        }
    ]


def test_parse_netscape_cookies_skips_malformed_lines():
    assert _parse_netscape_cookies("a\tb\tc") == []


def test_build_result_maps_fields_and_formats():
    item = {
        "id": 42,
        "desc": "d" * 600,
        "author": {"uniqueId": "creator", "id": 7},
        "video": {
            "playAddr": "https://cdn/play.mp4",
            "downloadAddr": "https://cdn/download.mp4",
            "cover": "https://cdn/cover.jpg",
            "duration": 12.9,
            "height": 1080,
            "width": 1920,
        },
    }
    result = _build_result(item)
    assert result["id"] == "42"
    assert result["title"] == "d" * 500
    assert result["thumbnail"] == "https://cdn/cover.jpg"
    assert result["duration"] == 12
    assert result["uploader"] == "creator"
    assert result["uploader_id"] == "7"
    assert result["_source"] == "playwright"
    assert [f["format_id"] for f in result["formats"]] == ["play_addr", "download_addr"]


def test_build_result_dedupes_identical_play_and_download_url():
    item = {"id": "1", "video": {"playAddr": "https://cdn/same.mp4", "downloadAddr": "https://cdn/same.mp4"}}
    result = _build_result(item)
    assert [f["format_id"] for f in result["formats"]] == ["play_addr"]


def test_build_result_handles_missing_video_block():
    result = _build_result({"id": "1"})
    assert result["formats"] == []
    assert result["title"] == ""
    assert result["duration"] == 0


# ── Session cookie harvest ──────────────────────────────────────────────────
# The browser context holds the cookies TikTok's CDN requires; they have to be
# carried over to the server-side download or it gets 403.


def test_harvest_cookies_populates_session_jar():
    class FakeContext:
        async def cookies(self):
            return [
                {"name": "tt_chain_token", "value": "abc"},
                {"name": "msToken", "value": "m1"},
            ]

    asyncio.run(playwright_extractor._harvest_cookies(FakeContext()))
    assert playwright_extractor.get_session_cookies() == {
        "tt_chain_token": "abc",
        "msToken": "m1",
    }


def test_get_session_cookies_returns_a_copy():
    asyncio.run(playwright_extractor._harvest_cookies(_CtxWith({"a": "1"})))
    jar = playwright_extractor.get_session_cookies()
    jar["injected"] = "x"
    assert "injected" not in playwright_extractor.get_session_cookies()


def test_harvest_cookies_ignores_broken_context():
    class BrokenContext:
        async def cookies(self):
            raise RuntimeError("browser gone")

    asyncio.run(playwright_extractor._harvest_cookies(_CtxWith({"keep": "v"})))
    asyncio.run(playwright_extractor._harvest_cookies(BrokenContext()))
    assert playwright_extractor.get_session_cookies() == {"keep": "v"}
