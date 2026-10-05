"""Tests for the download queue facade in app.download_manager."""

import os

from app import database, download_manager


def test_enqueue_creates_pending_item():
    item = download_manager.enqueue("https://www.tiktok.com/@u/video/123", "h264_720p", "title")
    assert len(item["id"]) == 12
    assert item["status"] == "pending"
    assert item["format_id"] == "h264_720p"

    stored = download_manager.get_item(item["id"])
    assert stored["title"] == "title"
    assert stored["retry_count"] == 0


def test_enqueue_defaults_empty_format_and_title():
    item = download_manager.enqueue("https://www.tiktok.com/@u/video/123", None)
    assert item["format_id"] == ""
    assert item["title"] == ""


def test_list_get_remove_and_clear():
    first = download_manager.enqueue("https://www.tiktok.com/@u/video/1", "")
    second = download_manager.enqueue("https://www.tiktok.com/@u/video/2", "")

    assert [i["id"] for i in download_manager.list_items()] == [first["id"], second["id"]]
    assert download_manager.remove_item(first["id"]) is True
    assert download_manager.get_item(first["id"]) is None

    assert download_manager.clear_queue() == 1
    assert database.list_items() == []


# ── Direct-URL downloads ────────────────────────────────────────────────────
# TikTok signs media URLs to the browser session that minted them; fetching one
# without that session's cookies returns 403 from TikTok's edge. These guard the
# plumbing that was missing when direct downloads and the queue both failed.

CDN_URL = "https://v16-webapp-prime.tiktok.com/video.mp4"


def _install_fake_cdn(monkeypatch, chunks=(b"MP4BYTES",), error=None):
    """Fake the CDN client. stream_to_file stays real, so the file really lands."""
    captured = {}

    class FakeResponse:
        def iter_content(self, size):
            return iter(chunks)

        def raise_for_status(self):
            if error is not None:
                raise error

    def fake_cdn_get(src, cookies=None, stream=False):
        captured.update(src=src, cookies=cookies, stream=stream)
        return FakeResponse()

    monkeypatch.setattr(download_manager, "check_outbound_url", lambda target: target)
    monkeypatch.setattr(download_manager, "cdn_get", fake_cdn_get)
    return captured


def test_process_item_sends_session_cookies_and_writes_file(monkeypatch):
    captured = _install_fake_cdn(monkeypatch)
    monkeypatch.setattr(download_manager, "get_session_cookies", lambda: {"tt_chain_token": "tok"})

    item = download_manager.enqueue("https://www.tiktok.com/@u/video/1", CDN_URL)
    download_manager.process_item(download_manager.get_item(item["id"]))

    row = download_manager.get_item(item["id"])
    assert row["status"] == "completed"
    assert row["error"] is None
    assert captured["src"] == CDN_URL
    assert captured["cookies"] == {"tt_chain_token": "tok"}
    assert captured["stream"] is True

    with open(row["file_path"], "rb") as handle:
        assert handle.read() == b"MP4BYTES"
    os.unlink(row["file_path"])


def test_process_item_records_cdn_error(monkeypatch):
    error = RuntimeError("HTTP Error 403: Forbidden")
    _install_fake_cdn(monkeypatch, error=error)

    item = download_manager.enqueue("https://www.tiktok.com/@u/video/1", CDN_URL)
    download_manager.process_item(download_manager.get_item(item["id"]))

    row = download_manager.get_item(item["id"])
    assert row["status"] == "failed"
    assert "403" in row["error"]


def test_process_item_ytdlp_path_uses_url_and_format(monkeypatch):
    """Non-http format ids go through yt-dlp, with the chosen format passed on."""
    captured = {}

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts
            captured["opts"] = opts

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download=False):
            captured["url"] = url
            captured["download"] = download
            with open(self.opts["outtmpl"], "wb") as handle:
                handle.write(b"BYTES")
            return {"id": "vid123"}

    monkeypatch.setattr(download_manager.yt_dlp, "YoutubeDL", FakeYDL)

    item = download_manager.enqueue("https://www.tiktok.com/@u/video/1", "h264_720p_x-0")
    download_manager.process_item(download_manager.get_item(item["id"]))

    row = download_manager.get_item(item["id"])
    assert row["status"] == "completed"
    assert row["video_id"] == "vid123"
    assert captured["url"] == "https://www.tiktok.com/@u/video/1"
    assert captured["download"] is True
    assert captured["opts"]["format"] == "h264_720p_x-0"
    os.unlink(row["file_path"])
