"""Agents store — CRUD over MongoDB agents collection.

Phase 1 uses this read-heavy: the Router queries by type, the Executor loads one
by id. Full user-facing CRUD endpoints arrive in Phase 2.
"""

from __future__ import annotations

import json
import uuid

from app.auth import store as auth_store

_JSON_FIELDS = ("tools", "sub_agents", "permissions")


def _decode(doc: dict) -> dict:
    """Convert MongoDB doc to agent dict."""
    rec = dict(doc)
    rec["id"] = rec.pop("_id")
    for f in _JSON_FIELDS:
        rec[f] = rec.get(f) or ([] if f != "permissions" else {})
    return rec


def create_agent(**fields) -> str:
    """Create an agent in MongoDB."""
    agent_id = fields.get("id") or uuid.uuid4().hex[:12]
    auth_store.create_agent(
        agent_id=agent_id,
        name=fields["name"],
        system_prompt=fields["system_prompt"],
        agent_type=fields["agent_type"],
        model=fields.get("model", "groq:llama-3.1-8b-instant"),
        temperature=fields.get("temperature", 0.7),
        tools=fields.get("tools", []),
        sub_agents=fields.get("sub_agents", []),
        department_id=fields.get("department_id"),
        created_by=fields.get("created_by", "default-user"),
        origin=fields.get("origin", "reusable"),
        role_title=fields.get("role_title"),
    )
    return agent_id


def get_agent(agent_id: str) -> dict | None:
    """Get an agent from MongoDB."""
    doc = auth_store.get_agent(agent_id)
    return _decode(doc) if doc else None


def list_agents(status: str = "active") -> list[dict]:
    """List agents from MongoDB."""
    agents = auth_store.list_agents(status=status)
    return [_decode(a) for a in agents]


def find_agents_by_type(agent_type: str, user_id: str, department_id: str | None) -> list[dict]:
    """Router query. Prefers the user's own agents in the given department."""
    agents = auth_store.list_agents(agent_type=agent_type, created_by=user_id, status="active")
    # Also get system agents
    system_agents = auth_store.list_agents(agent_type=agent_type, created_by="system", status="active")
    all_agents = agents + system_agents
    
    # Decode MongoDB docs to agent dicts (converts _id to id)
    decoded = [_decode(a) for a in all_agents]
    
    # Sort: user agents first, then by department match, then by created_at
    def sort_key(a):
        is_user = a.get("created_by") == user_id
        dept_match = a.get("department_id") == department_id
        return (not is_user, not dept_match, a.get("created_at", ""))
    
    return sorted(decoded, key=sort_key)


def get_system_default(agent_type: str) -> dict | None:
    """Get system default agent from MongoDB."""
    agents = auth_store.list_agents(agent_type=agent_type, created_by="system", status="active")
    if agents:
        return _decode(agents[0])
    # Last-resort: any 'general' system agent.
    general = auth_store.list_agents(agent_type="general", created_by="system", status="active")
    return _decode(general[0]) if general else None



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


def _snapshot_version(agent: dict, note: str = "") -> None:
    """Snapshot agent config into agent_versions in MongoDB."""
    version_id = uuid.uuid4().hex
    auth_store.create_agent_version(
        version_id=version_id,
        agent_id=agent["id"],
        version=agent.get("version", "v1.0.0"),
        config=agent,
        note=note or "pre-update snapshot",
        created_by=agent.get("created_by", "default-user")
    )


def update_agent(agent_id: str, changes: dict, *, note: str = "") -> dict | None:
    """Update fields and snapshot the PREVIOUS config into agent_versions."""
    current = get_agent(agent_id)
    if current is None:
        return None
    _snapshot_version(current, note=note or "pre-update snapshot")
    
    # Prepare update data
    update_data = {}
    for k, v in changes.items():
        if k not in _UPDATABLE:
            continue
        if k in _UPDATE_JSON:
            update_data[k] = json.dumps(v)
        elif k == "memory_enabled":
            update_data[k] = 1 if v else 0
        else:
            update_data[k] = v
    
    new_version = _bump_version(current.get("version"))
    update_data["version"] = new_version
    
    auth_store.update_agent(agent_id, **update_data)
    return get_agent(agent_id)


def delete_agent(agent_id: str) -> bool:
    """Soft delete — status = 'deleted'. Keeps traces + versions intact."""
    auth_store.update_agent(agent_id, status="deleted")
    return True


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
        id=None,  # Force new ID
    )


def get_versions(agent_id: str) -> list[dict]:
    """Get agent versions from MongoDB."""
    versions = auth_store.list_agent_versions(agent_id)
    return [dict(v) for v in versions]


def _stats_for(agent_id: str) -> dict:
    """Get stats for an agent from MongoDB execution traces using aggregation."""
    db = auth_store.get_db()
    
    # Use aggregation to calculate stats in a single query
    pipeline = [
        {"$match": {"agent_id": agent_id}},
        {
            "$group": {
                "_id": "$agent_id",
                "trace_count": {"$sum": 1},
                "ok_count": {"$sum": {"$cond": [{"$eq": ["$success", 1]}, 1, 0]}},
                "total_latency": {"$sum": "$latency_ms"},
                "total_tokens": {"$sum": {"$add": ["$input_tokens", "$output_tokens"]}},
                "total_cost": {"$sum": "$cost_usd"},
                "last_active": {"$max": "$created_at"},
                "mission_ids": {"$addToSet": "$mission_id"}
            }
        }
    ]
    
    result = list(db.execution_traces.aggregate(pipeline))
    
    if not result:
        return {
            "runs": 0,
            "success_rate": None,
            "avg_latency_ms": None,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "last_active": None,
            "trace_count": 0,
        }
    
    stats = result[0]
    traces_count = stats["trace_count"]
    ok_count = stats["ok_count"]
    total_latency = stats["total_latency"] or 0
    
    return {
        "runs": len(stats["mission_ids"]),
        "success_rate": round(ok_count / traces_count, 4) if traces_count else None,
        "avg_latency_ms": round(total_latency / traces_count, 1) if traces_count else None,
        "total_tokens": stats["total_tokens"] or 0,
        "estimated_cost_usd": round(stats["total_cost"] or 0, 6),
        "last_active": stats["last_active"],
        "trace_count": traces_count,
    }


def list_agents_with_stats(*, status: str = "active", agent_type: str | None = None,
                           department_id: str | None = None) -> list[dict]:
    """List agents with batch-optimized stats from MongoDB."""
    agents = auth_store.list_agents(agent_type=agent_type, status=status)
    
    # Collect all agent IDs
    agent_ids = [a.get("_id") for a in agents]
    
    # Batch calculate stats for all agents in a single aggregation query
    db = auth_store.get_db()
    pipeline = [
        {"$match": {"agent_id": {"$in": agent_ids}}},
        {
            "$group": {
                "_id": "$agent_id",
                "trace_count": {"$sum": 1},
                "ok_count": {"$sum": {"$cond": [{"$eq": ["$success", 1]}, 1, 0]}},
                "total_latency": {"$sum": "$latency_ms"},
                "total_tokens": {"$sum": {"$add": ["$input_tokens", "$output_tokens"]}},
                "total_cost": {"$sum": "$cost_usd"},
                "last_active": {"$max": "$created_at"},
                "mission_ids": {"$addToSet": "$mission_id"}
            }
        }
    ]
    
    stats_by_agent = {}
    for result in db.execution_traces.aggregate(pipeline):
        agent_id = result["_id"]
        traces_count = result["trace_count"]
        stats_by_agent[agent_id] = {
            "runs": len(result["mission_ids"]),
            "success_rate": round(result["ok_count"] / traces_count, 4) if traces_count else None,
            "avg_latency_ms": round((result["total_latency"] or 0) / traces_count, 1) if traces_count else None,
            "total_tokens": result["total_tokens"] or 0,
            "estimated_cost_usd": round(result["total_cost"] or 0, 6),
            "last_active": result["last_active"],
            "trace_count": traces_count,
        }
    
    # Assign stats to each agent
    out = []
    for a in agents:
        decoded = _decode(a)
        decoded["stats"] = stats_by_agent.get(decoded["id"], {
            "runs": 0,
            "success_rate": None,
            "avg_latency_ms": None,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "last_active": None,
            "trace_count": 0,
        })
        out.append(decoded)
    return out


def performance(agent_id: str) -> dict | None:
    """Get performance stats for an agent from MongoDB using aggregations."""
    agent = get_agent(agent_id)
    if agent is None:
        return None
    base = _stats_for(agent_id)
    
    db = auth_store.get_db()
    
    # Batch get error count and tool usage in aggregations
    pipeline = [
        {"$match": {"agent_id": agent_id}},
        {
            "$group": {
                "_id": "$agent_id",
                "error_count": {"$sum": {"$cond": [{"$eq": ["$success", 0]}, 1, 0]}},
                "tools": {"$push": {"$cond": [{"$eq": ["$trace_type", "tool"]}, "$tool_name", None]}}
            }
        }
    ]
    
    result = list(db.execution_traces.aggregate(pipeline))
    if result:
        stats = result[0]
        base["error_count"] = stats["error_count"]
        base["error_rate"] = round(stats["error_count"] / base["trace_count"], 4) if base["trace_count"] else None
        
        # Calculate tool usage from aggregated tools array
        tool_usage = {}
        for tool_name in stats["tools"]:
            if tool_name:
                tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
        base["tool_usage"] = [{"tool": k, "count": v} for k, v in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)]
    else:
        base["error_count"] = 0
        base["error_rate"] = None
        base["tool_usage"] = []
    
    # Get recent runs (limit to 20, sorted by created_at desc)
    recent = list(db.execution_traces.find(
        {"agent_id": agent_id},
        sort=[("created_at", -1)],
        limit=20
    ))
    base["recent_runs"] = [dict(t) for t in recent]
    
    return {"agent": {"id": agent["id"], "name": agent["name"], "agent_type": agent["agent_type"]}, **base}


# ---- Templates --------------------------------------------------------------

def create_template(**fields) -> str:
    """Create an agent template in MongoDB."""
    tid = fields.get("id") or uuid.uuid4().hex[:12]
    auth_store.create_agent_template(
        template_id=tid,
        name=fields["name"],
        description=fields.get("description", ""),
        category=fields.get("category", ""),
        base_config=fields.get("base_config", {}),
        tags=fields.get("tags", []),
        is_featured=fields.get("is_featured", False)
    )
    return tid


def list_templates() -> list[dict]:
    """List agent templates from MongoDB."""
    templates = auth_store.list_agent_templates()
    out = []
    for t in templates:
        rec = dict(t)
        rec["id"] = rec.pop("_id")
        rec["base_config"] = rec.get("base_config", {})
        rec["tags"] = rec.get("tags", [])
        rec["is_featured"] = bool(rec.get("is_featured"))
        out.append(rec)
    return out


def get_template(template_id: str) -> dict | None:
    """Get an agent template from MongoDB."""
    doc = auth_store.get_agent_template(template_id)
    if not doc:
        return None
    rec = dict(doc)
    rec["id"] = rec.pop("_id")
    rec["base_config"] = rec.get("base_config", {})
    rec["tags"] = rec.get("tags", [])
    rec["is_featured"] = bool(rec.get("is_featured"))
    return rec


def create_from_template(template_id: str, *, name: str | None = None,
                         created_by: str = "default-user") -> str | None:
    """Create an agent from a template."""
    tpl = get_template(template_id)
    if tpl is None:
        return None
    cfg = tpl.get("base_config", {})
    return create_agent(
        name=name or cfg.get("name") or tpl.get("name"),
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
