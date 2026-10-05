"""Inbound policy: authentication, rate limiting, response headers."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security import BasicAuthMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware


def bare_app() -> FastAPI:
    app = FastAPI()

    @app.get("/")
    def index():
        return {"ok": True}

    return app


def test_basic_auth_challenges_then_accepts():
    app = bare_app()
    app.add_middleware(BasicAuthMiddleware, password="s3cret")
    client = TestClient(app)

    unauth = client.get("/")
    assert unauth.status_code == 401
    assert unauth.headers["www-authenticate"].startswith("Basic")

    # Username is ignored; only the password is compared.
    assert client.get("/", auth=("anyone", "s3cret")).status_code == 200
    assert client.get("/", auth=("anyone", "wrong")).status_code == 401
    assert client.get("/", headers={"Authorization": "Basic not-base64!"}).status_code == 401
    assert client.get("/", headers={"Authorization": "Bearer s3cret"}).status_code == 401


def test_basic_auth_leaves_preflight_alone():
    app = bare_app()
    app.add_middleware(BasicAuthMiddleware, password="s3cret")
    client = TestClient(app)
    # A preflight carries no credentials; challenging it would break CORS.
    assert client.options("/").status_code != 401


def test_rate_limit_returns_429_with_retry_after():
    app = bare_app()
    app.add_middleware(RateLimitMiddleware, limit=3)
    client = TestClient(app)

    assert [client.get("/").status_code for _ in range(3)] == [200, 200, 200]
    blocked = client.get("/")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1


def test_rate_limit_skips_static_assets():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limit=1)

    @app.get("/assets/{name}")
    def asset(name: str):
        return {"asset": name}

    @app.get("/api")
    def api():
        return {"ok": True}

    client = TestClient(app)
    for _ in range(10):
        assert client.get("/assets/app.js").status_code == 200
    assert client.get("/api").status_code == 200
    assert client.get("/api").status_code == 429


def test_security_headers_are_added():
    app = bare_app()
    app.add_middleware(SecurityHeadersMiddleware)
    headers = TestClient(app).get("/").headers

    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    csp = headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "script-src 'self'" in csp


def test_running_app_sends_security_headers(client):
    headers = client.get("/auth/status").headers
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert "content-security-policy" in headers
