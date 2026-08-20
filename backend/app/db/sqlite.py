"""F59/F60 - SQLite persistence.

Standard-library sqlite3 only, no ORM. Two tables:

    sessions          - one row per generation run (F59)
    evaluation_results - one row per (prompt, approach, metric) (F60)

WAL mode is enabled so the evaluation harness can read while a generation writes.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Iterator

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id                  TEXT PRIMARY KEY,
    raw_prompt          TEXT NOT NULL,
    intent_json         TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    plan_json           TEXT,
    metadata_json       TEXT,
    active_departments  TEXT,
    skipped_departments TEXT,
    total_tokens        INTEGER DEFAULT 0,
    total_duration_ms   INTEGER,
    completeness_score  REAL,
    created_at          TEXT NOT NULL,
    completed_at        TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_status     ON sessions(status);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_label    TEXT NOT NULL,
    prompt_id    TEXT NOT NULL,
    prompt_text  TEXT NOT NULL,
    approach     TEXT NOT NULL,
    metric       TEXT NOT NULL,
    score        REAL,
    details_json TEXT,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_lookup
    ON evaluation_results(run_label, approach, metric);
"""


def _now() -> str:
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
    """Idempotent. Called on FastAPI startup."""
    with connection() as conn:
        conn.executescript(SCHEMA)


# =============================================================================
# F59 - sessions
# =============================================================================


def create_session(session_id: str, raw_prompt: str) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (id, raw_prompt, status, created_at) "
            "VALUES (?, ?, 'pending', ?)",
            (session_id, raw_prompt, _now()),
        )


def update_session(session_id: str, **fields: Any) -> None:
    """Update named columns. dict/list values are JSON-encoded automatically."""
    if not fields:
        return
    allowed = {
        "intent_json",
        "status",
        "plan_json",
        "metadata_json",
        "active_departments",
        "skipped_departments",
        "total_tokens",
        "total_duration_ms",
        "completeness_score",
        "completed_at",
    }
    unknown = fields.keys() - allowed
    if unknown:
        raise ValueError(f"Unknown session column(s): {sorted(unknown)}")

    encoded = {
        k: (json.dumps(v, default=str) if isinstance(v, (dict, list)) else v)
        for k, v in fields.items()
    }
    assignments = ", ".join(f"{k} = ?" for k in encoded)
    with connection() as conn:
        conn.execute(
            f"UPDATE sessions SET {assignments} WHERE id = ?",  # noqa: S608 - keys whitelisted
            (*encoded.values(), session_id),
        )


def get_session(session_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return _decode_session(row) if row else None


def list_sessions(limit: int = 50, offset: int = 0) -> list[dict]:
    """F51 - history list for the frontend."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, raw_prompt, status, completeness_score, total_duration_ms, "
            "created_at, completed_at FROM sessions "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_session(session_id: str) -> bool:
    with connection() as conn:
        cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return cursor.rowcount > 0


def _decode_session(row: sqlite3.Row) -> dict:
    record = dict(row)
    for field in ("intent_json", "plan_json", "metadata_json"):
        raw = record.get(field)
        record[field.removesuffix("_json")] = json.loads(raw) if raw else None
        record.pop(field, None)
    for field in ("active_departments", "skipped_departments"):
        raw = record.get(field)
        record[field] = json.loads(raw) if raw else []
    return record


# =============================================================================
# F60 - evaluation results
# =============================================================================


def record_metric(
    run_label: str,
    prompt_id: str,
    prompt_text: str,
    approach: str,
    metric: str,
    score: float | None,
    details: dict | None = None,
) -> None:
    """approach: 'multi_agent' | 'baseline' | 'multi_agent_no_api' | 'all_departments'"""
    with connection() as conn:
        conn.execute(
            "INSERT INTO evaluation_results "
            "(run_label, prompt_id, prompt_text, approach, metric, score, details_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_label,
                prompt_id,
                prompt_text,
                approach,
                metric,
                score,
                json.dumps(details, default=str) if details else None,
                _now(),
            ),
        )


def aggregate_metrics(run_label: str) -> list[dict]:
    """Mean/stdev per (approach, metric) - the source for the paper's results table."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT approach, metric, COUNT(*) AS n, AVG(score) AS mean_score, "
            "MIN(score) AS min_score, MAX(score) AS max_score "
            "FROM evaluation_results WHERE run_label = ? AND score IS NOT NULL "
            "GROUP BY approach, metric ORDER BY metric, approach",
            (run_label,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_metrics(run_label: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT run_label, prompt_id, prompt_text, approach, metric, score, "
            "details_json, created_at FROM evaluation_results "
            "WHERE run_label = ? ORDER BY prompt_id, metric, approach",
            (run_label,),
        ).fetchall()
    return [dict(r) for r in rows]
