"""The Router — maps a task's agent_type to a concrete agent_id.

Priority: user's custom agent (dept-matching first) → system default → general.
Never returns None (seed_defaults guarantees a 'general' system agent exists).
"""

from __future__ import annotations

from app.agents.store import find_agents_by_type, get_system_default


def route(task: dict, mission: dict) -> str:
    agent_type = task["agent_type"]
    user_id = mission["created_by"]
    department_id = mission.get("department_id")

    candidates = find_agents_by_type(agent_type, user_id, department_id)
    if candidates:
        return candidates[0]["id"]

    default = get_system_default(agent_type)
    if default:
        return default["id"]

    # Absolute last resort — should never happen after seed_defaults().
    general = get_system_default("general")
    return general["id"] if general else "sys-general"
