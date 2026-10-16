"""Orion v2 — SQLite persistence core.

Standard-library sqlite3 only, no ORM. WAL mode so the WebSocket reader and the
mission writer never block each other. All feature stores (missions, agents,
traces, settings) import `connection()` and `_now()` from here.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from app.config import settings

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _now() -> str:
    """UTC ISO-8601 timestamp — the one timestamp format used everywhere."""
    return datetime.now(UTC).isoformat()


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.sqlite_file, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Idempotent. Runs schema.sql on startup, then applies light migrations."""
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    with connection() as conn:
        conn.executescript(schema)
        _migrate(conn)


def _migrate(conn) -> None:
    """Add columns that may be missing on an older DB. Idempotent."""
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(missions)").fetchall()}
    if "conversation_id" not in cols:
        conn.execute("ALTER TABLE missions ADD COLUMN conversation_id TEXT")
