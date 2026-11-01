"""Tools table store — the DB-backed source of truth for the registry.

`name` is the stable key stored in agents.tools[] and dispatched by the executor
(NOT a UUID), keeping the existing engine + seeded agents working unchanged.
"""

from __future__ import annotations

import uuid

from app.auth import store as auth_store


def _decode(doc: dict) -> dict:
    rec = dict(doc)
    rec["id"] = rec.pop("_id")
    rec["enabled"] = bool(rec.get("enabled"))
    rec["degraded"] = bool(rec.get("degraded"))
    return rec


def upsert_tool(*, name: str, display_name: str, description: str, type: str = "builtin",
                category: str = "utility", input_schema: dict | None = None, config: dict | None = None,
                enabled: bool = True, requires_key: str | None = None, degraded: bool = False) -> str:
    db = auth_store.get_db()
    existing = db.tools.find_one({"name": name})
    tool_id = existing["_id"] if existing else uuid.uuid4().hex
    # Preserve a user's enable/disable choice on re-seed.
    enabled_val = existing["enabled"] if existing else (1 if enabled else 0)
    
    doc = {
        "_id": tool_id,
        "name": name,
        "display_name": display_name,
        "description": description,
        "type": type,
        "category": category,
        "input_schema": input_schema or {},
        "config": config or {},
        "enabled": enabled_val,
        "requires_key": requires_key,
        "degraded": 1 if degraded else 0,
        "created_at": existing.get("created_at") if existing else auth_store._now(),
        "updated_at": auth_store._now(),
    }
    
    db.tools.update_one({"_id": tool_id}, {"$set": doc}, upsert=True)
    return tool_id


def get_tool(name: str) -> dict | None:
    db = auth_store.get_db()
    doc = db.tools.find_one({"name": name})
    return _decode(doc) if doc else None


def get_tool_by_id(tool_id: str) -> dict | None:
    db = auth_store.get_db()
    doc = db.tools.find_one({"_id": tool_id})
    return _decode(doc) if doc else None


def list_tools(*, type: str | None = None, category: str | None = None,
               enabled: bool | None = None, search: str | None = None,
               include_stats: bool = False) -> list[dict]:
    db = auth_store.get_db()
    query = {}
    if type:
        query["type"] = type
    if category:
        query["category"] = category
    if enabled is not None:
        query["enabled"] = 1 if enabled else 0
    if search:
        search_lower = search.lower()
        query["$or"] = [
            {"name": {"$regex": search_lower, "$options": "i"}},
            {"display_name": {"$regex": search_lower, "$options": "i"}},
            {"description": {"$regex": search_lower, "$options": "i"}},
        ]
    
    cursor = db.tools.find(query).sort([("category", 1), ("name", 1)])
    tools = [_decode(t) for t in cursor]
    
    # Only attach stats if explicitly requested (expensive aggregation)
    if include_stats:
        _attach_last_used(tools)
    
    return tools


def _attach_last_used(tools: list[dict]) -> None:
    """Compute last_used + usage_count from execution_traces (by tool_name)."""
    if not tools:
        return
    db = auth_store.get_db()
    
    # Get tool names we need stats for (only fetch stats for these tools)
    tool_names = [t["name"] for t in tools]
    
    # Only aggregate for the tools we're returning (much faster)
    pipeline = [
        {"$match": {"trace_type": "tool", "tool_name": {"$in": tool_names}}},
        {"$group": {"_id": "$tool_name", "last_used": {"$max": "$created_at"}, "count": {"$sum": 1}}}
    ]
    rows = list(db.execution_traces.aggregate(pipeline))
    stats = {r["_id"]: (r["last_used"], r["count"]) for r in rows}
    for t in tools:
        lu, n = stats.get(t["name"], (None, 0))
        t["last_used"], t["usage_count"] = lu, n


def set_enabled(name: str, enabled: bool) -> bool:
    db = auth_store.get_db()
    result = db.tools.update_one(
        {"name": name},
        {"$set": {"enabled": 1 if enabled else 0, "updated_at": auth_store._now()}}
    )
    return result.modified_count > 0


def delete_tool(name: str) -> bool:
    db = auth_store.get_db()
    result = db.tools.delete_one({"name": name})
    return result.deleted_count > 0
