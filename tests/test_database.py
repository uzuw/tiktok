"""Tests for the SQLite queue store (DB path redirected to a temp file)."""

import sqlite3
import time

import pytest

from app import database


def make_item(item_id="a1", **overrides):
    item = {
        "id": item_id,
        "url": "https://www.tiktok.com/@u/video/1",
        "format_id": "h264_720p",
        "title": "",
        "status": "pending",
        "video_id": "",
        "file_path": None,
        "error": None,
        "retry_count": 0,
    }
    item.update(overrides)
    return item


def test_insert_and_get_roundtrip():
    inserted = database.insert_item(make_item())
    assert isinstance(inserted["created_at"], float)
    assert isinstance(inserted["updated_at"], float)

    stored = database.get_item("a1")
    assert stored["url"] == "https://www.tiktok.com/@u/video/1"
    assert stored["status"] == "pending"
    assert stored["file_path"] is None


def test_get_missing_returns_none():
    assert database.get_item("nope") is None


def test_update_item_sets_fields_and_timestamp():
    database.insert_item(make_item())
    database.update_item("a1", status="completed", file_path="/tmp/x.mp4")
    stored = database.get_item("a1")
    assert stored["status"] == "completed"
    assert stored["file_path"] == "/tmp/x.mp4"
    assert stored["updated_at"] >= stored["created_at"]


def test_update_item_rejects_invalid_status():
    database.insert_item(make_item())
    with pytest.raises(sqlite3.IntegrityError):
        database.update_item("a1", status="bogus")


def test_list_items_is_ordered_by_creation():
    database.insert_item(make_item("first"))
    time.sleep(0.001)
    database.insert_item(make_item("second"))
    assert [i["id"] for i in database.list_items()] == ["first", "second"]


def test_claim_pending_takes_oldest_and_marks_downloading():
    database.insert_item(make_item("first"))
    time.sleep(0.001)
    database.insert_item(make_item("second"))

    claimed = database.claim_pending()
    assert claimed["id"] == "first"
    assert claimed["status"] == "downloading"
    assert database.pending_count() == 1

    assert database.claim_pending()["id"] == "second"
    assert database.claim_pending() is None


def test_claim_pending_skips_completed_items():
    database.insert_item(make_item())
    database.update_item("a1", status="completed")
    assert database.claim_pending() is None


def test_remove_item_reports_hit_or_miss():
    database.insert_item(make_item())
    assert database.remove_item("a1") is True
    assert database.remove_item("a1") is False


def test_clear_items_returns_count():
    database.insert_item(make_item("a"))
    database.insert_item(make_item("b"))
    assert database.clear_items() == 2
    assert database.list_items() == []


def test_reset_stale_downloading():
    database.insert_item(make_item("stuck", status="downloading"))
    database.insert_item(make_item("fresh"))
    database.reset_stale_downloading()
    assert database.get_item("stuck")["status"] == "pending"
    assert database.pending_count() == 2
