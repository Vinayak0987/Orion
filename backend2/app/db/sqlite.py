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
    if "mode" not in cols:
        conn.execute("ALTER TABLE missions ADD COLUMN mode TEXT NOT NULL DEFAULT 'action'")

    agent_cols = {row["name"] for row in conn.execute("PRAGMA table_info(agents)").fetchall()}
    if "memory_ttl_days" not in agent_cols:
        conn.execute("ALTER TABLE agents ADD COLUMN memory_ttl_days INTEGER NOT NULL DEFAULT 30")
    if "version" not in agent_cols:
        conn.execute("ALTER TABLE agents ADD COLUMN version TEXT NOT NULL DEFAULT 'v1.0.0'")
    if "origin" not in agent_cols:
        conn.execute("ALTER TABLE agents ADD COLUMN origin TEXT NOT NULL DEFAULT 'reusable'")
    if "source_mission_id" not in agent_cols:
        conn.execute("ALTER TABLE agents ADD COLUMN source_mission_id TEXT")
    if "role_title" not in agent_cols:
        conn.execute("ALTER TABLE agents ADD COLUMN role_title TEXT")

    # Chat messages: charts (chart image artifacts from code_interpreter).
    msg_cols = {row["name"] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
    if msg_cols and "charts" not in msg_cols:
        conn.execute("ALTER TABLE messages ADD COLUMN charts TEXT NOT NULL DEFAULT '[]'")

    # Departments + membership (the Master routes into these).
    conn.execute(
        """CREATE TABLE IF NOT EXISTS departments (
               id TEXT PRIMARY KEY, name TEXT NOT NULL, slug TEXT,
               description TEXT NOT NULL DEFAULT '', purpose TEXT NOT NULL DEFAULT '',
               responsibilities TEXT NOT NULL DEFAULT '[]', dept_type TEXT NOT NULL DEFAULT 'custom',
               instructions TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active',
               config TEXT NOT NULL DEFAULT '{}', is_default INTEGER NOT NULL DEFAULT 0,
               created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_departments_owner ON departments(created_by, status)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS department_members (
               id TEXT PRIMARY KEY, department_id TEXT NOT NULL, agent_id TEXT NOT NULL,
               role TEXT NOT NULL DEFAULT 'specialist', status TEXT NOT NULL DEFAULT 'active',
               instructions TEXT NOT NULL DEFAULT '', permissions TEXT NOT NULL DEFAULT '{}',
               created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
               UNIQUE(department_id, agent_id), FOREIGN KEY (department_id) REFERENCES departments(id)
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dept_members_dept  ON department_members(department_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dept_members_agent ON department_members(agent_id)")

    # Generic namespaced key/value store backing the key_value_store + local_cache
    # built-in tools. Kept here (not schema.sql) so it is always present.
    conn.execute(
        """CREATE TABLE IF NOT EXISTS kv_store (
               namespace  TEXT NOT NULL,
               key        TEXT NOT NULL,
               value      TEXT NOT NULL,
               expires_at TEXT,
               updated_at TEXT NOT NULL,
               PRIMARY KEY (namespace, key)
           )"""
    )

    # Unified connectable catalog: extend `integrations` with per-tool connect
    # method + metadata (idempotent column adds).
    try:
        intg_cols = {row["name"] for row in conn.execute("PRAGMA table_info(integrations)").fetchall()}
        for col, ddl in (
            ("connect_method", "ALTER TABLE integrations ADD COLUMN connect_method TEXT NOT NULL DEFAULT 'api_key'"),
            ("oauth_provider", "ALTER TABLE integrations ADD COLUMN oauth_provider TEXT"),
            ("mcp_url", "ALTER TABLE integrations ADD COLUMN mcp_url TEXT"),
            ("docs_url", "ALTER TABLE integrations ADD COLUMN docs_url TEXT"),
            ("logo_key", "ALTER TABLE integrations ADD COLUMN logo_key TEXT"),
        ):
            if col not in intg_cols:
                conn.execute(ddl)
    except Exception:  # noqa: BLE001 — integrations table may not exist on a fresh DB yet
        pass

    # MCP servers may carry an encrypted auth token for hosted/authenticated servers.
    try:
        mcp_cols = {row["name"] for row in conn.execute("PRAGMA table_info(mcp_servers)").fetchall()}
        if "auth_token" not in mcp_cols:
            conn.execute("ALTER TABLE mcp_servers ADD COLUMN auth_token TEXT")
        if "auth_scheme" not in mcp_cols:
            conn.execute("ALTER TABLE mcp_servers ADD COLUMN auth_scheme TEXT NOT NULL DEFAULT 'bearer'")
        if "refresh_token" not in mcp_cols:
            conn.execute("ALTER TABLE mcp_servers ADD COLUMN refresh_token TEXT")
        if "oauth_config" not in mcp_cols:
            conn.execute("ALTER TABLE mcp_servers ADD COLUMN oauth_config TEXT")
    except Exception:  # noqa: BLE001
        pass

    # In-flight MCP OAuth flows (one-time state + PKCE + dynamically-registered client).
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mcp_oauth_flows (
               state          TEXT PRIMARY KEY,
               mcp_url        TEXT NOT NULL,
               server_name    TEXT,
               code_verifier  TEXT NOT NULL,
               client_id      TEXT NOT NULL,
               client_secret  TEXT,
               token_endpoint TEXT NOT NULL,
               redirect_uri   TEXT NOT NULL,
               resource       TEXT,
               created_at     TEXT NOT NULL,
               expires_at     TEXT NOT NULL
           )"""
    )
