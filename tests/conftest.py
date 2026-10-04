"""Shared test fixtures.

Import order matters: the queue DB and cookie paths are redirected to a temp
directory *before* `app.download_manager` is imported, because that module
resets stale rows and starts its background worker thread as a side effect.
The worker's `claim_pending` name is then stubbed out so it can never pull
items (and hit the network) during tests.
"""

import os
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="tiktok-tests-")

import app.cookies as cookies_mod  # noqa: E402
import app.database as database  # noqa: E402

database.DB_PATH = os.path.join(_TMP, "tiktok.db")
database.init_db()

import app.download_manager as download_manager  # noqa: E402

download_manager.claim_pending = lambda: None

cookies_mod.COOKIE_DIR = _TMP
cookies_mod.COOKIE_PATH = os.path.join(_TMP, "tiktok_cookies.txt")


@pytest.fixture(autouse=True)
def isolate_state():
    """Give every test an empty queue and no cookies."""
    database.clear_items()
    cookies_mod.clear_cookies()
    yield
    database.clear_items()
    cookies_mod.clear_cookies()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
