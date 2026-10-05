"""API-level tests for app.main using FastAPI's TestClient.

Network access is never involved: yt-dlp, Playwright and the CDN HTTP client
are all monkeypatched.
"""

from pathlib import Path

import pytest

import app.main as main
from app import database
from app.download_manager import QUEUE_DIR

VIDEO_URL = "https://www.tiktok.com/@user/video/7123456789012345678"

YTDLP_INFO = {
    "id": "7123456789012345678",
    "uploader": "creator",
    "description": "d" * 600,
    "duration": 15,
    "thumbnail": "https://cdn/thumb.jpg",
    "formats": [
        {"format_id": "download", "vcodec": "h264", "height": 480},
        {"format_id": "h264_720p_x", "vcodec": "h264", "height": 720},
        {"format_id": "bytevc1_1080p_y-1", "vcodec": "bytevc1", "height": 1080},
    ],
}

PLAYWRIGHT_INFO = {
    "id": "7123456789012345678",
    "uploader": "creator",
    "description": "pw",
    "duration": 15,
    "thumbnail": "https://cdn/thumb.jpg",
    "_source": "playwright",
    "formats": [
        {"format_id": "play_addr", "url": "https://cdn/play.mp4"},
        {"format_id": "download_addr", "url": "https://cdn/download.mp4"},
    ],
}


@pytest.fixture()
def no_playwright(monkeypatch):
    async def boom(url, cookiefile=None):
        raise AssertionError("playwright must not be called")

    monkeypatch.setattr(main, "playwright_extract", boom)


def test_index_serves_spa(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "<div id=\"root\">" in resp.text


def test_resolve_rejects_non_video_url(client, no_playwright):
    resp = client.post("/resolve", json={"url": "https://www.tiktok.com/@user"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Not a valid TikTok video URL"


def test_favicon_is_served(client):
    resp = client.get("/favicon.svg")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/svg+xml")
    assert resp.text.lstrip().startswith("<svg")


def test_unknown_page_path_serves_app_shell_with_404(client):
    """Deep links must resolve so the app can render its own not-found view."""
    resp = client.get("/definitely-not-a-page")
    assert resp.status_code == 404
    assert '<div id="root">' in resp.text


def test_unknown_api_path_stays_json(client):
    resp = client.get("/queue/abc/extra")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["detail"] == "Not Found"


def test_resolve_uses_ytdlp_and_normalizes_format(client, monkeypatch, no_playwright):
    monkeypatch.setattr(main, "extract_info", lambda url, cookiefile=None: YTDLP_INFO)
    resp = client.post("/resolve", json={"url": VIDEO_URL})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "7123456789012345678"
    assert body["author"] == "creator"
    assert body["duration"] == 15
    assert len(body["caption"]) == 500
    assert body["format_id"] == "bytevc1_1080p_y-0"


def test_resolve_falls_back_to_playwright(client, monkeypatch):
    def fail(url, cookiefile=None):
        raise RuntimeError("IP is blocked")

    async def extract(url, cookiefile=None):
        return PLAYWRIGHT_INFO

    monkeypatch.setattr(main, "extract_info", fail)
    monkeypatch.setattr(main, "playwright_extract", extract)
    resp = client.post("/resolve", json={"url": VIDEO_URL})
    assert resp.status_code == 200
    # play_addr is the variant the CDN will actually serve to a server-side fetch
    assert resp.json()["format_id"] == "https://cdn/play.mp4"


def test_resolve_prefers_play_addr_over_download_addr(client, monkeypatch):
    def fail(url, cookiefile=None):
        raise RuntimeError("nope")

    async def extract(url, cookiefile=None):
        # download_addr listed FIRST — resolve must still pick play_addr
        return {
            **PLAYWRIGHT_INFO,
            "formats": [
                {"format_id": "download_addr", "url": "https://cdn/download.mp4"},
                {"format_id": "play_addr", "url": "https://cdn/play.mp4"},
            ],
        }

    monkeypatch.setattr(main, "extract_info", fail)
    monkeypatch.setattr(main, "playwright_extract", extract)
    resp = client.post("/resolve", json={"url": VIDEO_URL})
    assert resp.json()["format_id"] == "https://cdn/play.mp4"


def test_resolve_falls_back_to_download_addr_without_play_addr(client, monkeypatch):
    def fail(url, cookiefile=None):
        raise RuntimeError("nope")

    async def extract(url, cookiefile=None):
        return {
            **PLAYWRIGHT_INFO,
            "formats": [{"format_id": "download_addr", "url": "https://cdn/download.mp4"}],
        }

    monkeypatch.setattr(main, "extract_info", fail)
    monkeypatch.setattr(main, "playwright_extract", extract)
    resp = client.post("/resolve", json={"url": VIDEO_URL})
    assert resp.json()["format_id"] == "https://cdn/download.mp4"


def test_resolve_playwright_falls_back_to_play_addr(client, monkeypatch):
    def fail(url, cookiefile=None):
        raise RuntimeError("nope")

    async def extract(url, cookiefile=None):
        return {**PLAYWRIGHT_INFO, "formats": [{"format_id": "play_addr", "url": "https://cdn/play.mp4"}]}

    monkeypatch.setattr(main, "extract_info", fail)
    monkeypatch.setattr(main, "playwright_extract", extract)
    resp = client.post("/resolve", json={"url": VIDEO_URL})
    assert resp.json()["format_id"] == "https://cdn/play.mp4"


def test_resolve_returns_502_when_all_extractors_fail(client, monkeypatch):
    def fail(url, cookiefile=None):
        raise RuntimeError("blocked")

    async def fail_pw(url, cookiefile=None):
        raise ValueError("browser blocked")

    monkeypatch.setattr(main, "extract_info", fail)
    monkeypatch.setattr(main, "playwright_extract", fail_pw)
    resp = client.post("/resolve", json={"url": VIDEO_URL})
    assert resp.status_code == 502
    assert "Extraction failed" in resp.json()["detail"]


def test_auth_status_defaults_to_false(client):
    assert client.get("/auth/status").json() == {"authenticated": False}


def test_auth_cookies_rejects_empty(client):
    assert client.post("/auth/cookies", json={"cookies": "   "}).status_code == 400


def test_auth_cookies_rejects_non_netscape_text(client):
    resp = client.post("/auth/cookies", json={"cookies": "just some pasted text"})
    assert resp.status_code == 400
    assert "Netscape" in resp.json()["detail"]


def test_auth_cookies_roundtrip(client):
    netscape = "# Netscape HTTP Cookie File\n.tiktok.com\tTRUE\t/\tTRUE\t0\tsessionid\tsecret\n"
    resp = client.post("/auth/cookies", json={"cookies": netscape})
    assert resp.status_code == 200
    assert resp.json() == {"authenticated": True}
    assert client.get("/auth/status").json() == {"authenticated": True}

    assert client.delete("/auth/cookies").json() == {"authenticated": False}
    assert client.get("/auth/status").json() == {"authenticated": False}


def test_queue_rejects_invalid_url(client):
    resp = client.post("/queue", json={"url": "https://example.com/nope", "format_id": ""})
    assert resp.status_code == 400


def test_queue_add_list_get_delete(client):
    created = client.post("/queue", json={"url": VIDEO_URL, "format_id": "h264_720p_x"})
    assert created.status_code == 200
    item_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    listed = client.get("/queue").json()["items"]
    assert [i["id"] for i in listed] == [item_id]

    fetched = client.get(f"/queue/{item_id}")
    assert fetched.status_code == 200
    assert fetched.json()["format_id"] == "h264_720p_x"

    assert client.get("/queue/missing").status_code == 404
    assert client.delete("/queue/missing").status_code == 404
    assert client.delete(f"/queue/{item_id}").json() == {"ok": True}
    assert client.get("/queue").json()["items"] == []


def test_queue_clear(client):
    client.post("/queue", json={"url": VIDEO_URL})
    client.post("/queue", json={"url": VIDEO_URL})
    resp = client.delete("/queue")
    assert resp.json() == {"ok": True, "cleared": 2}


def test_queue_file_missing_item(client):
    assert client.get("/queue/missing/file").status_code == 404


def test_queue_file_not_ready(client):
    item_id = client.post("/queue", json={"url": VIDEO_URL}).json()["id"]
    resp = client.get(f"/queue/{item_id}/file")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "File not ready"


def test_queue_file_completed(client):
    item_id = client.post("/queue", json={"url": VIDEO_URL}).json()["id"]
    path = Path(QUEUE_DIR) / f"{item_id}.mp4"
    path.write_bytes(b"VIDEO-BYTES")
    database.update_item(item_id, status="completed", file_path=str(path))

    resp = client.get(f"/queue/{item_id}/file")
    assert resp.status_code == 200
    assert resp.content == b"VIDEO-BYTES"
    assert resp.headers["content-disposition"] == f'attachment; filename="{item_id}.mp4"'
    path.unlink()


def test_queue_file_deleted_from_disk(client):
    item_id = client.post("/queue", json={"url": VIDEO_URL}).json()["id"]
    path = Path(QUEUE_DIR) / f"{item_id}.mp4"
    path.write_bytes(b"x")
    database.update_item(item_id, status="completed", file_path=str(path))
    path.unlink()

    assert client.get(f"/queue/{item_id}/file").status_code == 404


def test_queue_file_refuses_paths_outside_the_queue_dir(client, tmp_path):
    """A stored path must not be able to serve an arbitrary file."""
    item_id = client.post("/queue", json={"url": VIDEO_URL}).json()["id"]
    outside = tmp_path / "secret.txt"
    outside.write_bytes(b"SECRET")
    database.update_item(item_id, status="completed", file_path=str(outside))

    assert client.get(f"/queue/{item_id}/file").status_code == 404


def test_download_rejects_unrecognized_request(client):
    resp = client.get("/download", params={"url": "https://example.com", "format_id": "h264"})
    assert resp.status_code == 400


def test_download_direct_url_sends_session_cookies(client, monkeypatch):
    """The CDN signs media URLs to the browser session that minted them; a
    cookie-less fetch gets 403. This is the regression guard for that bug."""
    captured = {}

    class FakeResponse:
        def iter_content(self, size):
            return iter([b"MP4", b"DATA"])

        def raise_for_status(self):
            pass

    def fake_cdn_get(src, cookies=None, stream=False):
        captured.update(src=src, cookies=cookies, stream=stream)
        return FakeResponse()

    monkeypatch.setattr(main, "check_outbound_url", lambda target: target)
    monkeypatch.setattr(main, "cdn_get", fake_cdn_get)
    monkeypatch.setattr(main, "get_session_cookies", lambda: {"tt_chain_token": "tok"})

    media = "https://v16-webapp-prime.tiktok.com/video.mp4"
    resp = client.get("/download", params={"url": VIDEO_URL, "format_id": media})
    assert resp.status_code == 200
    assert resp.content == b"MP4DATA"
    assert resp.headers["content-disposition"] == 'attachment; filename="tiktok_video.mp4"'
    assert captured["src"] == media
    assert captured["cookies"] == {"tt_chain_token": "tok"}
    assert captured["stream"] is True


# ── Outbound target validation ──────────────────────────────────────────────
# Every outbound URL arrives as a request parameter, so the endpoints must not
# be usable as general-purpose fetchers.


def test_download_rejects_internal_target(client):
    resp = client.get(
        "/download",
        params={"url": VIDEO_URL, "format_id": "http://127.0.0.1:8080/auth/status"},
    )
    assert resp.status_code == 400
    assert "Blocked target" in resp.json()["detail"]


def test_download_rejects_metadata_service_target(client):
    resp = client.get(
        "/download",
        params={"url": VIDEO_URL, "format_id": "http://169.254.169.254/latest/meta-data/"},
    )
    assert resp.status_code == 400


def test_download_rejects_non_tiktok_page_url(client):
    resp = client.get(
        "/download", params={"url": "https://example.com/video/1", "format_id": "h264"}
    )
    assert resp.status_code == 400


def test_queue_rejects_internal_media_url(client):
    resp = client.post(
        "/queue",
        json={"url": VIDEO_URL, "format_id": "http://127.0.0.1:8080/auth/status"},
    )
    assert resp.status_code == 400
    assert "Blocked target" in resp.json()["detail"]


def test_resolve_rejects_non_tiktok_host(client, no_playwright):
    resp = client.post("/resolve", json={"url": "https://example.com/video/123"})
    assert resp.status_code == 400


def test_auth_cookies_rejects_oversized_payload(client):
    resp = client.post("/auth/cookies", json={"cookies": "x" * (256 * 1024 + 1)})
    assert resp.status_code == 422
