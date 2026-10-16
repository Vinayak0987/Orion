"""Tests for the /planning HTTP surface (design.md §8, phases.md Phase 3).

Offline: the LLM is scripted at the service boundary (the route calls
`build_report` without a client, which resolves the module-level
`service.llm_client`), and the database is a tmp file. No department
runners are involved, so placeholders are unnecessary.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

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
from app.generation.planning import store


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


INTENT_PAYLOAD = {
    "business_type": "ice_cream_shop",
    "business_type_label": "Ice Cream Shop",
    "sector": "food_and_beverage",
    "area": "Andheri West",
    "city": "Mumbai",
    "budget_text": "Rs 15L",
    "confidence": 0.9,
}


@pytest.fixture(autouse=True)
def offline_planning_api(tmp_path, monkeypatch):
    """Isolate the database and script the LLM the service resolves."""
    db_file = tmp_path / "planning_api.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file)
    )
    sqlite.init_db()
    store.init_planning()

    scripted = LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=ScriptedProvider(INTENT_PAYLOAD),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )
    import app.generation.planning.service as service_module
    import app.generation.app_routes as main_module

    monkeypatch.setattr(service_module, "llm_client", scripted)
    # The lifespan closes llm_client on shutdown; keep the real singleton safe.
    monkeypatch.setattr(main_module, "llm_client", scripted)

    yield scripted


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _dead_client() -> LLMClient:
    return LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=DeadProvider(ProviderName.GEMINI),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )


# =============================================================================
# POST /planning/reports - 201 (ready and blocked) and 422
# =============================================================================


def test_create_ready_report_is_201_with_full_shape(client) -> None:
    response = client.post(
        "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L budget"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["blockers"] == []
    assert body["intent_source"] == "llm"
    assert body["intent"]["business_type"] == "ice_cream_shop"
    assert len(body["agents"]) == 21
    assert body["estimates"]["agent_llm_calls"] == 21
    assert {entry["label"] for entry in body["inferences"]} == {
        "business_type", "budget", "location_area", "sector",
    }
    assert body["expires_at"] > body["created_at"]


def test_create_blocked_report_is_201_and_lists_the_full_plan(client) -> None:
    offline_planning_api = _dead_client()

    # Swap the scripted (available) client for a dead one for this test only.
    import app.generation.planning.service as service_module

    original = service_module.llm_client
    service_module.llm_client = offline_planning_api
    try:
        response = client.post(
            "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L budget"}
        )
    finally:
        service_module.llm_client = original

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "blocked"
    assert len(body["blockers"]) == 1
    assert "every LLM provider unavailable" in body["blockers"][0]
    # A blocked report still shows what would run (§7).
    assert len(body["agents"]) == 21
    assert body["estimates"]["intent_llm_calls"] == 0


def test_create_rejects_short_prompt_with_422(client) -> None:
    response = client.post("/planning/reports", json={"prompt": "cafe"})

    assert response.status_code == 422
    assert "at least 10 characters" in response.json()["detail"]


def test_create_rejects_empty_prompt_body(client) -> None:
    assert client.post("/planning/reports", json={"prompt": ""}).status_code == 422


def test_force_all_flag_reaches_the_router(client) -> None:
    response = client.post(
        "/planning/reports",
        json={
            "prompt": "Start an online tutoring platform for CBSE students",
            "force_all_departments": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["agents"]) == 21
    assert any("force_all_departments engaged" in w for w in body["warnings"])


# =============================================================================
# GET /planning/reports - list, summary fields only
# =============================================================================


def test_list_returns_summaries_newest_first(client) -> None:
    first = client.post(
        "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L budget"}
    ).json()
    second = client.post(
        "/planning/reports",
        json={"prompt": "Start an online tutoring platform for CBSE students"},
    ).json()

    response = client.get("/planning/reports")
    assert response.status_code == 200
    rows = response.json()
    assert [r["id"] for r in rows] == [second["id"], first["id"]]
    # Summary fields only.
    assert set(rows[0]) == {"id", "prompt", "status", "agent_count", "created_at"}
    assert rows[0]["agent_count"] == 17
    assert rows[1]["agent_count"] == 21


def test_list_pagination_is_capped_at_200(client) -> None:
    assert client.get("/planning/reports", params={"limit": 500}).status_code == 422
    assert client.get("/planning/reports", params={"limit": 0}).status_code == 422
    response = client.get("/planning/reports", params={"limit": 200, "offset": 0})
    assert response.status_code == 200


# =============================================================================
# GET /planning/reports/{id} - 200 / 404
# =============================================================================


def test_get_returns_full_report(client) -> None:
    created = client.post(
        "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L budget"}
    ).json()

    response = client.get(f"/planning/reports/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert len(response.json()["agents"]) == 21


def test_get_unknown_is_404(client) -> None:
    assert client.get("/planning/reports/nope").status_code == 404


# =============================================================================
# POST /planning/reports/{id}/confirm - 200 / 409 / 404
# =============================================================================


def test_confirm_ready_report_is_200(client) -> None:
    created = client.post(
        "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L budget"}
    ).json()

    response = client.post(
        f"/planning/reports/{created['id']}/confirm", json={"by": "vinayak"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["confirmed_by"] == "vinayak"
    assert body["confirmed_at"] is not None


def test_confirm_accepts_missing_body_with_default_operator(client) -> None:
    created = client.post(
        "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L budget"}
    ).json()

    response = client.post(f"/planning/reports/{created['id']}/confirm")
    assert response.status_code == 200
    assert response.json()["confirmed_by"] == "operator"


def test_confirm_unknown_is_404(client) -> None:
    assert client.post("/planning/reports/nope/confirm").status_code == 404


def test_confirm_409_for_every_illegal_transition(client) -> None:
    import app.generation.planning.service as service_module

    # blocked -> 409
    original = service_module.llm_client
    service_module.llm_client = _dead_client()
    try:
        blocked = client.post(
            "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L budget"}
        ).json()
    finally:
        service_module.llm_client = original
    assert blocked["status"] == "blocked"
    response = client.post(f"/planning/reports/{blocked['id']}/confirm")
    assert response.status_code == 409
    assert "cannot be confirmed" in response.json()["detail"]

    # confirmed -> 409 (double confirm)
    ready = client.post(
        "/planning/reports", json={"prompt": "Ice cream shop in Andheri, Rs 15L budget"}
    ).json()
    assert client.post(f"/planning/reports/{ready['id']}/confirm").status_code == 200
    second = client.post(f"/planning/reports/{ready['id']}/confirm")
    assert second.status_code == 409
    assert "cannot be confirmed" in second.json()["detail"]

    # expired -> 409 (lazy TTL, exercised through the store)
    stale = store.create_report(
        raw_prompt="Ice cream shop in Andheri, Rs 15L budget",
        intent_source="llm",
        status="ready",
        created_at="2020-01-01T00:00:00+00:00",
    )
    expired = client.post(f"/planning/reports/{stale['id']}/confirm")
    assert expired.status_code == 409
    assert "expired" in expired.json()["detail"]


# =============================================================================
# OpenAPI surface
# =============================================================================


def test_planning_tag_and_routes_present_in_openapi(client) -> None:
    schema = client.get("/openapi.json").json()

    paths = schema["paths"]
    assert "/planning/reports" in paths
    assert "/planning/reports/{report_id}" in paths
    assert "/planning/reports/{report_id}/confirm" in paths

    # The tag rides on each operation (the app defines no top-level tag
    # metadata, same as the operating router's "operating" tag).
    planning_operations = [
        operation
        for path in ("/planning/reports", "/planning/reports/{report_id}",
                     "/planning/reports/{report_id}/confirm")
        for operation in paths[path].values()
    ]
    assert all(
        "planning" in operation.get("tags", []) for operation in planning_operations
    )
