"""The Router — maps a task to a concrete agent_id.

Default: user agent (dept-biased) → system default → general.
Department-aware: when a mission targets a department, route to that department's
HEAD so it can decompose + delegate to specialists (built dynamically).
"""

from __future__ import annotations

from app.agents.store import find_agents_by_type, get_system_default


def route(task: dict, mission: dict) -> str:
    """Backward-compatible single agent_id."""
    return resolve(task, mission)["agent_id"]


def resolve(task: dict, mission: dict) -> dict:
    """Richer decision: {agent_id, department_id, is_head, source}."""
    agent_type = task["agent_type"]
    user_id = mission["created_by"]
    department_id = mission.get("department_id") or task.get("department_id")

    # Department-scoped → route to the department HEAD (it will delegate).
    if department_id:
        from app.departments import store as dept_store
        head = dept_store.get_head(department_id)
        if head:
            return {"agent_id": head["agent_id"], "department_id": department_id,
                    "is_head": True, "source": "dept_head"}

    candidates = find_agents_by_type(agent_type, user_id, department_id)
    if candidates:
        return {"agent_id": candidates[0]["id"], "department_id": department_id,
                "is_head": False, "source": "user_agent"}
    default = get_system_default(agent_type)
    if default:
        return {"agent_id": default["id"], "department_id": department_id,
                "is_head": False, "source": "system_default"}
    general = get_system_default("general")
    gid = general["id"] if general else "sys-general"
    return {"agent_id": gid, "department_id": department_id, "is_head": False, "source": "general"}
