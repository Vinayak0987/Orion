"""Mission Results endpoints — tools/evidence/trace/export + list search/type.

Runs a real mission through the engine with a scripted LLM (one tool call) so
execution_traces has data, then asserts the aggregation endpoints.
"""

from __future__ import annotations

import json

import pytest

from app.agents.defaults import seed_defaults


class ScriptedLLM:
    def __init__(self):
        self._step = 0

    async def call_structured(self, prompt, system="", tier="fast"):
        if "needs_clarification" in system:
            return {"needs_clarification": False}
        if "durable" in system or "reusable" in system:
            return []
        return [
            {"title": "Find competitors", "agent_type": "research", "tools_needed": ["web_search"], "depends_on": []},
            {"title": "Summarize", "agent_type": "writing", "tools_needed": [], "depends_on": ["Find competitors"]},
        ]

    async def call_text(self, prompt, system="", tier="fast", temperature=0.7):
        from app.llm.providers import LLMResult
        return LLMResult(text="Competitor Analysis", provider="scripted", model="x")

    async def call(self, messages, tier="fast", temperature=0.7):
        from app.llm.providers import LLMResult
        last = messages[-1]["content"]
        if "Find competitors" in last and self._step == 0:
            self._step = 1
            return LLMResult(text=json.dumps({"tool": "web_search", "input": {"query": "competitors"}}),
                             provider="scripted", model="x", input_tokens=10, output_tokens=5)
        if "web_search" in last:
            return LLMResult(text="Found 5 competitors: A, B, C, D, E.", provider="scripted", model="x",
                             input_tokens=20, output_tokens=10)
        return LLMResult(text="Summary: 5 key players in the market.", provider="scripted", model="x",
                         input_tokens=15, output_tokens=8)


@pytest.fixture
def scripted(monkeypatch):
    seed_defaults()
    llm = ScriptedLLM()
    import app.missions.engine as engine_mod
    import app.missions.executor as exec_mod
    monkeypatch.setattr(engine_mod, "LLMClient", lambda user_keys=None: llm)
    monkeypatch.setattr(exec_mod, "LLMClient", lambda user_keys=None: llm)

    async def fake_dispatch(tool_name, tool_input, user_keys=None, ctx=None):
        return {"results": [{"title": "Competitor A", "url": "http://a.com"}], "count": 1}
    monkeypatch.setattr(exec_mod.registry, "dispatch", fake_dispatch)
    return llm


async def _run(prompt="Analyze competitors"):
    from app.missions import engine, store
    mid = store.create_mission(prompt, "default-user")
    await engine.run_mission(mid, skip_clarify=True)
    return mid


async def test_tools_endpoint(scripted):
    from app.api.missions import mission_tools
    mid = await _run()
    data = await mission_tools(mid)
    assert any(t["tool"] == "web_search" and t["calls"] >= 1 for t in data["tools"])
    ws = next(t for t in data["tools"] if t["tool"] == "web_search")
    assert ws["success_rate"] == 100


async def test_evidence_endpoint(scripted):
    from app.api.missions import mission_evidence
    mid = await _run()
    data = await mission_evidence(mid)
    assert len(data["evidence"]) >= 1
    assert data["evidence"][0]["tool"] == "web_search"
    assert data["evidence"][0]["output"].get("count") == 1


async def test_trace_endpoint(scripted):
    from app.api.missions import mission_trace
    mid = await _run()
    data = await mission_trace(mid)
    assert len(data["steps"]) >= 2
    assert any(s["type"] == "llm" for s in data["steps"])
    assert any(s["type"] == "tool" for s in data["steps"])
    assert data["total_tokens"] > 0


async def test_export_endpoint(scripted):
    from app.api.missions import mission_export
    mid = await _run()
    data = await mission_export(mid)
    assert data["mission_id"] == mid
    assert len(data["tasks"]) == 2
    assert data["tasks"][0]["title"]


async def test_list_search_and_type(scripted):
    from app.api.missions import list_missions
    await _run("Analyze my competitors thoroughly")
    found = await list_missions(search="competitors")
    assert found["count"] >= 1
    m = found["missions"][0]
    assert m["type"] in ("Research", "Planning", "Operations")
    assert "progress" in m and "agent_ids" in m
