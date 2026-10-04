"""Tests for app.cookies (paths redirected to a temp dir by conftest)."""

import os

import app.cookies as cookies
from app.cookies import clear_cookies, has_cookies, load_cookies, save_cookies


def test_no_cookies_by_default():
    assert load_cookies() is None
    assert has_cookies() is False


def test_save_then_load_roundtrip():
    save_cookies(".tiktok.com\tTRUE\t/\tTRUE\t0\tsessionid\tsecret\n")
    assert has_cookies() is True
    assert load_cookies() == ".tiktok.com\tTRUE\t/\tTRUE\t0\tsessionid\tsecret"
    assert os.path.exists(cookies.COOKIE_PATH)


def test_whitespace_only_file_counts_as_absent():
    save_cookies("   \n\n")
    assert load_cookies() is None
    assert has_cookies() is False


def test_clear_cookies_is_idempotent():
    save_cookies("data")
    clear_cookies()
    assert has_cookies() is False
    clear_cookies()
    assert has_cookies() is False
