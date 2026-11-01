"""Scheduled missions — recurring department tasks (cron-ish).

A schedule stores a prompt + department + cadence (interval/daily/weekly) and a
next_run time. A background loop wakes periodically, finds due schedules, fires
a real mission (via the mission engine) for each, and advances next_run. Kept
lean: no external cron dependency.

Now uses MongoDB instead of SQLite.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

from app.auth import store as auth_store


def _now() -> datetime:
    return auth_store._now()


def _ensure_table() -> None:
    # No-op - MongoDB creates collections automatically
    pass


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
    sid = uuid.uuid4().hex[:12]
    first = (datetime.now(UTC) + timedelta(minutes=max(0, first_run_in_minutes))).isoformat()
    auth_store.create_scheduled_mission(
        schedule_id=sid,
        prompt=prompt,
        department_id=department_id,
        mode=mode,
        cadence=cadence,
        interval_minutes=interval_minutes,
        enabled=True,
        next_run=first,
    )
    return sid


def list_schedules(*, created_by: str | None = None, department_id: str | None = None) -> list[dict]:
    # MongoDB doesn't filter by created_by in the basic list, add if needed
    schedules = auth_store.list_scheduled_missions()
    if created_by:
        schedules = [s for s in schedules if s.get("created_by") == created_by]
    if department_id:
        schedules = [s for s in schedules if s.get("department_id") == department_id]
    return schedules


def set_enabled(schedule_id: str, enabled: bool) -> bool:
    auth_store.update_scheduled_mission(schedule_id, enabled=enabled)
    return True


def delete_schedule(schedule_id: str) -> bool:
    return auth_store.delete_scheduled_mission(schedule_id)


def _due() -> list[dict]:
    now = datetime.now(UTC).isoformat()
    schedules = auth_store.list_scheduled_missions(enabled_only=True)
    return [s for s in schedules if s.get("next_run") and s["next_run"] <= now]


def _advance(schedule_id: str, cadence: str, interval_minutes: int, mission_id: str) -> None:
    nxt = _next_from(cadence, interval_minutes)
    auth_store.update_scheduled_mission(
        schedule_id,
        last_run=_now().isoformat(),
        last_mission_id=mission_id,
        next_run=nxt,
    )


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
