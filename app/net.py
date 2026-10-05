"""Outbound policy: who we are willing to fetch, and how fast.

Both the page URL and the direct media URL arrive as request parameters, so a
URL from a caller is never fetched blindly. Without this the download endpoint
is a general-purpose fetcher — it would happily return the response of any
address the server can reach, including internal ones.

Also owns the shared CDN client: connection reuse and one TLS fingerprint setup
instead of renegotiating per request.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import threading
import time
from urllib.parse import urlparse

from curl_cffi import requests as cffi_requests


class BlockedTarget(ValueError):
    """An outbound URL we refuse to fetch."""


# TikTok serves pages and media from these. Matched on label boundaries, so
# "eviltiktok.com" does not match "tiktok.com".
ALLOWED_HOSTS = (
    "tiktok.com",
    "tiktokcdn.com",
    "tiktokcdn-us.com",
    "tiktokv.com",
    "tiktokv.us",
    "ttwstatic.com",
    "byteoversea.com",
    "ibytedtos.com",
    "ibyteimg.com",
    "muscdn.com",
)

# Sent with every direct media request. TikTok's CDN checks these.
CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.tiktok.com/",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "*/*",
}


def host_allowed(hostname: str) -> bool:
    host = (hostname or "").lower().rstrip(".")
    if not host:
        return False
    return any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_HOSTS)


_dns_cache: dict[str, tuple[float, bool]] = {}
_dns_lock = threading.Lock()
_DNS_TTL = 60.0


def _resolves_public(hostname: str) -> bool:
    """Reject hosts resolving to loopback/private/link-local space."""
    now = time.monotonic()
    with _dns_lock:
        cached = _dns_cache.get(hostname)
        if cached is not None and now - cached[0] < _DNS_TTL:
            return cached[1]

    try:
        infos = socket.getaddrinfo(hostname, None)
    except OSError:
        allowed = False
    else:
        allowed = bool(infos)
        for info in infos:
            try:
                ip = ipaddress.ip_address(info[4][0])
            except ValueError:
                allowed = False
                break
            if not ip.is_global:
                allowed = False
                break

    with _dns_lock:
        _dns_cache[hostname] = (now, allowed)
    return allowed


def check_outbound_url(url: str) -> str:
    """Return `url` when it is safe to fetch, else raise BlockedTarget."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise BlockedTarget("Only http(s) targets are supported")
    host = parsed.hostname or ""
    if not host_allowed(host):
        raise BlockedTarget("Unsupported host")
    if not _resolves_public(host):
        raise BlockedTarget("Target does not resolve to a public address")
    return url


# ── Outbound pacing ────────────────────────────────────────────────────────
# TikTok throttles and blocks aggressively, so requests are spaced out. This is
# deliberately a limiter, not a throughput optimiser: raising it trades latency
# for a higher chance of being blocked. Set SAVETOK_OUTBOUND_RPS to tune.


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = max(float(rate), 0.05)
        self.burst = max(int(burst), 1)
        self._tokens = float(self.burst)
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(self.burst, self._tokens + (now - self._updated) * self.rate)
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self.rate
            time.sleep(min(wait, 1.0))


_outbound = TokenBucket(
    rate=float(os.getenv("SAVETOK_OUTBOUND_RPS", "1")),
    burst=int(os.getenv("SAVETOK_OUTBOUND_BURST", "3")),
)


def pace_outbound() -> None:
    """Block until the outbound budget allows another TikTok request."""
    _outbound.acquire()


# ── Shared media client ────────────────────────────────────────────────────

_session = cffi_requests.Session(impersonate="chrome")


def cdn_get(url: str, *, cookies: dict[str, str] | None = None, stream: bool = False):
    """GET a media URL with the identity and pacing the CDN expects."""
    pace_outbound()
    return _session.get(
        url,
        headers=CDN_HEADERS,
        cookies=cookies or {},
        impersonate="chrome",
        stream=stream,
        timeout=60,
    )


def stream_to_file(response, path: str, chunk_size: int = 256 * 1024) -> int:
    """Write a response body to disk in chunks, returning the byte count.

    Chunked rather than `response.content` so a large video is never held in
    memory in full.
    """
    total = 0
    with open(path, "wb") as handle:
        for chunk in response.iter_content(chunk_size):
            if chunk:
                handle.write(chunk)
                total += len(chunk)
    return total
