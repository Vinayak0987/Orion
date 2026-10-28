"""Scheduled missions — recurring department tasks (cron-ish).

A schedule stores a prompt + department + cadence (interval/daily/weekly) and a
next_run time. A background loop wakes periodically, finds due schedules, fires
a real mission (via the mission engine) for each, and advances next_run. Kept
lean: no external cron dependency.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

from app.db.sqlite import _now, connection


def _ensure_table() -> None:
    with connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS scheduled_missions (
                   id TEXT PRIMARY KEY,
                   prompt TEXT NOT NULL,
                   department_id TEXT,
                   mode TEXT NOT NULL DEFAULT 'planning',
                   cadence TEXT NOT NULL DEFAULT 'daily',   -- interval | daily | weekly
                   interval_minutes INTEGER NOT NULL DEFAULT 1440,
                   enabled INTEGER NOT NULL DEFAULT 1,
                   next_run TEXT NOT NULL,
                   last_run TEXT,
                   last_mission_id TEXT,
                   created_by TEXT NOT NULL,
                   created_at TEXT NOT NULL
               )"""
        )


def _parse(dt: str) -> datetime:
    return datetime.fromisoformat(dt)


def _next_from(cadence: str, interval_minutes: int, base: datetime | None = None) -> str:
    base = base or datetime.now(UTC)
    if cadence == "interval":
        return (base + timedelta(minutes=max(1, interval_minutes))).isoformat()
    if cadence == "weekly":
        return (base + timedelta(days=7)).isoformat()
    return (base + timedelta(days=1)).isoformat()  # daily default


def create_schedule(*, prompt: str, created_by: str, department_id: str | None = None,
                    mode: str = "planning", cadence: str = "daily",
                    interval_minutes: int = 1440, first_run_in_minutes: int = 0) -> str:
    _ensure_table()
    sid = uuid.uuid4().hex[:12]
    first = (datetime.now(UTC) + timedelta(minutes=max(0, first_run_in_minutes))).isoformat()
    with connection() as conn:
        conn.execute(
            """INSERT INTO scheduled_missions
               (id, prompt, department_id, mode, cadence, interval_minutes, enabled,
                next_run, created_by, created_at)
               VALUES (?,?,?,?,?,?,1,?,?,?)""",
            (sid, prompt, department_id, mode, cadence, interval_minutes, first, created_by, _now()),
        )
    return sid


def list_schedules(*, created_by: str | None = None, department_id: str | None = None) -> list[dict]:
    _ensure_table()
    q = "SELECT * FROM scheduled_missions WHERE 1=1"
    params: list = []
    if created_by:
        q += " AND created_by = ?"; params.append(created_by)
    if department_id:
        q += " AND department_id = ?"; params.append(department_id)
    q += " ORDER BY created_at DESC"
    with connection() as conn:
        rows = conn.execute(q, params).fetchall()
    out = []
    for r in rows:
        d = dict(r); d["enabled"] = bool(d["enabled"]); out.append(d)
    return out


def set_enabled(schedule_id: str, enabled: bool) -> bool:
    _ensure_table()
    with connection() as conn:
        cur = conn.execute("UPDATE scheduled_missions SET enabled=? WHERE id=?",
                           (1 if enabled else 0, schedule_id))
    return cur.rowcount > 0


def delete_schedule(schedule_id: str) -> bool:
    _ensure_table()
    with connection() as conn:
        cur = conn.execute("DELETE FROM scheduled_missions WHERE id=?", (schedule_id,))
    return cur.rowcount > 0


def _due() -> list[dict]:
    now = datetime.now(UTC).isoformat()
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM scheduled_missions WHERE enabled=1 AND next_run <= ?", (now,)
        ).fetchall()
    return [dict(r) for r in rows]


def _advance(schedule_id: str, cadence: str, interval_minutes: int, mission_id: str) -> None:
    nxt = _next_from(cadence, interval_minutes)
    with connection() as conn:
        conn.execute("UPDATE scheduled_missions SET last_run=?, last_mission_id=?, next_run=? WHERE id=?",
                     (_now(), mission_id, nxt, schedule_id))


async def _tick() -> int:
    """Fire all due schedules once. Returns how many fired."""
    from app.missions import engine, store
    fired = 0
    for s in _due():
        try:
            mid = store.create_mission(s["prompt"], s["created_by"], s.get("department_id"),
                                       None, mode=s.get("mode", "planning"))
            asyncio.create_task(engine.run_mission(mid, skip_clarify=True))
            _advance(s["id"], s["cadence"], s["interval_minutes"], mid)
            fired += 1
        except Exception:  # noqa: BLE001 — one bad schedule must not stop others
            continue
    return fired


async def run_scheduler(poll_seconds: int = 30) -> None:
    """Background loop: every poll_seconds, fire due schedules. Never raises."""
    _ensure_table()
    while True:
        try:
            await _tick()
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(poll_seconds)
