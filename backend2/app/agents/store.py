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
                department_id, model, temperature, memory_enabled, memory_ttl_days,
                permissions, status, version, created_by, created_at, updated_at,
                origin, source_mission_id, role_title)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
                fields.get("memory_ttl_days", 30),
                json.dumps(fields.get("permissions", {})),
                fields.get("status", "active"),
                fields.get("version", "v1.0.0"),
                fields.get("created_by", "default-user"),
                now,
                now,
                fields.get("origin", "reusable"),
                fields.get("source_mission_id"),
                fields.get("role_title"),
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



# ============================================================================
# Phase 2 — full CRUD, versioning, stats, templates.
# ============================================================================

_UPDATABLE = {
    "name", "purpose", "system_prompt", "agent_type", "tools", "sub_agents",
    "department_id", "model", "temperature", "memory_enabled", "memory_ttl_days",
    "permissions", "status", "origin", "source_mission_id", "role_title",
}
_UPDATE_JSON = {"tools", "sub_agents", "permissions"}


def _bump_version(version: str | None) -> str:
    """v1.2.3 -> v1.2.4 (patch bump). Non-conforming -> v1.0.1."""
    import re

    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", version or "")
    if not m:
        return "v1.0.1"
    major, minor, patch = (int(x) for x in m.groups())
    return f"v{major}.{minor}.{patch + 1}"


def _snapshot_version(conn, agent: dict, note: str = "") -> None:
    conn.execute(
        """INSERT INTO agent_versions (id, agent_id, version, config, note, created_by, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (uuid.uuid4().hex, agent["id"], agent.get("version", "v1.0.0"),
         json.dumps(agent, default=str), note, agent.get("created_by", "default-user"), _now()),
    )


def update_agent(agent_id: str, changes: dict, *, note: str = "") -> dict | None:
    """Update fields and snapshot the PREVIOUS config into agent_versions."""
    current = get_agent(agent_id)
    if current is None:
        return None
    with connection() as conn:
        _snapshot_version(conn, current, note=note or "pre-update snapshot")
        sets, params = [], []
        for k, v in changes.items():
            if k not in _UPDATABLE:
                continue
            sets.append(f"{k} = ?")
            if k in _UPDATE_JSON:
                params.append(json.dumps(v))
            elif k == "memory_enabled":
                params.append(1 if v else 0)
            else:
                params.append(v)
        new_version = _bump_version(current.get("version"))
        sets.append("version = ?"); params.append(new_version)
        sets.append("updated_at = ?"); params.append(_now())
        params.append(agent_id)
        conn.execute(f"UPDATE agents SET {', '.join(sets)} WHERE id = ?", params)
    return get_agent(agent_id)


def delete_agent(agent_id: str) -> bool:
    """Soft delete — status = 'deleted'. Keeps traces + versions intact."""
    with connection() as conn:
        cur = conn.execute(
            "UPDATE agents SET status = 'deleted', updated_at = ? WHERE id = ?", (_now(), agent_id)
        )
    return cur.rowcount > 0


def clone_agent(agent_id: str, *, new_name: str | None = None, created_by: str = "default-user") -> str | None:
    src = get_agent(agent_id)
    if src is None:
        return None
    return create_agent(
        name=new_name or f"{src['name']} (copy)",
        purpose=src.get("purpose", ""),
        system_prompt=src["system_prompt"],
        agent_type=src["agent_type"],
        tools=src.get("tools", []),
        sub_agents=src.get("sub_agents", []),
        department_id=src.get("department_id"),
        model=src.get("model"),
        temperature=src.get("temperature", 0.7),
        memory_enabled=bool(src.get("memory_enabled")),
        memory_ttl_days=src.get("memory_ttl_days", 30),
        permissions=src.get("permissions", {}),
        status="active",
        created_by=created_by,
    )


def get_versions(agent_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, version, note, created_by, created_at FROM agent_versions "
            "WHERE agent_id = ? ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def _stats_for(conn, agent_id: str) -> dict:
    row = conn.execute(
        """SELECT
             COUNT(DISTINCT mission_id)                                  AS runs,
             COUNT(*)                                                    AS trace_count,
             SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)                AS ok_count,
             AVG(latency_ms)                                             AS avg_latency,
             SUM(COALESCE(input_tokens,0) + COALESCE(output_tokens,0))   AS tokens,
             SUM(COALESCE(cost_usd,0))                                   AS cost,
             MAX(created_at)                                             AS last_active
           FROM execution_traces WHERE agent_id = ?""",
        (agent_id,),
    ).fetchone()
    traces = row["trace_count"] or 0
    ok_count = row["ok_count"] or 0
    return {
        "runs": row["runs"] or 0,
        "success_rate": round(ok_count / traces, 4) if traces else None,
        "avg_latency_ms": round(row["avg_latency"], 1) if row["avg_latency"] is not None else None,
        "total_tokens": row["tokens"] or 0,
        "estimated_cost_usd": round(row["cost"] or 0.0, 6),
        "last_active": row["last_active"],
        "trace_count": traces,
    }


def list_agents_with_stats(*, status: str = "active", agent_type: str | None = None,
                           department_id: str | None = None) -> list[dict]:
    q = "SELECT * FROM agents WHERE status = ?"
    params: list = [status]
    if agent_type:
        q += " AND agent_type = ?"; params.append(agent_type)
    if department_id:
        q += " AND department_id = ?"; params.append(department_id)
    q += " ORDER BY created_at DESC"
    with connection() as conn:
        rows = conn.execute(q, params).fetchall()
        agents = []
        for r in rows:
            a = _decode(r)
            a["stats"] = _stats_for(conn, a["id"])
            agents.append(a)
    return agents


def performance(agent_id: str) -> dict | None:
    agent = get_agent(agent_id)
    if agent is None:
        return None
    with connection() as conn:
        base = _stats_for(conn, agent_id)
        error_count = conn.execute(
            "SELECT COUNT(*) AS c FROM execution_traces WHERE agent_id = ? AND success = 0", (agent_id,)
        ).fetchone()["c"]
        tool_rows = conn.execute(
            """SELECT tool_name, COUNT(*) AS n FROM execution_traces
               WHERE agent_id = ? AND trace_type='tool' AND tool_name IS NOT NULL
               GROUP BY tool_name ORDER BY n DESC""",
            (agent_id,),
        ).fetchall()
        recent = conn.execute(
            """SELECT mission_id, trace_type, provider, model, tool_name, latency_ms, success, created_at
               FROM execution_traces WHERE agent_id = ? ORDER BY created_at DESC LIMIT 20""",
            (agent_id,),
        ).fetchall()
    base["error_count"] = error_count
    base["error_rate"] = round(error_count / base["trace_count"], 4) if base["trace_count"] else None
    base["tool_usage"] = [{"tool": r["tool_name"], "count": r["n"]} for r in tool_rows]
    base["recent_runs"] = [dict(r) for r in recent]
    return {"agent": {"id": agent["id"], "name": agent["name"], "agent_type": agent["agent_type"]}, **base}


# ---- Templates --------------------------------------------------------------

def create_template(**fields) -> str:
    tid = fields.get("id") or uuid.uuid4().hex[:12]
    with connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO agent_templates
               (id, name, description, category, base_config, tags, is_featured, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (tid, fields["name"], fields.get("description", ""), fields.get("category", ""),
             json.dumps(fields.get("base_config", {})), json.dumps(fields.get("tags", [])),
             1 if fields.get("is_featured") else 0, _now()),
        )
    return tid


def list_templates() -> list[dict]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM agent_templates ORDER BY is_featured DESC, name").fetchall()
    out = []
    for r in rows:
        rec = dict(r)
        rec["base_config"] = json.loads(rec["base_config"]) if rec.get("base_config") else {}
        rec["tags"] = json.loads(rec["tags"]) if rec.get("tags") else []
        rec["is_featured"] = bool(rec["is_featured"])
        out.append(rec)
    return out


def get_template(template_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM agent_templates WHERE id = ?", (template_id,)).fetchone()
    if not row:
        return None
    rec = dict(row)
    rec["base_config"] = json.loads(rec["base_config"]) if rec.get("base_config") else {}
    rec["tags"] = json.loads(rec["tags"]) if rec.get("tags") else []
    rec["is_featured"] = bool(rec["is_featured"])
    return rec


def create_from_template(template_id: str, *, name: str | None = None,
                         created_by: str = "default-user") -> str | None:
    tpl = get_template(template_id)
    if tpl is None:
        return None
    cfg = tpl["base_config"] or {}
    return create_agent(
        name=name or cfg.get("name") or tpl["name"],
        purpose=cfg.get("purpose", tpl.get("description", "")),
        system_prompt=cfg.get("system_prompt", f"You are a {tpl['name']}."),
        agent_type=cfg.get("agent_type", "general"),
        tools=cfg.get("tools", []),
        sub_agents=cfg.get("sub_agents", []),
        department_id=cfg.get("department_id"),
        model=cfg.get("model"),
        temperature=cfg.get("temperature", 0.7),
        memory_enabled=bool(cfg.get("memory_enabled", True)),
        memory_ttl_days=cfg.get("memory_ttl_days", 30),
        permissions=cfg.get("permissions", {}),
        created_by=created_by,
    )
