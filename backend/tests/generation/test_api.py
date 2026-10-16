"""Tests for the HTTP and WebSocket API surface.

Offline: the orchestrator's department runners are replaced with placeholders and
the LLM is scripted, so the endpoints are exercised without network access.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.generation.agents.registry import DEPARTMENT_RUNNERS, make_placeholder, register_runner
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
from app.generation.models.state import Department
from app.generation.output import SECTION_ORDER

INTENT_PAYLOAD = {
    "business_type": "ice_cream_shop",
    "business_type_label": "Ice Cream Shop",
    "sector": "food_and_beverage",
    "area": "Andheri West",
    "city": "Mumbai",
    "budget_text": "Rs 15L",
    "confidence": 0.9,
}


class ScriptedProvider(LLMProvider):
    def __init__(self) -> None:
        self.name = ProviderName.GEMINI
        self.tracker = FreeTierTracker(name="gemini")

    def model_for(self, tier: ModelTier) -> str:
        return "gemini-3.5-flash-lite"

    async def is_available(self) -> bool:
        return True

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(INTENT_PAYLOAD),
            provider=self.name,
            model="gemini-3.5-flash-lite",
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


@pytest.fixture(autouse=True)
def offline_api(tmp_path, monkeypatch):
    """Isolate the database and keep departments and the LLM offline."""
    db_file = tmp_path / "api.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file)
    )
    sqlite.init_db()

    original = dict(DEPARTMENT_RUNNERS)
    for department in Department:
        register_runner(department, make_placeholder(department))

    scripted = LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=ScriptedProvider(),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )
    import app.generation.intent.classifier as classifier_module
    import app.generation.app_routes as main_module

    monkeypatch.setattr(classifier_module, "llm_client", scripted)
    # The app's lifespan closes llm_client on shutdown; each TestClient context
    # triggers that, so a second test would find the real singleton closed.
    monkeypatch.setattr(main_module, "llm_client", scripted)

    yield

    for department, runner in original.items():
        register_runner(department, runner)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


# =============================================================================
# F64 - health
# =============================================================================


def test_health_reports_every_subsystem(client) -> None:
    body = client.get("/health").json()
    assert body["status"] in ("ok", "degraded")
    for key in (
        "database",
        "llm_providers",
        "external_apis",
        "knowledge_cache",
        "pdf_export",
        "grounding",
        "feature_flags",
        "warnings",
    ):
        assert key in body, key


def test_health_names_the_rq3_arm(client) -> None:
    grounding = client.get("/health").json()["grounding"]
    assert grounding["rq3_arm"] in ("grounded", "text_only")


# =============================================================================
# F1/F2 - intent endpoint
# =============================================================================


def test_intent_endpoint_returns_execution_plan(client) -> None:
    response = client.post("/intent", json={"prompt": "Ice cream shop in Andheri, Rs 15L"})
    assert response.status_code == 200

    body = response.json()
    assert body["intent"]["sector"] == "food_and_beverage"
    assert body["derived"]["scale"] == "small"
    stages = body["execution_plan"]["stages"]
    assert stages[0]["departments"] == ["strategy"]
    assert stages[1]["execution"] == "parallel"


def test_intent_endpoint_rejects_short_prompt(client) -> None:
    response = client.post("/intent", json={"prompt": "cafe"})
    assert response.status_code == 422
    assert "at least 10 characters" in response.json()["detail"]


# =============================================================================
# F45 - section catalogue
# =============================================================================


def test_sections_catalogue(client) -> None:
    body = client.get("/sections").json()
    assert body["count"] == len(SECTION_ORDER)
    keys = [section["key"] for section in body["sections"]]
    assert keys == list(SECTION_ORDER)


# =============================================================================
# F10-F13 - generate endpoint
# =============================================================================


def test_generate_returns_run_summary(client) -> None:
    response = client.post("/generate", json={"prompt": "Ice cream shop in Andheri, Rs 15L"})
    assert response.status_code == 200

    body = response.json()
    assert body["session_id"]
    assert body["routing"]["active_departments"]
    assert "plan" in body


def test_generate_rejects_short_prompt(client) -> None:
    assert client.post("/generate", json={"prompt": "cafe"}).status_code == 422


def test_generate_force_all_departments_is_the_control_arm(client) -> None:
    body = client.post(
        "/generate",
        json={"prompt": "Start an online tutoring platform", "force_all_departments": True},
    ).json()
    assert len(body["routing"]["active_departments"]) == 5
    assert body["routing"]["skipped_departments"] == []


# =============================================================================
# F51 - session history
# =============================================================================


def test_sessions_list_and_fetch(client) -> None:
    created = client.post("/generate", json={"prompt": "Bakery in Dadar with 10 lakh"}).json()
    session_id = created["session_id"]

    listing = client.get("/sessions").json()
    assert any(item["id"] == session_id for item in listing)

    detail = client.get(f"/sessions/{session_id}").json()
    assert detail["raw_prompt"].startswith("Bakery in Dadar")


def test_session_delete(client) -> None:
    session_id = client.post("/generate", json={"prompt": "Salon in Bandra 12 lakh"}).json()[
        "session_id"
    ]
    assert client.delete(f"/sessions/{session_id}").status_code == 200
    assert client.get(f"/sessions/{session_id}").status_code == 404


def test_missing_session_returns_404(client) -> None:
    assert client.get("/sessions/nope").status_code == 404


# =============================================================================
# F42-F45 - output endpoints
# =============================================================================


def test_package_endpoint_requires_a_stored_plan(client) -> None:
    """Placeholder runners write nothing, so there is no plan to package."""
    session_id = client.post("/generate", json={"prompt": "Ice cream shop in Andheri"}).json()[
        "session_id"
    ]
    response = client.get(f"/sessions/{session_id}/package")
    assert response.status_code == 409
    assert "no stored plan" in response.json()["detail"]


def test_unknown_section_key_lists_valid_keys(client) -> None:
    session_id = client.post("/generate", json={"prompt": "Ice cream shop in Andheri"}).json()[
        "session_id"
    ]
    response = client.get(f"/sessions/{session_id}/sections/not_a_section")
    assert response.status_code == 404
    assert "Valid keys" in response.json()["detail"]


def test_report_for_missing_session_is_404(client) -> None:
    assert client.get("/sessions/nope/report").status_code == 404
    assert client.get("/sessions/nope/report.pdf").status_code == 404


# =============================================================================
# F48 - WebSocket progress
# =============================================================================


def test_websocket_streams_progress_then_result(client) -> None:
    with client.websocket_connect("/ws/generate") as socket:
        socket.send_json({"prompt": "Ice cream shop in Andheri, Rs 15L budget"})

        events = []
        while True:
            message = socket.receive_json()
            events.append(message)
            if message.get("event") in ("result", "error"):
                break

    kinds = [event["event"] for event in events]
    assert kinds[0] == "session_started"
    assert "intent_resolved" in kinds
    assert "routing_resolved" in kinds
    assert kinds.count("department_started") == 5
    assert kinds.count("department_completed") == 5
    assert kinds[-1] == "result"

    summary = events[-1]["summary"]
    assert summary["session_id"]
    assert summary["routing"]["active_departments"]


def test_websocket_reports_progress_percentage(client) -> None:
    with client.websocket_connect("/ws/generate") as socket:
        socket.send_json({"prompt": "Ice cream shop in Andheri, Rs 15L budget"})

        percentages = []
        while True:
            message = socket.receive_json()
            if message.get("event") == "department_completed":
                percentages.append(message["percent"])
            if message.get("event") in ("result", "error"):
                break

    assert percentages == [20.0, 40.0, 60.0, 80.0, 100.0]


def test_websocket_reports_validation_error_without_closing_hard(client) -> None:
    with client.websocket_connect("/ws/generate") as socket:
        socket.send_json({"prompt": "cafe"})
        message = socket.receive_json()

    assert message["event"] == "error"
    assert message["kind"] == "validation"
    assert "at least 10 characters" in message["detail"]


def test_websocket_honours_force_all_departments(client) -> None:
    with client.websocket_connect("/ws/generate") as socket:
        socket.send_json(
            {"prompt": "Start an online tutoring platform", "force_all_departments": True}
        )
        while True:
            message = socket.receive_json()
            if message.get("event") in ("result", "error"):
                break

    assert len(message["summary"]["routing"]["active_departments"]) == 5


def test_websocket_dynamic_routing_skips_operations(client) -> None:
    with client.websocket_connect("/ws/generate") as socket:
        socket.send_json({"prompt": "Start an online tutoring platform for CBSE students"})
        started = []
        while True:
            message = socket.receive_json()
            if message.get("event") == "department_started":
                started.append(message["department"])
            if message.get("event") in ("result", "error"):
                break

    assert "operations" not in started
    assert len(started) == 4
    assert message["summary"]["routing"]["skipped_departments"] == ["operations"]
