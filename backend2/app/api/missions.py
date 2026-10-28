"""Missions REST + WebSocket API."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.missions import engine, events, store

router = APIRouter(tags=["missions"])

# Phase 1: single-user placeholder. Auth integration is a later phase.
DEFAULT_USER = "default-user"

# Track the background asyncio task per mission so it can be cancelled on stop.
_running: dict[str, asyncio.Task] = {}


class CreateMissionRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=2000)
    department_id: str | None = None
    conversation_id: str | None = None
    mode: str = "action"   # planning (read-only) | action (all tools + approval)
    # When the user is answering a clarifying question, the frontend sends the
    # original goal plus the answer so the planner has full context and skips
    # asking again.
    clarified: bool = False


@router.post("/missions", status_code=202)
async def create_mission(req: CreateMissionRequest) -> dict:
    mission_id = store.create_mission(
        req.prompt, DEFAULT_USER, req.department_id, req.conversation_id, mode=req.mode
    )
    # Fire-and-forget: the mission runs in the background; the client watches via WS.
    task = asyncio.create_task(engine.run_mission(mission_id, skip_clarify=req.clarified))
    _running[mission_id] = task
    task.add_done_callback(lambda _t, mid=mission_id: _running.pop(mid, None))
    return {"mission_id": mission_id}


@router.post("/missions/{mission_id}/stop")
async def stop_mission(mission_id: str) -> dict:
    """Cancel a running mission immediately — the backend stops working on it."""
    from app.missions import approvals
    approvals.resolve_for_mission(mission_id, approved=False)
    task = _running.pop(mission_id, None)
    if task and not task.done():
        task.cancel()
    # Mark it stopped and tell any WS listeners to finalize.
    try:
        store.set_mission(mission_id, status="stopped")
    except Exception:
        pass
    await events.emit_to(mission_id, "mission_stopped")
    await events.finish(mission_id)
    return {"stopped": mission_id}


# ---- Approvals (human-in-the-loop for action tools) ------------------------
class ApprovalDecision(BaseModel):
    approved: bool
    always: bool = False


@router.get("/approvals")
async def list_approvals() -> dict:
    from app.missions import approvals
    return {"approvals": approvals.list_pending()}


@router.post("/approvals/{approval_id}")
async def resolve_approval(approval_id: str, req: ApprovalDecision) -> dict:
    from app.missions import approvals
    ok = approvals.resolve(approval_id, approved=req.approved, always=req.always)
    if not ok:
        raise HTTPException(404, "Approval not found or already resolved")
    return {"resolved": approval_id, "approved": req.approved}


@router.get("/missions")
async def list_missions(limit: int = 50, offset: int = 0, status: str | None = None,
                        search: str | None = None, type: str | None = None) -> dict:
    limit = max(1, min(limit, 200))
    missions = store.list_missions(limit, offset, status, DEFAULT_USER, search, type)
    return {"missions": missions, "count": len(missions)}


@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str) -> dict:
    mission = store.get_mission(mission_id)
    if mission is None:
        raise HTTPException(404, f"Mission '{mission_id}' not found")
    return mission


@router.get("/missions/{mission_id}/tools")
async def mission_tools(mission_id: str) -> dict:
    """Aggregated tool-call stats for this mission (from execution_traces)."""
    from app.traces.store import list_traces
    agg: dict[str, dict] = {}
    for t in list_traces(mission_id):
        if t["trace_type"] != "tool" or not t.get("tool_name"):
            continue
        a = agg.setdefault(t["tool_name"], {"tool": t["tool_name"], "calls": 0, "total_latency_ms": 0, "successes": 0})
        a["calls"] += 1
        a["total_latency_ms"] += t.get("latency_ms") or 0
        a["successes"] += 1 if t.get("success") else 0
    tools = []
    for a in agg.values():
        a["success_rate"] = round(100 * a["successes"] / a["calls"]) if a["calls"] else 0
        a["avg_latency_ms"] = round(a["total_latency_ms"] / a["calls"]) if a["calls"] else 0
        tools.append(a)
    tools.sort(key=lambda x: x["calls"], reverse=True)
    return {"tools": tools}


@router.get("/missions/{mission_id}/evidence")
async def mission_evidence(mission_id: str) -> dict:
    """Tool outputs as an evidence trail (from execution_traces)."""
    import json as _json
    from app.traces.store import list_traces
    items = []
    for t in list_traces(mission_id):
        if t["trace_type"] != "tool":
            continue
        try:
            out = _json.loads(t["tool_output"]) if t.get("tool_output") else {}
        except Exception:
            out = {"raw": t.get("tool_output")}
        try:
            inp = _json.loads(t["tool_input"]) if t.get("tool_input") else {}
        except Exception:
            inp = {}
        items.append({
            "tool": t.get("tool_name"), "input": inp, "output": out,
            "success": bool(t.get("success")), "created_at": t.get("created_at"),
        })
    return {"evidence": items}


@router.get("/missions/{mission_id}/trace")
async def mission_trace(mission_id: str) -> dict:
    """Ordered LLM + tool steps for this mission (provider, tokens, latency, cost)."""
    from app.traces.store import list_traces
    steps = []
    total_cost = 0.0
    total_tokens = 0
    for t in list_traces(mission_id):
        total_cost += t.get("cost_usd") or 0.0
        total_tokens += (t.get("input_tokens") or 0) + (t.get("output_tokens") or 0)
        steps.append({
            "type": t["trace_type"], "provider": t.get("provider"), "model": t.get("model"),
            "tool_name": t.get("tool_name"), "input_tokens": t.get("input_tokens"),
            "output_tokens": t.get("output_tokens"), "cost_usd": t.get("cost_usd"),
            "latency_ms": t.get("latency_ms"), "success": bool(t.get("success")),
            "error": t.get("error_message"), "created_at": t.get("created_at"),
        })
    return {"steps": steps, "total_cost_usd": round(total_cost, 6), "total_tokens": total_tokens}


@router.get("/missions/{mission_id}/export.json")
async def mission_export(mission_id: str) -> dict:
    mission = store.get_mission(mission_id)
    if mission is None:
        raise HTTPException(404, f"Mission '{mission_id}' not found")
    return {
        "mission_id": mission["id"], "prompt": mission["prompt"], "title": mission.get("title"),
        "status": mission["status"], "created_at": mission.get("created_at"),
        "completed_at": mission.get("completed_at"),
        "tasks": [
            {"title": t["title"], "agent_type": t["agent_type"], "agent_id": t.get("agent_id"),
             "status": t["status"], "tools_needed": t.get("tools_needed", []),
             "depends_on": t.get("depends_on", []), "result": t.get("result")}
            for t in mission.get("tasks", [])
        ],
    }


@router.delete("/missions/{mission_id}")
async def delete_mission(mission_id: str) -> dict:
    if not store.delete_mission(mission_id):
        raise HTTPException(404, f"Mission '{mission_id}' not found")
    return {"deleted": mission_id}


@router.websocket("/ws/missions/{mission_id}")
async def ws_mission(websocket: WebSocket, mission_id: str) -> None:
    await websocket.accept()
    try:
        async for event in events.subscribe(mission_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
