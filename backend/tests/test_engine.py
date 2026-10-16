"""End-to-end mission engine test — fully offline with a scripted LLM and mocked tools.

Verifies the whole Phase 1 loop: plan → route → execute (ReAct with a tool call)
→ dependency ordering → mission completes with results and traces.
"""

from __future__ import annotations

import json

import pytest

from app.agents.defaults import seed_defaults


class ScriptedLLM:
    """Stand-in for LLMClient. Returns canned responses based on call type."""

    def __init__(self):
        self.plan_json = [
            {"title": "Find competitors", "agent_type": "research",
             "tools_needed": ["web_search"], "depends_on": []},
            {"title": "Summarize findings", "agent_type": "writing",
             "tools_needed": [], "depends_on": ["Find competitors"]},
        ]
        self._research_step = 0

    async def call_structured(self, prompt, system="", tier="fast"):
        return self.plan_json

    async def call_text(self, prompt, system="", tier="fast", temperature=0.7):
        from app.llm.providers import LLMResult
        return LLMResult(text="Competitor Analysis", provider="scripted", model="x")

    async def call(self, messages, tier="fast", temperature=0.7):
        from app.llm.providers import LLMResult
        last = messages[-1]["content"]
        # Research agent: first reply is a tool call, then a final answer.
        if "Find competitors" in last and self._research_step == 0:
            self._research_step = 1
            return LLMResult(
                text=json.dumps({"tool": "web_search", "input": {"query": "competitors"}}),
                provider="scripted", model="x", input_tokens=10, output_tokens=5,
            )
        if "web_search" in last:
            return LLMResult(text="Found 5 competitors: A, B, C, D, E.",
                             provider="scripted", model="x", input_tokens=20, output_tokens=10)
        # Writing agent: direct final answer.
        return LLMResult(text="Summary: the market has 5 key players.",
                         provider="scripted", model="x", input_tokens=15, output_tokens=8)


@pytest.fixture
def scripted(monkeypatch):
    seed_defaults()
    llm = ScriptedLLM()

    # Patch the LLMClient constructor everywhere the engine/executor builds one.
    import app.missions.engine as engine_mod
    import app.missions.executor as exec_mod
    monkeypatch.setattr(engine_mod, "LLMClient", lambda user_keys=None: llm)
    monkeypatch.setattr(exec_mod, "LLMClient", lambda user_keys=None: llm)

    # Mock the web_search tool so no network is touched.
    async def fake_dispatch(tool_name, tool_input, user_keys=None):
        return {"results": [{"title": "Competitor A"}], "count": 1}
    monkeypatch.setattr(exec_mod.registry, "dispatch", fake_dispatch)

    return llm


async def test_full_mission_runs_offline(scripted):
    from app.missions import engine, store

    mission_id = store.create_mission("Analyze my competitors", "default-user")
    await engine.run_mission(mission_id)

    mission = store.get_mission(mission_id)
    assert mission["status"] == "completed"
    assert mission["title"]  # title generated
    assert len(mission["tasks"]) == 2

    statuses = {t["title"]: t["status"] for t in mission["tasks"]}
    assert statuses["Find competitors"] == "completed"
    assert statuses["Summarize findings"] == "completed"

    # Research task should have an agent assigned.
    research = next(t for t in mission["tasks"] if t["title"] == "Find competitors")
    assert research["agent_id"] is not None
    assert research["result"]["data"]  # produced output


async def test_traces_recorded(scripted):
    from app.missions import engine, store
    from app.traces.store import list_traces

    mission_id = store.create_mission("Analyze my competitors", "default-user")
    await engine.run_mission(mission_id)

    traces = list_traces(mission_id)
    assert any(t["trace_type"] == "llm" for t in traces)
    assert any(t["trace_type"] == "tool" and t["tool_name"] == "web_search" for t in traces)


async def test_empty_plan_fails_cleanly(scripted, monkeypatch):
    from app.missions import engine, store

    scripted.plan_json = []  # planner returns no tasks
    mission_id = store.create_mission("vague", "default-user")
    await engine.run_mission(mission_id)

    mission = store.get_mission(mission_id)
    assert mission["status"] == "failed"
