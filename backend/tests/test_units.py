"""Unit tests for planner validation, router, agents, JSON repair, and the API."""

from __future__ import annotations

from app.agents.defaults import seed_defaults


# --- planner validation ------------------------------------------------------

def test_planner_validate_drops_bad_depends_and_types():
    from app.missions.planner import _validate

    raw = [
        {"title": "A", "agent_type": "research", "tools_needed": ["web_search"], "depends_on": []},
        {"title": "B", "agent_type": "nonsense", "tools_needed": ["bad_tool"],
         "depends_on": ["A", "ghost"]},
    ]
    out = _validate(raw)
    assert len(out) == 2
    b = next(t for t in out if t["title"] == "B")
    assert b["agent_type"] == "general"      # invalid type coerced
    assert b["tools_needed"] == []           # invalid tool dropped
    assert b["depends_on"] == ["A"]          # ghost dependency dropped


# --- router ------------------------------------------------------------------

def test_router_returns_system_default():
    from app.missions.router import route

    seed_defaults()
    mission = {"created_by": "default-user", "department_id": None}
    agent_id = route({"agent_type": "research"}, mission)
    assert agent_id == "sys-research"


def test_router_falls_back_to_general_for_unknown_type():
    from app.missions.router import route

    seed_defaults()
    mission = {"created_by": "default-user", "department_id": None}
    agent_id = route({"agent_type": "doesnotexist"}, mission)
    assert agent_id == "sys-general"


# --- agents store ------------------------------------------------------------

def test_seed_defaults_idempotent():
    from app.agents.store import list_agents

    seed_defaults()
    seed_defaults()
    agents = list_agents()
    types = {a["agent_type"] for a in agents}
    assert {"research", "marketing", "finance", "analysis", "writing",
            "operations", "general"}.issubset(types)
    # No duplicates from double seeding.
    assert sum(1 for a in agents if a["id"] == "sys-research") == 1


# --- JSON repair -------------------------------------------------------------

def test_extract_json_from_markdown():
    from app.llm.repair import extract_json

    text = 'Here is the plan:\n```json\n[{"title": "x"}]\n```\nDone.'
    assert extract_json(text) == [{"title": "x"}]


def test_extract_json_direct():
    from app.llm.repair import extract_json

    assert extract_json('{"tool": "web_search"}') == {"tool": "web_search"}


def test_extract_json_raises_on_garbage():
    import pytest

    from app.llm.repair import JSONParseError, extract_json

    with pytest.raises(JSONParseError):
        extract_json("no json here at all")


# --- API ---------------------------------------------------------------------

def test_missions_api_list_empty():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/missions")
        assert resp.status_code == 200
        assert resp.json()["missions"] == []


def test_health_endpoint():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["database"] == "ok"
        assert "llm_providers" in body


def test_settings_api_keys_roundtrip():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        client.put("/settings/api-keys", json={"groq_api_key": "gsk_secret1234"})
        resp = client.get("/settings/api-keys")
        assert resp.json()["groq"] == "...1234"   # masked
