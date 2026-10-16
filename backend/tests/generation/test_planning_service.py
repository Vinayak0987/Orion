"""Tests for the planning report builder (design.md §4-§7, phases.md Phase 2).

Offline: the LLM is scripted (ScriptedProvider / DeadProvider, the
tests/test_api.py pattern); no department runners are involved, so
placeholders are unnecessary. The database is a tmp file per test.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

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
from app.generation.planning import service, store

PHYSICAL_PROMPT = "Ice cream shop in Andheri, Rs 15L budget"
DIGITAL_PROMPT = "Start an online tutoring platform for CBSE students"


class ScriptedProvider(LLMProvider):
    """Returns a fixed extraction payload - the intent classifier's LLM."""

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


def _ice_cream_payload() -> dict:
    return {
        "business_type": "ice_cream_shop",
        "business_type_label": "Ice Cream Shop",
        "sector": "food_and_beverage",
        "area": "Andheri West",
        "city": "Mumbai",
        "budget_text": "Rs 15L",
        "confidence": 0.9,
    }


def _scripted_client(payload: dict | None = None) -> LLMClient:
    return LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=ScriptedProvider(payload or _ice_cream_payload()),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )


def _dead_client() -> LLMClient:
    return LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=DeadProvider(ProviderName.GEMINI),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch) -> None:
    """Throwaway database for both the sessions tables and planning_reports."""
    db_file = tmp_path / "service.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file)
    )
    sqlite.init_db()
    store.init_planning()



# =============================================================================
# ready vs blocked
# =============================================================================


async def test_ready_report_with_scripted_llm() -> None:
    record = await service.build_report(PHYSICAL_PROMPT, client=_scripted_client())

    assert record["status"] == "ready"
    assert record["blockers"] == []
    assert record["intent_source"] == "llm"
    assert record["intent"]["business_type"] == "ice_cream_shop"
    persisted = store.get_report(record["id"])
    assert persisted is not None
    assert persisted["status"] == "ready"


async def test_blocked_report_when_every_provider_is_down() -> None:
    record = await service.build_report(PHYSICAL_PROMPT, client=_dead_client())

    assert record["status"] == "blocked"
    assert len(record["blockers"]) == 1
    assert "every LLM provider unavailable" in record["blockers"][0]
    # A blocked report still lists the full plan (design.md §7).
    assert len(record["agents"]) == 21
    assert record["intent_source"] == "heuristic"
    # The heuristic path carries the §7 low-confidence warning.
    assert any("keyword heuristic" in w for w in record["warnings"])


async def test_blockers_are_only_the_two_impossible_conditions() -> None:
    """Missing external-API keys are warnings, never blockers (§7)."""
    record = await service.build_report(PHYSICAL_PROMPT, client=_scripted_client())
    assert record["blockers"] == []
    # settings.warnings() surfaces verbatim (whatever keys this env lacks).
    for warning in record["warnings"]:
        assert not warning.startswith("BLOCKER")


# =============================================================================
# 21 vs 17 agents - physical vs digital routing
# =============================================================================


async def test_physical_prompt_enumerates_21_agents() -> None:
    record = await service.build_report(PHYSICAL_PROMPT, client=_scripted_client())
    assert len(record["agents"]) == 21
    assert "operations" not in record["skipped_departments"]
    ids = [a["agent_id"] for a in record["agents"]]
    assert len(set(ids)) == 21  # every agent appears exactly once


async def test_digital_prompt_enumerates_17_agents_and_skips_operations() -> None:
    payload = {
        "business_type": "online_tutoring_platform",
        "business_type_label": "Online Tutoring Platform",
        "sector": "education",
        "area": "",
        "city": "",
        "budget_text": "",
        "confidence": 0.85,
    }
    record = await service.build_report(DIGITAL_PROMPT, client=_scripted_client(payload))
    assert len(record["agents"]) == 17
    assert record["skipped_departments"] == ["operations"]
    assert "operations" not in {a["department"] for a in record["agents"]}


async def test_force_all_gives_21_agents_with_rq2_warning() -> None:
    record = await service.build_report(
        DIGITAL_PROMPT, force_all=True, client=_scripted_client()
    )
    assert len(record["agents"]) == 21
    assert record["skipped_departments"] == []
    assert any("force_all_departments engaged" in w for w in record["warnings"])


# =============================================================================
# estimate arithmetic (design.md §6)
# =============================================================================


async def test_estimates_are_the_documented_upper_bound() -> None:
    record = await service.build_report(PHYSICAL_PROMPT, client=_scripted_client())

    expected = service.INTENT_MAX_TOKENS + sum(a["max_tokens"] for a in record["agents"])
    assert record["estimated_max_completion_tokens"] == expected
    assert record["estimated_agent_calls"] == 21
    # The API view labels the bound honestly (§4).
    view = service.to_api_view(record)
    assert view["estimates"]["intent_llm_calls"] == 1
    assert view["estimates"]["agent_llm_calls"] == 21
    assert view["estimates"]["max_completion_tokens"] == expected


# =============================================================================
# heuristic warning (no provider up)
# =============================================================================


async def test_heuristic_intent_source_is_flagged() -> None:
    record = await service.build_report(PHYSICAL_PROMPT, client=_dead_client())
    assert record["intent_source"] == "heuristic"
    view = service.to_api_view(record)
    assert view["estimates"]["intent_llm_calls"] == 0


# =============================================================================
# inferences (design.md §6) and the §7 one-to-one warning derivation
# =============================================================================


async def test_inferences_full_payload() -> None:
    """All four fields resolved: business_type/budget/area confirmed or
    inferred with corroborated sourceLabels."""
    record = await service.build_report(PHYSICAL_PROMPT, client=_scripted_client())
    view = service.to_api_view(record)
    entries = {entry["label"]: entry for entry in view["inferences"]}

    assert set(entries) == {"business_type", "budget", "location_area", "sector"}

    bt = entries["business_type"]
    assert bt["value"] == "ice_cream_shop"
    assert bt["status"] == "inferred"
    assert bt["confidence"] == 0.9
    assert bt["sourceLabels"] == ["llm"]

    budget = entries["budget"]
    assert budget["status"] == "confirmed"
    assert budget["sourceLabels"] == ["budget_parser"]
    assert "parsed deterministically" in budget["rationale"]

    area = entries["location_area"]
    assert area["value"] == "Andheri"  # gazetteer normalizes 'Andheri West'
    assert area["status"] == "confirmed"
    assert area["sourceLabels"] == ["gazetteer"]

    sector = entries["sector"]
    assert sector["value"] == "food_and_beverage"
    assert sector["status"] == "inferred"
    assert sector["sourceLabels"] == ["llm", "keyword_vote"]  # corroborated


async def test_inferences_needs_confirmation_and_warning_mapping() -> None:
    """An empty prompt leaves fields unspecified -> needs-confirmation, and
    §7 derives exactly one warning per such entry."""
    record = await service.build_report(
        "generic trading business", client=_scripted_client(
            {
                "business_type": "",
                "business_type_label": "",
                "sector": "unspecified",
                "area": "",
                "city": "",
                "budget_text": "",
                "confidence": 0.4,
            }
        )
    )
    view = service.to_api_view(record)
    entries = {entry["label"]: entry for entry in view["inferences"]}

    assert entries["budget"]["status"] == "needs-confirmation"
    assert entries["location_area"]["status"] == "needs-confirmation"
    assert entries["sector"]["status"] == "needs-confirmation"

    # §7: one-to-one mapping needs-confirmation -> "prompt lacks {label} - ..."
    derived = [
        w for w in record["warnings"] if w.startswith("prompt lacks ")
    ]
    assert sorted(w.split(" - ")[0] for w in derived) == [
        "prompt lacks budget",
        "prompt lacks location_area",
        "prompt lacks sector",
    ]
    # business_type came from the keyword fallback, so it is inferred.
    assert entries["business_type"]["status"] == "inferred"
    assert entries["business_type"]["sourceLabels"] == ["keyword_fallback"]


async def test_inferences_are_recomputed_at_read_time_not_stored() -> None:
    """No inferences column exists (§5); the array is derived from the stored
    intent + prompt, so it can never disagree with the stored intent."""
    record = await service.build_report(PHYSICAL_PROMPT, client=_scripted_client())
    with sqlite.connection() as conn:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(planning_reports)")]
    assert "inferences_json" not in columns

    again = service.to_api_view(store.get_report(record["id"]))
    assert again["inferences"] == service.to_api_view(record)["inferences"]


# =============================================================================
# validation + expiry in the API view
# =============================================================================


async def test_short_prompt_raises_validation_error() -> None:
    from app.generation.intent.classifier import PromptValidationError

    with pytest.raises(PromptValidationError, match="at least 10 characters"):
        await service.build_report("cafe", client=_scripted_client())
    # Nothing was persisted for the rejected prompt.
    assert store.list_reports(limit=10) == []


async def test_api_view_has_expires_at_plus_frozen_column_names() -> None:
    record = await service.build_report(PHYSICAL_PROMPT, client=_scripted_client())
    view = service.to_api_view(record)

    assert view["prompt"] == PHYSICAL_PROMPT
    assert "raw_prompt" not in view
    expected_expiry = datetime.fromisoformat(view["created_at"]) + timedelta(hours=24)
    assert datetime.fromisoformat(view["expires_at"]) == expected_expiry
    # Frozen store columns stay intact (no renames, memory.md §4 vocabulary).
    assert set(record) == {
        "id", "raw_prompt", "intent", "intent_source", "status",
        "blockers", "warnings", "routing", "agents",
        "active_departments", "skipped_departments",
        "estimated_agent_calls", "estimated_max_completion_tokens",
        "created_at", "confirmed_at", "confirmed_by",
        "executed_at", "executed_session_id",
    }
