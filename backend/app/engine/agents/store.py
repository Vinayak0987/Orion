"""Agents store — CRUD over the agents table.

Phase 1 uses this read-heavy: the Router queries by type, the Executor loads one
by id. Full user-facing CRUD endpoints arrive in Phase 2.
"""

from __future__ import annotations

import json
import uuid

from app.db.sqlite import _now, connection

_JSON_FIELDS = ("tools", "sub_agents", "permissions")


def _decode(row) -> dict:
    rec = dict(row)
    for f in _JSON_FIELDS:
        rec[f] = json.loads(rec[f]) if rec.get(f) else ([] if f != "permissions" else {})
    return rec


def create_agent(**fields) -> str:
    agent_id = fields.get("id") or uuid.uuid4().hex[:12]
    now = _now()
    with connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO agents
               (id, name, purpose, system_prompt, agent_type, tools, sub_agents,
                department_id, model, temperature, memory_enabled, permissions,
                status, created_by, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                agent_id,
                fields["name"],
                fields.get("purpose", ""),
                fields["system_prompt"],
                fields["agent_type"],
                json.dumps(fields.get("tools", [])),
                json.dumps(fields.get("sub_agents", [])),
                fields.get("department_id"),
                fields.get("model", "groq:llama-3.1-8b-instant"),
                fields.get("temperature", 0.7),
                1 if fields.get("memory_enabled") else 0,
                json.dumps(fields.get("permissions", {})),
                fields.get("status", "active"),
                fields.get("created_by", "default-user"),
                now,
                now,
            ),
        )
    return agent_id


def get_agent(agent_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return _decode(row) if row else None


def list_agents(status: str = "active") -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM agents WHERE status = ? ORDER BY created_at", (status,)
        ).fetchall()
    return [_decode(r) for r in rows]


def find_agents_by_type(agent_type: str, user_id: str, department_id: str | None) -> list[dict]:
    """Router query. Prefers the user's own agents in the given department."""
    with connection() as conn:
        rows = conn.execute(
            """SELECT * FROM agents
               WHERE agent_type = ? AND status = 'active'
                 AND (created_by = ? OR created_by = 'system')
               ORDER BY
                 (created_by = ?) DESC,
                 (department_id IS ?) DESC,
                 created_at""",
            (agent_type, user_id, user_id, department_id),
        ).fetchall()
    return [_decode(r) for r in rows]


def get_system_default(agent_type: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM agents WHERE agent_type = ? AND created_by = 'system' LIMIT 1",
            (agent_type,),
        ).fetchone()
    if row is None:
        # Last-resort: any 'general' system agent.
        with connection() as conn:
            row = conn.execute(
                "SELECT * FROM agents WHERE agent_type = 'general' AND created_by = 'system' LIMIT 1"
            ).fetchone()
    return _decode(row) if row else None
