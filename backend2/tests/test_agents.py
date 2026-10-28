"""Agents backend tests (Plan 05) — CRUD, versioning, clone, templates, performance.

The /test endpoint runs the real executor; here we patch the LLM to stay offline.
"""

from __future__ import annotations

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
    from app.agents.templates import seed_templates
    from app.tools.seed import seed_builtin_tools

    seed_defaults()
    seed_templates()
    seed_builtin_tools()
    yield


@pytest.fixture
def client():
    from app.api.agents import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_list_includes_seeded_defaults(client):
    r = client.get("/agents")
    assert r.status_code == 200
    agents = r.json()["agents"]
    assert len(agents) >= 7
    assert all("stats" in a for a in agents)


def test_create_get_update_delete_lifecycle(client):
    # Create
    r = client.post("/agents", json={"name": "My Agent", "system_prompt": "Do things.",
                                     "agent_type": "research", "tools": ["web_search"]})
    assert r.status_code == 201
    aid = r.json()["agent_id"]

    # Get
    assert client.get(f"/agents/{aid}").json()["name"] == "My Agent"

    # Update bumps version + snapshots previous
    r = client.put(f"/agents/{aid}", json={"name": "Renamed", "note": "rename"})
    assert r.status_code == 200
    assert r.json()["agent"]["name"] == "Renamed"
    assert r.json()["agent"]["version"] != "v1.0.0"

    versions = client.get(f"/agents/{aid}/versions").json()["versions"]
    assert len(versions) >= 1

    # Soft delete — disappears from active list but row remains
    assert client.delete(f"/agents/{aid}").status_code == 200
    active_ids = {a["id"] for a in client.get("/agents").json()["agents"]}
    assert aid not in active_ids
    assert client.get("/agents?status=deleted").json()["count"] >= 1


def test_invalid_agent_type_rejected(client):
    r = client.post("/agents", json={"name": "X", "system_prompt": "y", "agent_type": "wizard"})
    assert r.status_code == 422


def test_clone(client):
    aid = client.post("/agents", json={"name": "Orig", "system_prompt": "p",
                                      "agent_type": "general"}).json()["agent_id"]
    r = client.post(f"/agents/{aid}/clone", json={"name": "Copy"})
    assert r.status_code == 201
    assert r.json()["agent"]["name"] == "Copy"
    assert r.json()["agent_id"] != aid


def test_templates_listed_and_instantiated(client):
    templates = client.get("/agents/templates").json()["templates"]
    assert len(templates) == 7
    tpl_id = templates[0]["id"]
    r = client.post(f"/agents/from-template/{tpl_id}", json={"name": "From Tpl"})
    assert r.status_code == 201
    assert r.json()["agent"]["name"] == "From Tpl"


def test_from_unknown_template_404(client):
    assert client.post("/agents/from-template/nope", json={}).status_code == 404


def test_performance_empty_agent(client):
    aid = client.post("/agents", json={"name": "P", "system_prompt": "p",
                                      "agent_type": "general"}).json()["agent_id"]
    r = client.get(f"/agents/{aid}/performance")
    assert r.status_code == 200
    body = r.json()
    assert body["runs"] == 0 and body["tool_usage"] == []


def test_test_endpoint_runs_executor_offline(client, monkeypatch):
    import app.missions.executor as exec_mod
    from app.llm.providers import LLMResult

    class FakeLLM:
        async def call(self, messages, tier="fast", temperature=0.7):
            return LLMResult(text="Hello, I am a test agent response.", provider="fake",
                             model="x", input_tokens=5, output_tokens=7)

    monkeypatch.setattr(exec_mod, "LLMClient", lambda user_keys=None: FakeLLM())

    aid = client.post("/agents", json={"name": "T", "system_prompt": "Be helpful.",
                                      "agent_type": "general", "tools": []}).json()["agent_id"]
    r = client.post(f"/agents/{aid}/test", json={"message": "Say hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "test agent response" in body["output"]
    assert any(s["type"] == "llm" for s in body["trace"])
