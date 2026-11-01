"""Missions + mission_tasks store - MongoDB-backed."""

from __future__ import annotations

import json
import uuid

from app.auth import store as auth_store


def _decode_mission(doc: dict, include_tasks: bool = True) -> dict:
    """Convert MongoDB doc to mission dict."""
    mission = dict(doc)
    mission["id"] = mission.pop("_id")
    # Map user_id to created_by for compatibility
    if "user_id" in mission and "created_by" not in mission:
        mission["created_by"] = mission["user_id"]
    if include_tasks:
        mission["tasks"] = list_tasks(mission["id"])
    else:
        mission["tasks"] = []
    return mission


def _decode_task(doc: dict) -> dict:
    """Convert MongoDB doc to task dict."""
    task = dict(doc)
    task["id"] = task.pop("_id")
    for f in ("tools_needed", "depends_on"):
        task[f] = task.get(f) or []
    task["result"] = task.get("result") or None
    return task


# --- missions ----------------------------------------------------------------

def create_mission(prompt: str, created_by: str = "default-user",
                   department_id: str | None = None,
                   conversation_id: str | None = None,
                   mode: str = "action") -> str:
    """Create a mission in MongoDB."""
    mission_id = uuid.uuid4().hex[:12]
    mode = mode if mode in ("planning", "action") else "action"
    auth_store.create_mission(
        mission_id, created_by, prompt, None, department_id, conversation_id, mode
    )
    return mission_id


def set_mission(mission_id: str, **fields) -> None:
    """Update mission fields in MongoDB."""
    auth_store.update_mission(mission_id, **fields)


def get_mission(mission_id: str, user_id: str = "default-user") -> dict | None:
    """Get a mission from MongoDB."""
    doc = auth_store.get_mission(mission_id, user_id)
    if doc is None:
        return None
    return _decode_mission(doc)


def list_missions(limit: int = 50, offset: int = 0, status: str | None = None,
                  created_by: str = "default-user", search: str | None = None,
                  mtype: str | None = None) -> list[dict]:
    """List missions from MongoDB."""
    missions = auth_store.list_missions(created_by, limit, offset)
    
    # Filter by status if specified
    if status:
        missions = [m for m in missions if m.get("status") == status]
    
    # Filter by search if specified
    if search:
        search_lower = search.lower()
        missions = [m for m in missions if search_lower in m.get("prompt", "").lower() or search_lower in m.get("title", "").lower()]
    
    out = []
    for m in missions:
        m_decoded = _decode_mission(m)
        tasks = auth_store.get_mission_tasks(m_decoded["id"])
        
        # Calculate stats
        agent_types = [t.get("agent_type") for t in tasks if t.get("agent_type")]
        agent_ids = sorted({t.get("agent_id") for t in tasks if t.get("agent_id")})
        
        m_decoded["task_count"] = len(tasks)
        m_decoded["agent_count"] = len(agent_ids)
        m_decoded["type"] = _classify_type(agent_types)
        m_decoded["agent_ids"] = agent_ids
        done = sum(1 for t in tasks if t.get("status") in ("completed", "failed", "stopped"))
        m_decoded["progress"] = round(100 * done / len(tasks)) if tasks else 0
        out.append(m_decoded)
    
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


def delete_mission(mission_id: str, user_id: str = "default-user") -> bool:
    """Delete a mission from MongoDB."""
    auth_store.delete_mission_tasks(mission_id)
    return auth_store.delete_mission(mission_id, user_id)


# --- tasks -------------------------------------------------------------------

def save_tasks(mission_id: str, tasks: list[dict]) -> list[dict]:
    """Insert planner tasks into MongoDB. Returns them with assigned ids."""
    saved = []
    for t in tasks:
        task_id = uuid.uuid4().hex[:12]
        auth_store.create_mission_task(
            task_id, mission_id, t["title"], t["agent_type"],
            t.get("agent_id"), t.get("tools_needed", []), t.get("depends_on", []), "pending"
        )
        saved.append({**t, "id": task_id, "mission_id": mission_id, "status": "pending"})
    return saved


def set_task(task_id: str, **fields) -> None:
    """Update task fields in MongoDB."""
    auth_store.update_mission_task(task_id, **fields)


def list_tasks(mission_id: str) -> list[dict]:
    """List tasks for a mission from MongoDB."""
    tasks = auth_store.get_mission_tasks(mission_id)
    return [_decode_task(t) for t in tasks]
