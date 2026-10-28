"""The Master — organization-level router at the front of the mission engine.

Given the user's goal, the Master decides WHICH department should own it (or
'direct' for a simple task that needs no department/hierarchy). It only chooses
from the user's actual departments; it never invents one. Reuses the shared
LLMClient (no parallel engine).

Returns {"department_id": str|None, "department_name": str|None, "reason": str,
"direct": bool}.
"""

from __future__ import annotations

from app.departments import store as dept_store
from app.llm.client import LLMClient

_SYSTEM = (
    "You are the Chief Orchestrator of an AI company. You read a user's goal and "
    "route it to the single most appropriate DEPARTMENT, or decide it's a simple "
    "task that should be handled directly without a department. Return STRICT JSON."
)


def _prompt(goal: str, depts: list[dict]) -> str:
    listing = "\n".join(f'- id="{d["id"]}" name="{d["name"]}" — {d.get("purpose","")[:100]}'
                        for d in depts)
    return f"""Available departments:
{listing}

User goal:
\"\"\"{goal.strip()}\"\"\"

Decide routing. Return STRICT JSON:
{{"department_id": "<exact id from the list, or empty string if direct>",
  "direct": <true if this is a simple task that needs no department, else false>,
  "reason": "<one short sentence>"}}

Guidance:
- Simple questions / quick lookups / one-off answers → direct=true, department_id="".
- Multi-step business work (marketing, research, finance, operations, content, etc.)
  → pick the best-matching department_id, direct=false.
Return ONLY the JSON object."""


async def route_goal(goal: str, *, created_by: str = "default-user",
                     user_keys: dict | None = None) -> dict:
    """Classify the goal. Falls back to 'direct' if the model is unavailable or
    returns something unusable — so a routing hiccup never blocks a mission."""
    depts = dept_store.list_departments(created_by=created_by)
    if not depts:
        return {"department_id": None, "department_name": None, "direct": True,
                "reason": "No departments available."}
    try:
        raw = await LLMClient(user_keys=user_keys).call_structured(
            _prompt(goal, depts), system=_SYSTEM, tier="fast")
    except Exception:  # noqa: BLE001
        return {"department_id": None, "department_name": None, "direct": True,
                "reason": "Router unavailable — handling directly."}
    if not isinstance(raw, dict):
        return {"department_id": None, "department_name": None, "direct": True,
                "reason": "Unclear routing — handling directly."}
    if raw.get("direct") or not raw.get("department_id"):
        return {"department_id": None, "department_name": None, "direct": True,
                "reason": str(raw.get("reason", "Simple task."))[:200]}
    # Validate the chosen id is a real department.
    did = str(raw.get("department_id")).strip()
    match = next((d for d in depts if d["id"] == did), None)
    if match is None:
        # Try name/slug match as a fallback.
        match = dept_store.find_by_slug_or_name(did, created_by=created_by)
    if match is None:
        return {"department_id": None, "department_name": None, "direct": True,
                "reason": "No matching department — handling directly."}
    return {"department_id": match["id"], "department_name": match["name"], "direct": False,
            "reason": str(raw.get("reason", ""))[:200]}
