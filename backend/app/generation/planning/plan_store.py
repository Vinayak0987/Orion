"""Execution plan store - the `execution_plans` + `plan_events` tables.

A compiled `ExecutionPlan` (compile.py) is persisted whole as one JSON column.
Re-saving it after every node (`save_plan`) is the checkpoint that gives crash
recovery with no external infrastructure: on restart, unfinished plans are
reloaded and resumed from their first non-terminal node.

`plan_events` is an append-only execution trace. Each event is written in the
SAME transaction as the plan checkpoint (`save_plan_with_event`), so the log and
the state can never disagree - this is the offline, single-node replacement for
a message broker + outbox.

House style follows `app/db/sqlite.py` and `app/planning/store.py`: stdlib
sqlite3, WAL (inherited from the shared `connection()`), UTC ISO timestamps,
JSON columns, idempotent DDL.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime

from app.generation.db.sqlite import connection
from app.generation.planning.plan_models import ExecutionPlan

SCHEMA = """
CREATE TABLE IF NOT EXISTS execution_plans (
    id          TEXT PRIMARY KEY,
    report_id   TEXT NOT NULL,
    prompt      TEXT NOT NULL,
    status      TEXT NOT NULL,
    plan_json   TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plans_created ON execution_plans(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_plans_report  ON execution_plans(report_id);

CREATE TABLE IF NOT EXISTS plan_events (
    id          TEXT PRIMARY KEY,
    plan_id     TEXT NOT NULL,
    node_id     TEXT,
    event_type  TEXT NOT NULL,
    data_json   TEXT,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plan_events_plan ON plan_events(plan_id, created_at);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _event_id() -> str:
    return uuid.uuid4().hex[:12]


def init_plans() -> None:
    """Idempotent. Called from `init_planning()` on FastAPI startup."""
    with connection() as conn:
        conn.executescript(SCHEMA)


# =============================================================================
# execution_plans
# =============================================================================


def create_plan(plan: ExecutionPlan) -> ExecutionPlan:
    """Insert a freshly compiled plan and return it unchanged."""
    with connection() as conn:
        conn.execute(
            "INSERT INTO execution_plans "
            "(id, report_id, prompt, status, plan_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                plan.id,
                plan.report_id,
                plan.prompt,
                plan.status,
                plan.model_dump_json(),
                plan.created_at,
                plan.updated_at,
            ),
        )
    return plan


def get_plan(plan_id: str) -> ExecutionPlan | None:
    """Full plan, reconstructed from its JSON column, or None if unknown."""
    with connection() as conn:
        row = conn.execute(
            "SELECT plan_json FROM execution_plans WHERE id = ?", (plan_id,)
        ).fetchone()
    if row is None:
        return None
    return ExecutionPlan.model_validate_json(row["plan_json"])


def save_plan(plan: ExecutionPlan) -> ExecutionPlan:
    """Checkpoint: overwrite the stored plan with current node statuses.

    Bumps `updated_at`. This is called after every node so a crash loses at
    most the node in flight.
    """
    plan.updated_at = _now()
    with connection() as conn:
        _write_plan(conn, plan)
    return plan


def list_plans(limit: int = 50, offset: int = 0) -> list[dict]:
    """Summary rows only: id, report_id, status, prompt, node count, created_at."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, report_id, prompt, status, plan_json, created_at "
            "FROM execution_plans ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    summaries: list[dict] = []
    for row in rows:
        payload = json.loads(row["plan_json"])
        summaries.append(
            {
                "id": row["id"],
                "report_id": row["report_id"],
                "prompt": row["prompt"],
                "status": row["status"],
                "node_count": len(payload.get("nodes", [])),
                "created_at": row["created_at"],
            }
        )
    return summaries


def list_unfinished_plans() -> list[ExecutionPlan]:
    """Plans that were mid-run when the process last stopped (status 'running').

    The resume path reloads these and continues from their first non-terminal
    node - the crash-recovery entry point.
    """
    with connection() as conn:
        rows = conn.execute(
            "SELECT plan_json FROM execution_plans WHERE status = 'running' "
            "ORDER BY created_at DESC"
        ).fetchall()
    return [ExecutionPlan.model_validate_json(r["plan_json"]) for r in rows]


# =============================================================================
# plan_events - append-only trace
# =============================================================================


def add_event(
    plan_id: str, event_type: str, *, node_id: str | None = None, data: dict | None = None
) -> None:
    """Append one execution event."""
    with connection() as conn:
        _write_event(conn, plan_id, event_type, node_id, data)


def save_plan_with_event(
    plan: ExecutionPlan,
    event_type: str,
    *,
    node_id: str | None = None,
    data: dict | None = None,
) -> ExecutionPlan:
    """Checkpoint the plan AND append an event in ONE transaction.

    The state update and its trace entry commit together or not at all, so a
    reader can never see a node marked completed without the matching event, or
    vice versa (the offline replacement for a transactional outbox).
    """
    plan.updated_at = _now()
    with connection() as conn:
        _write_plan(conn, plan)
        _write_event(conn, plan.id, event_type, node_id, data)
    return plan


def get_events(plan_id: str, limit: int = 500) -> list[dict]:
    """The execution trace for a plan, oldest first."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, plan_id, node_id, event_type, data_json, created_at "
            "FROM plan_events WHERE plan_id = ? ORDER BY created_at, id LIMIT ?",
            (plan_id, limit),
        ).fetchall()
    events: list[dict] = []
    for row in rows:
        record = dict(row)
        raw = record.pop("data_json")
        record["data"] = json.loads(raw) if raw else None
        events.append(record)
    return events


# =============================================================================
# internals - operate on an open connection so callers can share a transaction
# =============================================================================


def _write_plan(conn: sqlite3.Connection, plan: ExecutionPlan) -> None:
    conn.execute(
        "UPDATE execution_plans SET status = ?, plan_json = ?, updated_at = ? "
        "WHERE id = ?",
        (plan.status, plan.model_dump_json(), plan.updated_at, plan.id),
    )


def _write_event(
    conn: sqlite3.Connection,
    plan_id: str,
    event_type: str,
    node_id: str | None,
    data: dict | None,
) -> None:
    conn.execute(
        "INSERT INTO plan_events (id, plan_id, node_id, event_type, data_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            _event_id(),
            plan_id,
            node_id,
            event_type,
            json.dumps(data, default=str) if data else None,
            _now(),
        ),
    )
