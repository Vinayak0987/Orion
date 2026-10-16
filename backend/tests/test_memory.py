"""Memory + clarify + streaming tests — fully offline with a scripted LLM.

Covers:
  • clarifying question emitted for a vague goal, then skipped when answered
  • answer streamed as answer_chunk events
  • automatic long-term memory extracted into global_context
  • short-term memory (conversation history) reaches the planner prompt
"""

from __future__ import annotations

import json

import pytest

from app.engine.agents.defaults import seed_defaults


class ScriptedLLM:
    """Prompt-aware stand-in. Branches on the system prompt / content."""

    def __init__(self, needs_clarification=False, facts=None):
        self.needs_clarification = needs_clarification
        self.facts = facts or []
        self.seen_plan_prompts = []
        self._step = 0

    async def call_structured(self, prompt, system="", tier="fast"):
        if "needs_clarification" in system:  # CLARIFY_SYSTEM
            if self.needs_clarification:
                return {"needs_clarification": True, "question": "Which market should I focus on?"}
            return {"needs_clarification": False}
        if "durable" in system or "reusable facts" in system:  # MEMORY_SYSTEM
            return self.facts
        # PLANNER_SYSTEM — record the prompt so we can assert memory injection.
        self.seen_plan_prompts.append(prompt)
        return [
            {"title": "Do the thing", "agent_type": "general", "tools_needed": [], "depends_on": []},
        ]

    async def call_text(self, prompt, system="", tier="fast", temperature=0.7):
        from app.llm.providers import LLMResult
        return LLMResult(text="A Title", provider="scripted", model="x")

    async def call(self, messages, tier="fast", temperature=0.7):
        from app.llm.providers import LLMResult
        return LLMResult(text="Here is the final answer with enough length to stream in chunks.",
                         provider="scripted", model="x", input_tokens=5, output_tokens=5)


def _patch(monkeypatch, llm):
    import app.engine.missions.engine as engine_mod
    import app.engine.missions.executor as exec_mod
    monkeypatch.setattr(engine_mod, "LLMClient", lambda user_keys=None: llm)
    monkeypatch.setattr(exec_mod, "LLMClient", lambda user_keys=None: llm)


async def _collect_events(mission_id):
    """Drain the mission's event stream into a list after it finished."""
    from app.engine.missions import events
    out = []
    async for ev in events.subscribe(mission_id):
        out.append(ev)
    return out


@pytest.fixture(autouse=True)
def _seed():
    seed_defaults()


async def test_clarifying_question_pauses_mission(monkeypatch):
    from app.engine.missions import engine, store

    llm = ScriptedLLM(needs_clarification=True)
    _patch(monkeypatch, llm)

    conv = _new_conv()
    mission_id = store.create_mission("make a plan", "default-user", conversation_id=conv)
    await engine.run_mission(mission_id)

    events_list = await _collect_events(mission_id)
    kinds = [e["event"] for e in events_list]
    assert "clarification_needed" in kinds
    # planning_started may fire first to give the UI immediate feedback, but the
    # mission must PAUSE before producing any tasks.
    assert "task_created" not in kinds
    assert "planning_complete" not in kinds
    q = next(e for e in events_list if e["event"] == "clarification_needed")
    assert q["question"]
    assert store.get_mission(mission_id)["status"] == "awaiting_input"


async def test_skip_clarify_runs_full_mission(monkeypatch):
    from app.engine.missions import engine, store

    llm = ScriptedLLM(needs_clarification=True)  # would ask, but we skip
    _patch(monkeypatch, llm)

    mission_id = store.create_mission("make a plan for X in the US market", "default-user")
    await engine.run_mission(mission_id, skip_clarify=True)

    events_list = await _collect_events(mission_id)
    kinds = [e["event"] for e in events_list]
    assert "clarification_needed" not in kinds
    assert "planning_started" in kinds
    assert "mission_completed" in kinds


async def test_answer_is_streamed_in_chunks(monkeypatch):
    from app.engine.missions import engine, store

    llm = ScriptedLLM()
    _patch(monkeypatch, llm)

    mission_id = store.create_mission("just do it clearly", "default-user")
    await engine.run_mission(mission_id, skip_clarify=True)

    events_list = await _collect_events(mission_id)
    chunks = [e for e in events_list if e["event"] == "answer_chunk"]
    assert len(chunks) >= 2  # streamed in multiple pieces
    joined = "".join(e["text"] for e in chunks)
    assert "final answer" in joined
    completed = next(e for e in events_list if e["event"] == "mission_completed")
    assert completed["answer"] == joined


async def test_long_term_memory_auto_extracted(monkeypatch):
    from app.stores.chat import store as chat_store
    from app.engine.missions import engine, store

    facts = [{"key": "company", "value": "Acme"}, {"key": "tone", "value": "concise"}]
    llm = ScriptedLLM(facts=facts)
    _patch(monkeypatch, llm)

    conv = chat_store.create_conversation("default-user")["id"]
    chat_store.add_message(conv, "user", "I run Acme and prefer concise answers.")
    mission_id = store.create_mission("do a task", "default-user", conversation_id=conv)
    await engine.run_mission(mission_id, skip_clarify=True)

    saved = {f["key"]: f["value"] for f in chat_store.list_context("default-user")}
    assert saved.get("company") == "Acme"
    assert saved.get("tone") == "concise"

    events_list = await _collect_events(mission_id)
    assert any(e["event"] == "memory_updated" for e in events_list)


async def test_short_term_memory_reaches_planner(monkeypatch):
    from app.stores.chat import store as chat_store
    from app.engine.missions import engine, store

    llm = ScriptedLLM()
    _patch(monkeypatch, llm)

    conv = chat_store.create_conversation("default-user")["id"]
    chat_store.add_message(conv, "user", "Earlier I said my budget is 5000 dollars.")
    mission_id = store.create_mission("continue the plan", "default-user", conversation_id=conv)
    await engine.run_mission(mission_id, skip_clarify=True)

    # The planner prompt should include the recent conversation text.
    assert any("budget is 5000" in p for p in llm.seen_plan_prompts)


def _new_conv():
    from app.stores.chat import store as chat_store
    return chat_store.create_conversation("default-user")["id"]
