"""Planning report store - the `planning_reports` table (design.md §5).

One row per pre-execution report. A report exists BEFORE any session: it is
the inspect-and-confirm artefact an operator reviews before a run spends
multi-agent quota, which is why it is a table of its own and not a `sessions`
column (`sessions.plan_json` already means the finished business plan -
memory.md §4).

Status machine, enforced here and mirroring the operating layer's
`IllegalTransition` discipline:

    ready --confirm--> confirmed --run completed--> executed
    ready --24 h TTL--> expired   (computed lazily at read time; no reaper)
    blocked                      (terminal)

No `pending` row is ever stored: creation receives a fully computed report
and inserts a final `ready` or `blocked` row, so a report can never be
observed half-built.

House style follows `app/db/sqlite.py`: stdlib sqlite3 only, WAL, UTC ISO
timestamps, JSON columns, idempotent DDL. The authoritative TTL constant
lives in `app.generation.planning.service` (`REPORT_TTL_HOURS = 24`); the helpers here
take it as a parameter defaulting to the same value so the store is usable
standalone.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.generation.db.sqlite import connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS planning_reports (
    id              TEXT PRIMARY KEY,
    raw_prompt      TEXT NOT NULL,
    intent_json     TEXT,
    intent_source   TEXT NOT NULL,
    status          TEXT NOT NULL,
    blockers_json   TEXT NOT NULL DEFAULT '[]',
    warnings_json   TEXT NOT NULL DEFAULT '[]',
    routing_json    TEXT,
    agents_json     TEXT,
    active_departments   TEXT,
    skipped_departments  TEXT,
    estimated_agent_calls INTEGER NOT NULL DEFAULT 0,
    estimated_max_completion_tokens INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    confirmed_at     TEXT,
    confirmed_by     TEXT,
    executed_at      TEXT,
    executed_session_id  TEXT
);

CREATE INDEX IF NOT EXISTS idx_planning_created ON planning_reports(created_at DESC);
"""

# Creation may only ever store a final verdict. `confirmed` and `executed` are
# reached only through the guarded helpers below; `expired` is never stored at
# all - it is derived from created_at at read time.
FINAL_CREATION_STATUSES = frozenset({"ready", "blocked"})

# Logical field names accepted by create_report (whitelist, like
# sqlite.update_session's allowed-column set).
_ALLOWED_FIELDS = frozenset(
    {
        "id",
        "raw_prompt",
        "intent",
        "intent_source",
        "status",
        "blockers",
        "warnings",
        "routing",
        "agents",
        "active_departments",
        "skipped_departments",
        "estimated_agent_calls",
        "estimated_max_completion_tokens",
        "created_at",
    }
)


class IllegalTransition(RuntimeError):
    """A planning report was moved between states by an unsanctioned path."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def new_report_id() -> str:
    """Same shape as session ids (`uuid4().hex[:12]`, runner.new_session_id)."""
    return uuid.uuid4().hex[:12]


def init_planning() -> None:
    """Idempotent. Called on FastAPI startup next to operating `init_all()`."""
    with connection() as conn:
        conn.executescript(SCHEMA)


# =============================================================================
# TTL - lazy expiry, no reaper process
# =============================================================================


def is_expired(created_at: str, *, ttl_hours: float = 24.0) -> bool:
    """True once `created_at` (UTC ISO) is older than the TTL.

    The boundary is inclusive: a report exactly 24 h old is expired.
    """
    created = datetime.fromisoformat(created_at)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return datetime.now(UTC) - created >= timedelta(hours=ttl_hours)


def effective_status(record: dict, *, ttl_hours: float = 24.0) -> str:
    """The status a reader should see. 'expired' is derived, never stored:
    a 'ready' report past its TTL reads as expired (design.md §5)."""
    if record["status"] == "ready" and is_expired(record["created_at"], ttl_hours=ttl_hours):
        return "expired"
    return record["status"]


# =============================================================================
# CRUD
# =============================================================================


def create_report(**fields: Any) -> dict:
    """Insert a fully computed report and return the decoded row.

    No `pending` row is ever stored: the caller (the service) computes the
    whole report first and passes a final `status` of 'ready' or 'blocked'.
    `id` and `created_at` are generated here; either may be overridden
    (tests backdate `created_at` to exercise the TTL boundary).
    """
    unknown = fields.keys() - _ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"Unknown planning report field(s): {sorted(unknown)}")

    for required in ("raw_prompt", "intent_source"):
        if not fields.get(required):
            raise ValueError(f"create_report requires a non-empty '{required}'")

    status = fields.get("status", "ready")
    if status not in FINAL_CREATION_STATUSES:
        raise ValueError(
            "create_report stores a final 'ready' or 'blocked' row - "
            f"a report can never be observed half-built, got '{status}'"
        )

    columns: dict[str, Any] = {
        "id": fields.get("id") or new_report_id(),
        "raw_prompt": fields["raw_prompt"],
        "intent_json": _encode(fields.get("intent")),
        "intent_source": fields["intent_source"],
        "status": status,
        "blockers_json": _encode(fields.get("blockers", [])),
        "warnings_json": _encode(fields.get("warnings", [])),
        "routing_json": _encode(fields.get("routing")),
        "agents_json": _encode(fields.get("agents", [])),
        "active_departments": _encode(fields.get("active_departments", [])),
        "skipped_departments": _encode(fields.get("skipped_departments", [])),
        "estimated_agent_calls": fields.get("estimated_agent_calls", 0),
        "estimated_max_completion_tokens": fields.get(
            "estimated_max_completion_tokens", 0
        ),
        "created_at": fields.get("created_at") or _now(),
    }

    placeholders = ", ".join("?" for _ in columns)
    with connection() as conn:
        conn.execute(
            f"INSERT INTO planning_reports ({', '.join(columns)}) "  # noqa: S608 - keys whitelisted
            f"VALUES ({placeholders})",
            tuple(columns.values()),
        )
        row = conn.execute(
            "SELECT * FROM planning_reports WHERE id = ?", (columns["id"],)
        ).fetchone()
    return _decode_report(row)


def get_report(report_id: str, *, ttl_hours: float = 24.0) -> dict | None:
    """Full stored report, or None if unknown. A 'ready' row past its TTL
    reads as 'expired'."""
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM planning_reports WHERE id = ?", (report_id,)
        ).fetchone()
    if row is None:
        return None
    record = _decode_report(row)
    record["status"] = effective_status(record, ttl_hours=ttl_hours)
    return record


def list_reports(limit: int = 50, offset: int = 0, *, ttl_hours: float = 24.0) -> list[dict]:
    """Summary rows only (design.md §8): id, status, prompt, created_at,
    agent count - never the full payload."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, raw_prompt, status, agents_json, created_at "
            "FROM planning_reports ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    summaries: list[dict] = []
    for row in rows:
        agents = json.loads(row["agents_json"]) if row["agents_json"] else []
        summaries.append(
            {
                "id": row["id"],
                "prompt": row["raw_prompt"],
                "status": effective_status(
                    {"status": row["status"], "created_at": row["created_at"]},
                    ttl_hours=ttl_hours,
                ),
                "agent_count": len(agents),
                "created_at": row["created_at"],
            }
        )
    return summaries


# =============================================================================
# Status machine
# =============================================================================


def confirm_report(report_id: str, by: str = "operator", *, ttl_hours: float = 24.0) -> dict | None:
    """ready -> confirmed. Zero LLM calls: revalidation reads the stored
    verdict and the TTL only (design.md §4, §8).

    Raises `IllegalTransition` from every other status (blocked, confirmed,
    executed, expired-by-TTL). Unknown ids return None (404 at the route).
    """
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM planning_reports WHERE id = ?", (report_id,)
        ).fetchone()
        if row is None:
            return None
        record = _decode_report(row)
        status = effective_status(record, ttl_hours=ttl_hours)
        if status != "ready":
            raise IllegalTransition(
                f"report '{report_id}' cannot be confirmed from status "
                f"'{status}' - only a ready, unexpired report can be confirmed"
            )
        conn.execute(
            "UPDATE planning_reports SET status = 'confirmed', confirmed_at = ?, "
            "confirmed_by = ? WHERE id = ?",
            (_now(), (by or "operator").strip() or "operator", report_id),
        )
        row = conn.execute(
            "SELECT * FROM planning_reports WHERE id = ?", (report_id,)
        ).fetchone()
    return _decode_report(row)


def mark_executed(report_id: str, session_id: str) -> dict | None:
    """confirmed -> executed, recording the session that ran the plan.

    Called by the run linkage when a generation completes (design.md §8).
    Raises `IllegalTransition` from any state other than 'confirmed'.
    """
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM planning_reports WHERE id = ?", (report_id,)
        ).fetchone()
        if row is None:
            return None
        record = _decode_report(row)
        if record["status"] != "confirmed":
            raise IllegalTransition(
                f"report '{report_id}' cannot be executed from status "
                f"'{record['status']}' - only a confirmed report can run"
            )
        conn.execute(
            "UPDATE planning_reports SET status = 'executed', executed_at = ?, "
            "executed_session_id = ? WHERE id = ?",
            (_now(), session_id, report_id),
        )
        row = conn.execute(
            "SELECT * FROM planning_reports WHERE id = ?", (report_id,)
        ).fetchone()
    return _decode_report(row)


# =============================================================================
# Encoding
# =============================================================================


def _encode(value: Any) -> str | None:
    """dict/list values are JSON-encoded automatically (update_session pattern)."""
    return json.dumps(value) if isinstance(value, (dict, list)) else value


def _decode_report(row: sqlite3.Row) -> dict:
    """JSON columns decode to dicts/lists with None/[] defaults, following
    `_decode_session` (phases.md Phase 1)."""
    record = dict(row)
    for field in ("intent_json", "routing_json"):
        raw = record.pop(field)
        record[field.removesuffix("_json")] = json.loads(raw) if raw else None
    for field in ("agents_json", "blockers_json", "warnings_json"):
        raw = record.pop(field)
        record[field.removesuffix("_json")] = json.loads(raw) if raw else []
    for field in ("active_departments", "skipped_departments"):
        raw = record.get(field)
        record[field] = json.loads(raw) if raw else []
    return record
