"""Outbound policy: what we are willing to fetch, and how fast."""

import socket
import time

import pytest

from app import net


def test_allows_tiktok_hosts():
    for host in (
        "www.tiktok.com",
        "vm.tiktok.com",
        "v16-webapp-prime.tiktok.com",
        "webapp-sg.tiktok.com",
        "p16-sign-va.tiktokcdn.com",
        "sf16-website-login.neutral.ttwstatic.com",
    ):
        assert net.host_allowed(host), host


def test_rejects_lookalikes_and_other_hosts():
    for host in (
        "eviltiktok.com",
        "tiktok.com.evil.com",
        "example.com",
        "127.0.0.1",
        "169.254.169.254",
        "",
    ):
        assert not net.host_allowed(host), host


def test_check_outbound_url_rejects_non_allowlisted_hosts():
    # The exact payload that used to make /download a general-purpose fetcher.
    with pytest.raises(net.BlockedTarget):
        net.check_outbound_url("http://127.0.0.1:8080/auth/status")
    with pytest.raises(net.BlockedTarget):
        net.check_outbound_url("https://example.com/video/1")
    with pytest.raises(net.BlockedTarget):
        net.check_outbound_url("http://169.254.169.254/latest/meta-data/")


def test_check_outbound_url_rejects_non_http_schemes():
    for candidate in ("file:///etc/passwd", "gopher://tiktok.com/", "ftp://tiktok.com/x"):
        with pytest.raises(net.BlockedTarget):
            net.check_outbound_url(candidate)


def test_check_outbound_url_rejects_allowlisted_host_that_resolves_inward(monkeypatch):
    # Even a TikTok name must not be followed to a private address (rebinding).
    monkeypatch.setattr(net, "_resolves_public", lambda host: False)
    with pytest.raises(net.BlockedTarget):
        net.check_outbound_url("https://www.tiktok.com/@u/video/1")


def test_check_outbound_url_accepts_allowed_public_host(monkeypatch):
    monkeypatch.setattr(net, "_resolves_public", lambda host: True)
    url = "https://v16-webapp-prime.tiktok.com/video.mp4"
    assert net.check_outbound_url(url) == url


def test_resolves_public_rejects_link_local(monkeypatch):
    net._dns_cache.clear()
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 0))],
    )
    assert net._resolves_public("metadata.internal") is False


def test_resolves_public_accepts_public_address(monkeypatch):
    net._dns_cache.clear()
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    assert net._resolves_public("example.com") is True


def test_resolves_public_rejects_unresolvable(monkeypatch):
    net._dns_cache.clear()

    def boom(host, port):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    assert net._resolves_public("nope.invalid") is False


def test_token_bucket_spaces_requests():
    bucket = net.TokenBucket(rate=50, burst=1)
    start = time.monotonic()
    for _ in range(4):
        bucket.acquire()
    # One token up front, then three more at 50/s.
    assert time.monotonic() - start >= 0.05


def test_cdn_headers_carry_referer_and_user_agent():
    assert net.CDN_HEADERS["Referer"] == "https://www.tiktok.com/"
    assert "Mozilla/5.0" in net.CDN_HEADERS["User-Agent"]


def test_stream_to_file_writes_every_chunk(tmp_path):
    class FakeResponse:
        def iter_content(self, size):
            return iter([b"abc", b"", b"defg"])

    dest = tmp_path / "out.mp4"
    written = net.stream_to_file(FakeResponse(), str(dest), chunk_size=2)
    assert written == 7
    assert dest.read_bytes() == b"abcdefg"
