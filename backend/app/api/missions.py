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
    # When the user is answering a clarifying question, the frontend sends the
    # original goal plus the answer so the planner has full context and skips
    # asking again.
    clarified: bool = False


@router.post("/missions", status_code=202)
async def create_mission(req: CreateMissionRequest) -> dict:
    mission_id = store.create_mission(
        req.prompt, DEFAULT_USER, req.department_id, req.conversation_id
    )
    # Fire-and-forget: the mission runs in the background; the client watches via WS.
    task = asyncio.create_task(engine.run_mission(mission_id, skip_clarify=req.clarified))
    _running[mission_id] = task
    task.add_done_callback(lambda _t, mid=mission_id: _running.pop(mid, None))
    return {"mission_id": mission_id}


@router.post("/missions/{mission_id}/stop")
async def stop_mission(mission_id: str) -> dict:
    """Cancel a running mission immediately — the backend stops working on it."""
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


@router.get("/missions")
async def list_missions(limit: int = 50, offset: int = 0, status: str | None = None) -> dict:
    limit = max(1, min(limit, 200))
    missions = store.list_missions(limit, offset, status, DEFAULT_USER)
    return {"missions": missions, "count": len(missions)}


@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str) -> dict:
    mission = store.get_mission(mission_id)
    if mission is None:
        raise HTTPException(404, f"Mission '{mission_id}' not found")
    return mission


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
