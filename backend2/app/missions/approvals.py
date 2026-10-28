"""Approval gate — human-in-the-loop for real-world ACTION tools.

When an agent in Action mode tries to run an action tool (send email, post,
upload…), the executor calls `request_approval(...)` which BLOCKS (awaits) until
the user approves or denies via the API. Approvals live in memory keyed by a
generated approval id. The mission's WebSocket stream carries an
`approval_required` event so the UI can prompt; the API's resolve endpoint
unblocks the awaiting executor.

This is the shared gate used by MCP, API, and browser action tools alike.
"""

from __future__ import annotations

import asyncio
import uuid

# approval_id -> {"future": Future, "info": {...}, "status": "pending|approved|denied"}
_pending: dict[str, dict] = {}


def list_pending() -> list[dict]:
    return [
        {"approval_id": aid, **rec["info"], "status": rec["status"]}
        for aid, rec in _pending.items() if rec["status"] == "pending"
    ]


async def request_approval(*, mission_id: str, task_id: str, agent_id: str,
                           tool: str, tool_input: dict, reason: str, emit) -> dict:
    """Block until the user resolves this action. Returns
    {"approved": bool, "always": bool}. Emits approval_required on the mission WS."""
    approval_id = uuid.uuid4().hex[:12]
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    info = {"mission_id": mission_id, "task_id": task_id, "agent_id": agent_id,
            "tool": tool, "tool_input": tool_input, "reason": reason}
    _pending[approval_id] = {"future": fut, "info": info, "status": "pending"}

    await emit("approval_required", task_id=task_id, approval_id=approval_id,
               tool=tool, tool_input=tool_input, reason=reason)

    try:
        return await fut  # unblocked by resolve()
    finally:
        _pending.pop(approval_id, None)


def resolve(approval_id: str, approved: bool, always: bool = False) -> bool:
    """Resolve a pending approval. Returns True if it existed + was resolved."""
    rec = _pending.get(approval_id)
    if rec is None or rec["status"] != "pending":
        return False
    rec["status"] = "approved" if approved else "denied"
    fut = rec["future"]
    if not fut.done():
        fut.set_result({"approved": approved, "always": always})
    return True


def resolve_for_mission(mission_id: str, approved: bool) -> int:
    """Resolve all pending approvals for a mission (e.g. on stop/cancel)."""
    n = 0
    for aid, rec in list(_pending.items()):
        if rec["info"].get("mission_id") == mission_id and rec["status"] == "pending":
            if resolve(aid, approved):
                n += 1
    return n
