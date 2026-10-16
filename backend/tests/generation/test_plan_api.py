"""Tests for the /planning/plans HTTP surface (Planner Subsystem, Step 6).

Offline: the LLM the executor/service resolves is scripted, real department
runners are swapped for trace-emitting fakes, and the database is a tmp file.
No network, no quota. TestClient over the real app router.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.generation.agents import registry
from app.generation.agents.registry import agents_for
from app.generation.db import sqlite
from app.generation.llm.base import (
    FreeTierTracker,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
)
from app.generation.llm.chain import LLMClient
from app.main import app
from app.generation.models.state import AgentTrace, Department
from app.generation.planning import store

INTENT_PAYLOAD = {
    "business_type": "ice_cream_shop",
    "business_type_label": "Ice Cream Shop",
    "sector": "food_and_beverage",
    "area": "Andheri",
    "city": "Mumbai",
    "budget_text": "Rs 15L",
    "confidence": 0.9,
}


class ScriptedProvider(LLMProvider):
    def __init__(self, payload: dict) -> None:
        self.name = ProviderName.GEMINI
        self.tracker = FreeTierTracker(name="gemini")
        self.payload = payload

    def model_for(self, tier: ModelTier) -> str:
        return "gemini-scripted"

    async def is_available(self) -> bool:
        return True

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self.payload),
            provider=self.name,
            model="gemini-scripted",
            prompt_tokens=40,
            completion_tokens=20,
        )


class DeadProvider(LLMProvider):
    def __init__(self, name: ProviderName) -> None:
        self.name = name
        self.tracker = FreeTierTracker(name=name.value)

    def model_for(self, tier: ModelTier) -> str:
        return "dead"

    async def is_available(self) -> bool:
        return False

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise ProviderUnavailable("dead")


def _fake_runner(department: Department):
    async def runner(state):
        return {
            "agent_traces": [
                AgentTrace(
                    agent_id=agent.spec.agent_id,
                    department=department,
                    status="completed",
                    completion_tokens=10,
                )
                for agent in agents_for(department)
            ]
        }

    return runner


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    db_file = tmp_path / "plan_api.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file)
    )
    sqlite.init_db()
    from app.generation.planning import init_planning

    init_planning()

    scripted = LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=ScriptedProvider(INTENT_PAYLOAD),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )
    import app.generation.app_routes as main_module
    import app.generation.planning.service as service_module
    import app.generation.planning.plan_api as plan_api_module
    import app.generation.intent.classifier as classifier_module

    monkeypatch.setattr(service_module, "llm_client", scripted)
    monkeypatch.setattr(main_module, "llm_client", scripted)
    # The run route passes this client into orchestrate; the intent step inside
    # orchestrate falls back to the classifier's module-level client.
    monkeypatch.setattr(plan_api_module, "llm_client", scripted)
    monkeypatch.setattr(classifier_module, "llm_client", scripted)

    # Swap real department runners for trace-emitting fakes so a run is offline.
    originals = {dept: registry.DEPARTMENT_RUNNERS[dept] for dept in Department}
    for dept in Department:
        registry.register_runner(dept, _fake_runner(dept))

    yield scripted

    # Restore the real runners so no other test sees the fakes.
    for dept, runner in originals.items():
        registry.register_runner(dept, runner)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _confirmed_report(client) -> str:
    """Create a report and confirm it, returning its id."""
    created = client.post(
        "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L budget"}
    ).json()
    client.post(f"/planning/reports/{created['id']}/confirm", json={"by": "tester"})
    return created["id"]


# =============================================================================
# POST /planning/plans - compile from confirmed report
# =============================================================================


def test_compile_plan_from_confirmed_report_is_201() -> None:
    with TestClient(app) as client:
        report_id = _confirmed_report(client)
        response = client.post("/planning/plans", json={"report_id": report_id})

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "draft"
        assert body["report_id"] == report_id
        assert len(body["nodes"]) == 21
        bp = next(n for n in body["nodes"] if n["id"] == "business_planning")
        assert bp["depends_on"]  # stage-2 node has dependencies


def test_compile_rejects_unconfirmed_report_with_409() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L"}
        ).json()
        # Not confirmed yet.
        response = client.post("/planning/plans", json={"report_id": created["id"]})
        assert response.status_code == 409
        assert "confirmed" in response.json()["detail"]


def test_compile_unknown_report_is_404() -> None:
    with TestClient(app) as client:
        response = client.post("/planning/plans", json={"report_id": "does-not-exist"})
        assert response.status_code == 404


# =============================================================================
# GET plan / list / events
# =============================================================================


def test_get_plan_returns_full_node_list() -> None:
    with TestClient(app) as client:
        report_id = _confirmed_report(client)
        plan_id = client.post("/planning/plans", json={"report_id": report_id}).json()["id"]

        response = client.get(f"/planning/plans/{plan_id}")
        assert response.status_code == 200
        assert len(response.json()["nodes"]) == 21


def test_get_unknown_plan_is_404() -> None:
    with TestClient(app) as client:
        assert client.get("/planning/plans/nope").status_code == 404


def test_list_plans_returns_summaries() -> None:
    with TestClient(app) as client:
        report_id = _confirmed_report(client)
        client.post("/planning/plans", json={"report_id": report_id})

        rows = client.get("/planning/plans").json()
        assert len(rows) == 1
        assert rows[0]["node_count"] == 21
        assert "nodes" not in rows[0]  # summary only


# =============================================================================
# POST run - offline via fake runners
# =============================================================================


def test_run_plan_executes_and_marks_nodes() -> None:
    with TestClient(app) as client:
        report_id = _confirmed_report(client)
        plan_id = client.post("/planning/plans", json={"report_id": report_id}).json()["id"]

        response = client.post(f"/planning/plans/{plan_id}/run")
        assert response.status_code == 200
        body = response.json()
        assert all(n["status"] == "completed" for n in body["nodes"])

        # The execution trace is queryable and brackets the run.
        events = client.get(f"/planning/plans/{plan_id}/events").json()
        assert events[0]["event_type"] == "run_started"
        assert events[-1]["event_type"] == "run_finished"


def test_run_unknown_plan_is_404() -> None:
    with TestClient(app) as client:
        assert client.post("/planning/plans/nope/run").status_code == 404


def test_events_unknown_plan_is_404() -> None:
    with TestClient(app) as client:
        assert client.get("/planning/plans/nope/events").status_code == 404
