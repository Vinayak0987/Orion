"""Multi-agent pipeline tests — structured sub_agents, the AI architect
endpoint (LLM mocked), and the sequential sub-agent executor (LLM mocked)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "workspace_path", str(tmp_path / "ws"))
    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "chroma"))
    from app.db import init_db

    init_db()
    from app.agents.defaults import seed_defaults
    from app.tools.seed import seed_builtin_tools

    seed_defaults()
    seed_builtin_tools()
    yield


@pytest.fixture
def client():
    from fastapi import FastAPI

    from app.api.agents import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# --- 1. Structured sub_agent round-trips through create + get -----------------
def test_structured_sub_agents_persist(client):
    body = {
        "name": "Master",
        "system_prompt": "Orchestrate.",
        "agent_type": "marketing",
        "tools": ["calculator", "text_summarizer"],
        "sub_agents": [
            {"id": "sa_1", "name": "Scorer", "role": "score", "input": "mission",
             "output": "scores", "tools": ["calculator"], "order": 1},
            {"id": "sa_2", "name": "Writer", "role": "write", "input": "scores",
             "output": "copy", "tools": ["text_summarizer"], "order": 2},
        ],
    }
    aid = client.post("/agents", json=body).json()["agent_id"]
    agent = client.get(f"/agents/{aid}").json()
    assert len(agent["sub_agents"]) == 2
    assert [s["name"] for s in agent["sub_agents"]] == ["Scorer", "Writer"]
    assert agent["sub_agents"][0]["tools"] == ["calculator"]
    assert agent["sub_agents"][1]["output"] == "copy"


# --- 2. Architect endpoint derives a validated pipeline (LLM mocked) ----------
def test_architect_endpoint(client, monkeypatch):
    import app.agents.architect as arch

    pipeline_json = {
        "name": "Customer Outreach",
        "agent_type": "marketing",
        "purpose": "Score users and email them.",
        "system_prompt": "You orchestrate outreach.",
        "sub_agents": [
            {"name": "Scorer", "role": "score users", "input": "interactions",
             "output": "scores", "tools": ["data_aggregator", "NOT_A_REAL_TOOL"]},
            {"name": "Writer", "role": "draft emails", "input": "scores",
             "output": "emails", "tools": ["text_summarizer"]},
        ],
    }

    class FakeLLM:
        def __init__(self, user_keys=None):
            pass

        async def call_structured(self, prompt, system="", tier="fast"):
            return pipeline_json

    monkeypatch.setattr(arch, "LLMClient", FakeLLM)

    r = client.post("/agents/architect", json={
        "description": "Score customers and email them.",
        "department": "Marketing", "agent_type": "marketing",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Customer Outreach"
    assert len(data["sub_agents"]) == 2
    # Bogus tool was stripped during validation.
    assert "NOT_A_REAL_TOOL" not in data["sub_agents"][0]["tools"]
    assert "data_aggregator" in data["sub_agents"][0]["tools"]
    # Each sub-agent got an id + order.
    assert data["sub_agents"][0]["order"] == 1
    assert data["sub_agents"][1]["order"] == 2
    assert all(s["id"].startswith("sa_") for s in data["sub_agents"])
    # Master tools = union of sub-agent tools.
    assert set(data["tools"]) == {"data_aggregator", "text_summarizer"}


def test_architect_503_when_no_llm(client, monkeypatch):
    import app.agents.architect as arch
    from app.llm.client import AllProvidersFailedError

    class FailLLM:
        def __init__(self, user_keys=None):
            pass

        async def call_structured(self, prompt, system="", tier="fast"):
            raise AllProvidersFailedError({"groq": "no key"})

    monkeypatch.setattr(arch, "LLMClient", FailLLM)
    r = client.post("/agents/architect", json={"description": "do things"})
    assert r.status_code == 503


# --- 3. Sequential pipeline executor (LLM mocked) -----------------------------
@pytest.mark.asyncio
async def test_pipeline_executor_runs_in_order(monkeypatch):
    import app.missions.executor as exec_mod
    from app.agents.store import create_agent
    from app.llm.providers import LLMResult

    # Each LLM call just echoes which step it is + the input it was given, so we
    # can assert ordering + that output piped into the next step's prompt.
    seen_prompts: list[str] = []

    class FakeLLM:
        def __init__(self, user_keys=None):
            pass

        async def call(self, messages, tier="fast", temperature=0.7):
            user = messages[-1]["content"]
            seen_prompts.append(user)
            # Give a final answer (no tool call) tagged with the sub-agent name.
            sys = messages[0]["content"]
            tag = "STEP_A" if "step A" in sys or "Alpha" in sys else "STEP_B"
            return LLMResult(text=f"done {tag}", provider="fake", model="x",
                             input_tokens=1, output_tokens=1)

    monkeypatch.setattr(exec_mod, "LLMClient", FakeLLM)

    aid = create_agent(
        name="Master", system_prompt="Orchestrate.", agent_type="general",
        tools=[], sub_agents=[
            {"id": "sa_1", "name": "Alpha", "role": "first", "input": "mission",
             "output": "a-out", "tools": [], "system_prompt": "You are step A (Alpha).", "order": 1},
            {"id": "sa_2", "name": "Beta", "role": "second", "input": "a-out",
             "output": "b-out", "tools": [], "system_prompt": "You are step B (Beta).", "order": 2},
        ],
    )

    events: list[dict] = []

    async def emit(event_type, **payload):
        events.append({"event": event_type, **payload})

    task = {"id": "t1", "title": "Do the pipeline", "agent_type": "general"}
    mission = {"id": "m1", "created_by": "default-user", "user_keys": None, "short_term_memory": ""}

    result = await exec_mod.run_task(aid, task, {}, mission, emit)

    # Ordered pipeline events emitted.
    names = [e["event"] for e in events]
    assert names[0] == "pipeline_start"
    assert names[-1] == "pipeline_done"
    steps = [e.get("step") for e in events if e["event"] == "step_start"]
    assert steps == ["Alpha", "Beta"]

    # Step 1's output was piped into step 2's prompt.
    assert any("done STEP_A" in p for p in seen_prompts)
    # Final output is the last step's output.
    assert "STEP_B" in result["data"]
    assert len(result["steps"]) == 2


@pytest.mark.asyncio
async def test_single_agent_still_works_without_sub_agents(monkeypatch):
    """Backward compat: an agent with no sub_agents uses the single ReAct loop."""
    import app.missions.executor as exec_mod
    from app.agents.store import create_agent
    from app.llm.providers import LLMResult

    class FakeLLM:
        def __init__(self, user_keys=None):
            pass

        async def call(self, messages, tier="fast", temperature=0.7):
            return LLMResult(text="single answer", provider="fake", model="x",
                             input_tokens=1, output_tokens=1)

    monkeypatch.setattr(exec_mod, "LLMClient", FakeLLM)

    aid = create_agent(name="Solo", system_prompt="Help.", agent_type="general", tools=[])

    async def emit(event_type, **payload):
        pass

    task = {"id": "t1", "title": "hi", "agent_type": "general"}
    mission = {"id": "m1", "created_by": "default-user", "user_keys": None, "short_term_memory": ""}
    result = await exec_mod.run_task(aid, task, {}, mission, emit)
    assert "single answer" in result["data"]
    assert "steps" not in result  # single path doesn't return a pipeline steps list
