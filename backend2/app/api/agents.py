"""Agents REST API (Plan 05).

Full CRUD + clone + version history + templates + from-template + performance +
a live /test that runs the REAL executor in isolation on a single synthetic task.

Phase 1: single-user placeholder (created_by='default-user'), matching the rest
of the backend.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents import store

router = APIRouter(tags=["agents"])

DEFAULT_USER = "default-user"

_VALID_TYPES = {"research", "marketing", "finance", "operations", "hr", "analysis", "writing", "general"}


class SubAgentSpec(BaseModel):
    """One step in a master agent's pipeline. Each sub-agent has a focused role,
    a declared input/output contract, and ONLY the tools it actually needs."""
    id: str = Field(default_factory=lambda: "sa_" + uuid.uuid4().hex[:8])
    name: str = Field(min_length=1, max_length=120)
    role: str = ""                       # what this sub-agent does
    input: str = ""                      # what it consumes (prev step output / mission input)
    output: str = ""                     # what it produces for the next step
    tools: list[str] = Field(default_factory=list)   # minimal tool set (builtin + external)
    system_prompt: str = ""              # optional explicit prompt; derived if blank
    order: int = 0


class CreateAgentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    system_prompt: str = Field(min_length=1)
    agent_type: str = "general"
    purpose: str = ""
    tools: list[str] = Field(default_factory=list)
    sub_agents: list[SubAgentSpec] = Field(default_factory=list)
    department_id: str | None = None
    model: str | None = None
    temperature: float = 0.7
    memory_enabled: bool = True
    memory_ttl_days: int = 30
    permissions: dict = Field(default_factory=dict)


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    agent_type: str | None = None
    purpose: str | None = None
    tools: list[str] | None = None
    sub_agents: list[SubAgentSpec] | None = None
    department_id: str | None = None
    model: str | None = None
    temperature: float | None = None
    memory_enabled: bool | None = None
    memory_ttl_days: int | None = None
    permissions: dict | None = None
    status: str | None = None
    note: str = ""


class TestAgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class FromTemplateRequest(BaseModel):
    name: str | None = None


class CloneRequest(BaseModel):
    name: str | None = None


class ArchitectRequest(BaseModel):
    description: str = Field(min_length=1, max_length=4000)
    department: str = ""
    agent_type: str = "general"


# ---- AI Architect (declared before /{agent_id} so paths don't collide) -----
@router.post("/agents/architect")
async def architect(req: ArchitectRequest) -> dict:
    """Derive a structured multi-agent pipeline from a natural-language goal.
    Returns the master config + ordered sub_agents (each with role, I/O, and a
    minimal tool set). Nothing is persisted — the UI reviews/edits, then POSTs
    to /agents to create."""
    from app.agents import architect as arch
    from app.llm.client import AllProvidersFailedError
    from app.settings import store as settings_store

    try:
        keys = settings_store.decrypted_keys(DEFAULT_USER)
    except Exception:  # noqa: BLE001
        keys = None
    try:
        pipeline = await arch.design_pipeline(
            req.description, department=req.department, agent_type=req.agent_type, user_keys=keys,
        )
    except AllProvidersFailedError as e:
        raise HTTPException(503, f"No LLM available to design the pipeline: {e}") from e
    return pipeline


# ---- Templates (declared before /{agent_id} so paths don't collide) --------
@router.get("/agents/templates")
async def list_templates() -> dict:
    return {"templates": store.list_templates()}


@router.post("/agents/from-template/{template_id}", status_code=201)
async def create_from_template(template_id: str, req: FromTemplateRequest) -> dict:
    agent_id = store.create_from_template(template_id, name=req.name, created_by=DEFAULT_USER)
    if agent_id is None:
        raise HTTPException(404, f"Template '{template_id}' not found")
    return {"agent_id": agent_id, "agent": store.get_agent(agent_id)}


# ---- CRUD -------------------------------------------------------------------
@router.get("/agents")
async def list_agents(status: str = "active", type: str | None = None,
                      department_id: str | None = None) -> dict:
    agents = store.list_agents_with_stats(status=status, agent_type=type, department_id=department_id)
    return {"agents": agents, "count": len(agents)}


@router.post("/agents", status_code=201)
async def create_agent(req: CreateAgentRequest) -> dict:
    if req.agent_type not in _VALID_TYPES:
        raise HTTPException(422, f"agent_type must be one of {sorted(_VALID_TYPES)}")
    agent_id = store.create_agent(created_by=DEFAULT_USER, **req.model_dump())
    return {"agent_id": agent_id, "agent": store.get_agent(agent_id)}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    agent = store.get_agent(agent_id)
    if agent is None:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return agent


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, req: UpdateAgentRequest) -> dict:
    changes = {k: v for k, v in req.model_dump(exclude_unset=True).items() if k != "note"}
    if req.agent_type and req.agent_type not in _VALID_TYPES:
        raise HTTPException(422, f"agent_type must be one of {sorted(_VALID_TYPES)}")
    updated = store.update_agent(agent_id, changes, note=req.note)
    if updated is None:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return {"agent": updated}


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str) -> dict:
    if not store.delete_agent(agent_id):
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return {"deleted": agent_id}


@router.post("/agents/{agent_id}/clone", status_code=201)
async def clone_agent(agent_id: str, req: CloneRequest) -> dict:
    new_id = store.clone_agent(agent_id, new_name=req.name, created_by=DEFAULT_USER)
    if new_id is None:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return {"agent_id": new_id, "agent": store.get_agent(new_id)}


@router.get("/agents/{agent_id}/versions")
async def get_versions(agent_id: str) -> dict:
    if store.get_agent(agent_id) is None:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return {"versions": store.get_versions(agent_id)}


@router.get("/agents/{agent_id}/performance")
async def get_performance(agent_id: str) -> dict:
    perf = store.performance(agent_id)
    if perf is None:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return perf


@router.post("/agents/{agent_id}/test")
async def test_agent(agent_id: str, req: TestAgentRequest) -> dict:
    """Run the REAL executor on a single synthetic task in isolation and return
    the full trace + output. Uses a throwaway mission id so traces don't pollute
    real missions."""
    agent = store.get_agent(agent_id)
    if agent is None:
        raise HTTPException(404, f"Agent '{agent_id}' not found")

    from app.missions.executor import run_task
    from app.traces.store import list_traces

    test_mission_id = f"test-{uuid.uuid4().hex[:10]}"
    task = {"id": uuid.uuid4().hex[:10], "title": req.message, "agent_type": agent["agent_type"],
            "tools_needed": agent.get("tools", [])}
    mission = {"id": test_mission_id, "created_by": DEFAULT_USER, "user_keys": None,
               "short_term_memory": ""}

    captured: list[dict] = []

    async def emit(event_type, **payload):
        captured.append({"event": event_type, **payload})

    try:
        result = await run_task(agent_id, task, {}, mission, emit)
    except Exception as e:  # noqa: BLE001 — surface, never 500 the test console
        return {"ok": False, "error": str(e), "events": captured}

    steps = [{"type": t["trace_type"], "provider": t.get("provider"), "model": t.get("model"),
              "tool_name": t.get("tool_name"), "latency_ms": t.get("latency_ms"),
              "success": bool(t.get("success")), "error": t.get("error_message")}
             for t in list_traces(test_mission_id)]
    return {"ok": "error" not in result, "output": result.get("data") or result.get("summary"),
            "result": result, "trace": steps, "events": captured}
