"""Inbound policy: who may call us, and how often.

All three middlewares are opt-in or tuned by environment variables so a local
run on loopback stays frictionless while a self-hosted deployment can be locked
down:

    SAVETOK_PASSWORD      shared password; auth is off when unset
    SAVETOK_RATE_LIMIT    requests per minute per IP (default 240)
"""

from __future__ import annotations

import base64
import binascii
import hmac
import os
import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Paths that are immutable and heavily requested on every page load. Counting
# them would spend the budget on assets instead of API calls.
_UNCOUNTED_PREFIXES = ("/assets/", "/favicon.svg")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), interest-cohort=()",
    # No inline or eval'd script; the bundle is same-origin. Thumbnails come from
    # the TikTok CDNs the outbound allowlist already permits. style-src needs
    # 'unsafe-inline' only because the app sets CSS custom properties inline.
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; "
        "img-src 'self' data: https://*.tiktokcdn.com https://*.tiktokcdn-us.com "
        "https://*.ttwstatic.com https://*.byteoversea.com https://*.ibyteimg.com; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """One shared password. Inactive unless SAVETOK_PASSWORD is set.

    The username is ignored; only the password is compared, in constant time.
    """

    def __init__(self, app, password: str):
        super().__init__(app)
        self._password = password.encode()

    def _matches(self, header: str) -> bool:
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "basic" or not token:
            return False
        try:
            decoded = base64.b64decode(token, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            return False
        _, _, supplied = decoded.partition(":")
        return hmac.compare_digest(supplied.encode(), self._password)

    async def dispatch(self, request, call_next):
        # Preflights carry no credentials, so challenging them breaks CORS.
        if request.method == "OPTIONS":
            return await call_next(request)
        if not self._matches(request.headers.get("authorization", "")):
            return JSONResponse(
                {"detail": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="SaveTok", charset="UTF-8"'},
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window per client IP. Counts API traffic, not static assets."""

    def __init__(self, app, limit: int, window: float = 60.0):
        super().__init__(app)
        self._limit = max(limit, 1)
        self._window = window
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _client(self, request) -> str:
        # Trusts X-Forwarded-For only when the app is explicitly behind a proxy.
        if os.getenv("SAVETOK_TRUST_PROXY"):
            forwarded = request.headers.get("x-forwarded-for", "")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request, call_next):
        if request.url.path.startswith(_UNCOUNTED_PREFIXES):
            return await call_next(request)

        now = time.monotonic()
        client = self._client(request)
        with self._lock:
            hits = [t for t in self._hits.get(client, []) if now - t < self._window]
            if len(hits) >= self._limit:
                retry = max(1, int(self._window - (now - hits[0])))
                self._hits[client] = hits
                return JSONResponse(
                    {"detail": "Too many requests, slow down."},
                    status_code=429,
                    headers={"Retry-After": str(retry)},
                )
            hits.append(now)
            self._hits[client] = hits
            if len(self._hits) > 512:  # drop idle clients
                self._hits = {
                    ip: stamps
                    for ip, stamps in self._hits.items()
                    if stamps and now - stamps[-1] < self._window
                }
        return await call_next(request)
