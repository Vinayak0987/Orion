"""Tools table store — the DB-backed source of truth for the registry.

`name` is the stable key stored in agents.tools[] and dispatched by the executor
(NOT a UUID), keeping the existing engine + seeded agents working unchanged.
"""

from __future__ import annotations

import json
import uuid

from app.db.sqlite import _now, connection

_JSON = ("input_schema", "config")


def _decode(row) -> dict:
    rec = dict(row)
    for f in _JSON:
        rec[f] = json.loads(rec[f]) if rec.get(f) else {}
    rec["enabled"] = bool(rec.get("enabled"))
    rec["degraded"] = bool(rec.get("degraded"))
    return rec


def upsert_tool(*, name: str, display_name: str, description: str, type: str = "builtin",
                category: str = "utility", input_schema: dict | None = None, config: dict | None = None,
                enabled: bool = True, requires_key: str | None = None, degraded: bool = False) -> str:
    now = _now()
    with connection() as conn:
        existing = conn.execute("SELECT id, enabled FROM tools WHERE name = ?", (name,)).fetchone()
        tool_id = existing["id"] if existing else uuid.uuid4().hex
        # Preserve a user's enable/disable choice on re-seed.
        enabled_val = existing["enabled"] if existing else (1 if enabled else 0)
        conn.execute(
            """INSERT INTO tools
               (id, name, display_name, description, type, category, input_schema, config,
                enabled, requires_key, degraded, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(name) DO UPDATE SET
                 display_name=excluded.display_name, description=excluded.description,
                 type=excluded.type, category=excluded.category, input_schema=excluded.input_schema,
                 config=excluded.config, requires_key=excluded.requires_key,
                 degraded=excluded.degraded, updated_at=excluded.updated_at""",
            (tool_id, name, display_name, description, type, category,
             json.dumps(input_schema or {}), json.dumps(config or {}),
             enabled_val, requires_key, 1 if degraded else 0, now, now),
        )
    return tool_id


def get_tool(name: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM tools WHERE name = ?", (name,)).fetchone()
    return _decode(row) if row else None


def get_tool_by_id(tool_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
    return _decode(row) if row else None


def list_tools(*, type: str | None = None, category: str | None = None,
               enabled: bool | None = None, search: str | None = None) -> list[dict]:
    q = "SELECT * FROM tools WHERE 1=1"
    params: list = []
    if type:
        q += " AND type = ?"; params.append(type)
    if category:
        q += " AND category = ?"; params.append(category)
    if enabled is not None:
        q += " AND enabled = ?"; params.append(1 if enabled else 0)
    if search:
        q += " AND (name LIKE ? OR display_name LIKE ? OR description LIKE ?)"
        params += [f"%{search}%"] * 3
    q += " ORDER BY category, name"
    with connection() as conn:
        rows = conn.execute(q, params).fetchall()
    tools = [_decode(r) for r in rows]
    _attach_last_used(tools)
    return tools


def _attach_last_used(tools: list[dict]) -> None:
    """Compute last_used + usage_count from execution_traces (by tool_name)."""
    if not tools:
        return
    with connection() as conn:
        rows = conn.execute(
            """SELECT tool_name, MAX(created_at) AS last_used, COUNT(*) AS n
               FROM execution_traces WHERE trace_type='tool' GROUP BY tool_name"""
        ).fetchall()
    stats = {r["tool_name"]: (r["last_used"], r["n"]) for r in rows}
    for t in tools:
        lu, n = stats.get(t["name"], (None, 0))
        t["last_used"], t["usage_count"] = lu, n


def set_enabled(name: str, enabled: bool) -> bool:
    with connection() as conn:
        cur = conn.execute("UPDATE tools SET enabled = ?, updated_at = ? WHERE name = ?",
                           (1 if enabled else 0, _now(), name))
    return cur.rowcount > 0


def delete_tool(name: str) -> bool:
    with connection() as conn:
        cur = conn.execute("DELETE FROM tools WHERE name = ?", (name,))
    return cur.rowcount > 0
