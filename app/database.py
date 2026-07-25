"""SQLite persistence for queue items."""

import sqlite3
import time
from pathlib import Path

DB_DIR = Path("/tmp/tiktok_queue")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DB_DIR / "tiktok.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=3000")
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS queue_items (
                id          TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                format_id   TEXT DEFAULT '',
                title       TEXT DEFAULT '',
                status      TEXT DEFAULT 'pending'
                            CHECK(status IN ('pending','downloading','completed','failed')),
                video_id    TEXT DEFAULT '',
                file_path   TEXT,
                error       TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL
            );
        """)


# ── CRUD ────────────────────────────────────────────────────────────────────

def insert_item(item: dict) -> dict:
    now = time.time()
    item["created_at"] = now
    item["updated_at"] = now
    with _conn() as conn:
        conn.execute(
            """INSERT INTO queue_items
               (id,url,format_id,title,status,video_id,file_path,error,retry_count,created_at,updated_at)
               VALUES (:id,:url,:format_id,:title,:status,:video_id,:file_path,:error,:retry_count,:created_at,:updated_at)""",
            item,
        )
    return item


def update_item(item_id: str, **fields):
    fields["updated_at"] = time.time()
    sets = ", ".join(f"{k}=? " for k in fields)
    vals = list(fields.values()) + [item_id]
    with _conn() as conn:
        conn.execute(f"UPDATE queue_items SET {sets} WHERE id=?", vals)


def list_items() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM queue_items ORDER BY created_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_item(item_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM queue_items WHERE id=?", (item_id,)
        ).fetchone()
    return dict(row) if row else None


def claim_pending() -> dict | None:
    """Atomically claim the oldest pending item (mark 'downloading')."""
    with _conn() as conn:
        row = conn.execute(
            "UPDATE queue_items SET status='downloading', updated_at=? "
            "WHERE id=(SELECT id FROM queue_items WHERE status='pending' ORDER BY created_at ASC LIMIT 1) "
            "RETURNING *",
            (time.time(),),
        ).fetchone()
    return dict(row) if row else None


def remove_item(item_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM queue_items WHERE id=?", (item_id,))
        return cur.rowcount > 0


def clear_items() -> int:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM queue_items")
        return cur.rowcount


def pending_count() -> int:
    with _conn() as conn:
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM queue_items WHERE status='pending'"
        ).fetchone()
    return count


def reset_stale_downloading():
    """Reset items stuck in 'downloading' back to 'pending' on startup."""
    with _conn() as conn:
        conn.execute(
            "UPDATE queue_items SET status='pending', updated_at=? WHERE status='downloading'",
            (time.time(),),
        )


init_db()
