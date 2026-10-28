"""Missions + mission_tasks store."""

from __future__ import annotations

import json
import uuid

from app.db.sqlite import _now, connection


def _decode_mission(row) -> dict:
    return dict(row)


def _decode_task(row) -> dict:
    rec = dict(row)
    for f in ("tools_needed", "depends_on"):
        rec[f] = json.loads(rec[f]) if rec.get(f) else []
    rec["result"] = json.loads(rec["result"]) if rec.get("result") else None
    return rec


# --- missions ----------------------------------------------------------------

def create_mission(prompt: str, created_by: str = "default-user",
                   department_id: str | None = None,
                   conversation_id: str | None = None,
                   mode: str = "action") -> str:
    mission_id = uuid.uuid4().hex[:12]
    mode = mode if mode in ("planning", "action") else "action"
    with connection() as conn:
        conn.execute(
            "INSERT INTO missions (id, prompt, status, department_id, conversation_id, mode, created_by, created_at) "
            "VALUES (?, ?, 'planning', ?, ?, ?, ?, ?)",
            (mission_id, prompt, department_id, conversation_id, mode, created_by, _now()),
        )
    return mission_id


def set_mission(mission_id: str, **fields) -> None:
    allowed = {"title", "status", "completed_at", "department_id"}
    bad = fields.keys() - allowed
    if bad:
        raise ValueError(f"Unknown mission column(s): {bad}")
    assignments = ", ".join(f"{k} = ?" for k in fields)
    with connection() as conn:
        conn.execute(
            f"UPDATE missions SET {assignments} WHERE id = ?",  # noqa: S608 - whitelisted
            (*fields.values(), mission_id),
        )


def get_mission(mission_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
    if row is None:
        return None
    mission = _decode_mission(row)
    mission["tasks"] = list_tasks(mission_id)
    return mission


def list_missions(limit: int = 50, offset: int = 0, status: str | None = None,
                  created_by: str = "default-user", search: str | None = None,
                  mtype: str | None = None) -> list[dict]:
    q = "SELECT * FROM missions WHERE created_by = ?"
    params: list = [created_by]
    if status:
        q += " AND status = ?"
        params.append(status)
    if search:
        q += " AND (LOWER(prompt) LIKE ? OR LOWER(COALESCE(title,'')) LIKE ?)"
        like = f"%{search.lower()}%"
        params += [like, like]
    q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with connection() as conn:
        rows = conn.execute(q, params).fetchall()
    out = []
    for r in rows:
        m = _decode_mission(r)
        with connection() as conn:
            counts = conn.execute(
                "SELECT COUNT(*) AS tasks, COUNT(DISTINCT agent_id) AS agents "
                "FROM mission_tasks WHERE mission_id = ?",
                (m["id"],),
            ).fetchone()
            trows = conn.execute(
                "SELECT agent_type, agent_id, status FROM mission_tasks WHERE mission_id = ?",
                (m["id"],),
            ).fetchall()
        m["task_count"] = counts["tasks"]
        m["agent_count"] = counts["agents"]
        types = [t["agent_type"] for t in trows]
        m["type"] = _classify_type(types)
        m["agent_ids"] = sorted({t["agent_id"] for t in trows if t["agent_id"]})
        done = sum(1 for t in trows if t["status"] in ("completed", "failed", "stopped"))
        m["progress"] = round(100 * done / len(trows)) if trows else 0
        out.append(m)
    if mtype:
        out = [m for m in out if m["type"].lower() == mtype.lower()]
    return out


def _classify_type(types: list[str]) -> str:
    """Derive a mission 'type' from its task agent_types (Plan 14)."""
    if not types:
        return "Planning"
    s = set(types)
    if {"analysis", "writing", "finance"} & s and "research" not in s:
        return "Planning"
    if "operations" in s or "hr" in s:
        return "Operations"
    research = sum(1 for t in types if t == "research")
    if research >= len(types) / 2:
        return "Research"
    if {"analysis", "writing", "finance"} & s:
        return "Planning"
    return "Research" if research else "Planning"


def delete_mission(mission_id: str) -> bool:
    with connection() as conn:
        conn.execute("DELETE FROM mission_tasks WHERE mission_id = ?", (mission_id,))
        cur = conn.execute("DELETE FROM missions WHERE id = ?", (mission_id,))
    return cur.rowcount > 0


# --- tasks -------------------------------------------------------------------

def save_tasks(mission_id: str, tasks: list[dict]) -> list[dict]:
    """Insert planner tasks. Returns them with assigned ids."""
    saved = []
    with connection() as conn:
        for t in tasks:
            task_id = uuid.uuid4().hex[:12]
            conn.execute(
                "INSERT INTO mission_tasks "
                "(id, mission_id, title, agent_type, tools_needed, depends_on, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
                (
                    task_id, mission_id, t["title"], t["agent_type"],
                    json.dumps(t.get("tools_needed", [])),
                    json.dumps(t.get("depends_on", [])),
                    _now(),
                ),
            )
            saved.append({**t, "id": task_id, "mission_id": mission_id, "status": "pending"})
    return saved


def set_task(task_id: str, **fields) -> None:
    allowed = {"agent_id", "status", "result", "completed_at"}
    bad = fields.keys() - allowed
    if bad:
        raise ValueError(f"Unknown task column(s): {bad}")
    enc = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in fields.items()}
    assignments = ", ".join(f"{k} = ?" for k in enc)
    with connection() as conn:
        conn.execute(
            f"UPDATE mission_tasks SET {assignments} WHERE id = ?",  # noqa: S608 - whitelisted
            (*enc.values(), task_id),
        )


def list_tasks(mission_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM mission_tasks WHERE mission_id = ? ORDER BY created_at", (mission_id,)
        ).fetchall()
    return [_decode_task(r) for r in rows]
