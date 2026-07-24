"""Cookie management for TikTok auth."""

import os

COOKIE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
COOKIE_PATH = os.path.join(COOKIE_DIR, "tiktok_cookies.txt")


def save_cookies(text: str) -> None:
    """Save cookie text to disk."""
    os.makedirs(COOKIE_DIR, exist_ok=True)
    with open(COOKIE_PATH, "w") as f:
        f.write(text)


def load_cookies() -> str | None:
    """Read cookie text from disk. Returns None if no cookies saved."""
    if not os.path.exists(COOKIE_PATH):
        return None
    with open(COOKIE_PATH) as f:
        text = f.read().strip()
    return text if text else None


def has_cookies() -> bool:
    return load_cookies() is not None


def clear_cookies() -> None:
    if os.path.exists(COOKIE_PATH):
        os.unlink(COOKIE_PATH)
