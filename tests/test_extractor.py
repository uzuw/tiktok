"""Tests for URL detection in app.extractor."""

import pytest

from app.extractor import is_video_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.tiktok.com/@user/video/7123456789012345678",
        "https://www.tiktok.com/@user/video/7123456789012345678?is_from_webapp=1",
        "https://m.tiktok.com/v/123/video/456",
        "https://vm.tiktok.com/abc/video/123",
    ],
)
def test_video_urls_recognized(url):
    assert is_video_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://www.tiktok.com/@user",
        "https://www.tiktok.com/@user/video/notanumber",
        "https://www.tiktok.com/foryou",
        "not a url",
    ],
)
def test_non_video_urls_rejected(url):
    assert is_video_url(url) is False
