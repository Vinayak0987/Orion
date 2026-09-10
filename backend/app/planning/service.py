"""Planning report builder (design.md §4-§7, phases.md Phase 2).

`build_report` composes the generation layer's existing primitives - intent
classification, routing, agent topology, provider health - into one
persisted, inspect-and-confirm artefact. It READS those primitives; it never
re-derives topology, never alters routing, and never invents health facts
(`settings.warnings()` is surfaced verbatim).

Quota honesty (design.md §4): building a report costs at most ONE LLM call
(the intent classification). Confirming is free. The token bound
(`600 + Σ spec.max_tokens`) is labelled an upper bound everywhere.
"""

from __future__ import annotations

import structlog
from datetime import UTC, datetime, timedelta

from app.apis.places import select_provider
from app.config import settings
from app.db import sqlite
from app.intent.classifier import classify_intent, validate_prompt
from app.llm.chain import LLMClient, llm_client
from app.models.intent import BusinessIntent
from app.models.state import Department
from app.orchestrator.graph import describe_graph
from app.orchestrator.routing import resolve_departments
from app.agents.registry import DEPARTMENT_STAGES

from app.planning import store

log = structlog.get_logger(__name__)

# Design.md §5: lazy expiry keeps the system reaper-free. Promote to Settings
# only if operators ever need to tune it.
REPORT_TTL_HOURS = 24

# The classifier's max_tokens cap (classifier.py _classify_with_llm); the
# report's own estimate adds it on top of the agent sum (design.md §6).
INTENT_MAX_TOKENS = 600

# Agents that consult an external data source before prompting the model, and
# the source they would consult (design.md §6). All others ground via LLM only.
_GROUNDING_SOURCES: dict[str, str] = {
    "market_research": "serper",
    "competitive_analysis": None,  # resolved per report via select_provider()
}


# =============================================================================
# Intent source - llm or heuristic
# =============================================================================


async def _provider_availability(client: LLMClient) -> dict[str, bool]:
    """Snapshot of per-provider availability (the classifier's own inputs).

    The heuristic path fires only when EVERY provider is unavailable
    (classifier docstring); anything else means the classification came from
    an LLM. `classify_intent` itself is NOT modified (phases.md Phase 2 rule).
    """
    health = await client.health()
    return {name: entry["available"] for name, entry in health.items()}


def _intent_source(availability: dict[str, bool]) -> str:
    return "llm" if any(availability.values()) else "heuristic"


# =============================================================================
# Agent roster - flattened view of the existing topology (design.md §6)
# =============================================================================


# Agents that consult an external data source before prompting the model, and
# the source they would consult (design.md §6). All others ground via LLM only.
_GROUNDED_AGENT_IDS = frozenset({"market_research", "competitive_analysis"})


def _grounding_for(agent_id: str) -> str | None:
    """Which external source this agent would consult before prompting.

    `competitive_analysis` resolves dynamically via `select_provider()`
    (Places/OSM when either is on); `market_research` uses Serper when the
    feature flag is on; the other 19 agents have no external grounding.
    """
    if agent_id not in _GROUNDED_AGENT_IDS:
        return None
    if agent_id == "market_research":
        return "serper" if settings.serper_available else None
    provider = select_provider()
    return provider.name if provider is not None else None


def build_agent_roster(active_departments: tuple[Department, ...]) -> list[dict]:
    """The flattened, ordered view of `describe_all_departments()` filtered to
    ACTIVE departments - one entry per agent, values read from that agent's
    `AgentSpec`. No topology is re-derived (phases.md Phase 2 step 4)."""
    active = set(active_departments)
    roster: list[dict] = []
    for department, stages in DEPARTMENT_STAGES.items():
        if department not in active:
            continue
        for stage_index, stage in enumerate(stages, start=1):
            for agent in stage:
                roster.append(
                    {
                        "agent_id": agent.spec.agent_id,
                        "department": department.value,
                        "feature": agent.spec.feature,
                        "department_stage": stage_index,
                        "execution": "parallel" if len(stage) > 1 else "sequential",
                        "tier": agent.spec.tier.value,
                        "max_tokens": agent.spec.max_tokens,
                        "grounding": _grounding_for(agent.spec.agent_id),
                    }
                )
    return roster


# =============================================================================
# Inferences - the AgentOS pattern adapted to hybrid extraction (design.md §6)
# =============================================================================


def build_inferences(prompt: str, intent: BusinessIntent | None, intent_source: str) -> list[dict]:
    """One entry per key intent field with its derivation status.

    Recomputed at read time from the stored intent + prompt + intent_source,
    so it can never disagree with the stored intent, needs no extra LLM call,
    and needs no new column (design.md §6). Re-runs the deterministic parsers
    (`find_locality`, `classify_sector`, `parse_budget`) for provenance.
    """
    if intent is None:
        return []

    from app.intent.budget_parser import parse_budget
    from app.intent.location_parser import find_locality
    from app.intent.taxonomy import classify_sector, fallback_business_type

    inferences: list[dict] = []
    keyword_sector, matched_keyword = classify_sector(prompt)
    fallback_type, _ = fallback_business_type(prompt, matched_keyword)

    # business_type - carries the intent's confidence; produced by the LLM or
    # by the keyword fallback (which also fills in when an available LLM
    # declines to name a type). Provenance is derived by comparing the stored
    # value against the fallback derivation.
    if intent.business_type and intent.business_type != "unspecified":
        sources: list[str] = []
        rationale_parts: list[str] = []
        if intent_source == "llm" and intent.business_type != fallback_type:
            sources.append("llm")
            rationale_parts.append("LLM extraction")
        if intent.business_type == fallback_type:
            sources.append("keyword_fallback")
            rationale_parts.append("matches the keyword fallback derivation")
        if not sources:
            sources = ["keyword_fallback"]
            rationale_parts.append("keyword fallback")
        inferences.append(
            {
                "label": "business_type",
                "value": intent.business_type,
                "confidence": intent.confidence,
                "status": "inferred",
                "rationale": "; ".join(rationale_parts),
                "sourceLabels": sources,
            }
        )
    else:
        inferences.append(_needs_confirmation("business_type", "prompt does not name a business type"))

    # budget - deterministic parser first, then LLM hint backup.
    parsed_budget = parse_budget(prompt)
    if intent.budget.specified and intent.budget.amount > 0:
        if parsed_budget.specified:
            rationale = f"parsed deterministically from '{parsed_budget.raw}'"
            sources = ["budget_parser"]
        else:
            rationale = f"parsed from LLM-quoted budget text '{intent.budget.raw}'"
            sources = ["budget_parser", "llm"]
        inferences.append(
            {
                "label": "budget",
                "value": intent.budget.display,
                "confidence": None,
                "status": "confirmed",
                "rationale": rationale,
                "sourceLabels": sources,
            }
        )
    else:
        inferences.append(_needs_confirmation("budget", "prompt states no budget"))

    # location_area - gazetteer first, then LLM hint backup.
    locality = find_locality(prompt)
    if intent.location.area != "unspecified":
        if locality is not None:
            inferences.append(
                {
                    "label": "location_area",
                    "value": intent.location.area,
                    "confidence": None,
                    "status": "confirmed",
                    "rationale": f"gazetteer match on '{locality[1]}'",
                    "sourceLabels": ["gazetteer"],
                }
            )
        else:
            inferences.append(
                {
                    "label": "location_area",
                    "value": intent.location.area,
                    "confidence": None,
                    "status": "inferred",
                    "rationale": f"LLM-suggested area '{intent.location.area}'",
                    "sourceLabels": ["llm"],
                }
            )
    else:
        inferences.append(_needs_confirmation("location_area", "prompt mentions no locality"))

    # sector - LLM extraction or keyword vote, corroborated when both agree.
    if intent.sector.value != "unspecified":
        if intent_source == "llm":
            sources = ["llm"]
            rationale = "LLM-suggested sector"
        else:
            sources = ["keyword_vote"]
            rationale = "keyword vote"
        if keyword_sector == intent.sector:
            sources = [*sources, "keyword_vote"]
            rationale = f"{rationale}; keyword vote agrees ('{matched_keyword}')"
        inferences.append(
            {
                "label": "sector",
                "value": intent.sector.value,
                "confidence": None,
                "status": "inferred",
                "rationale": rationale,
                "sourceLabels": sources,
            }
        )
    else:
        inferences.append(_needs_confirmation("sector", "prompt does not determine a sector"))

    return inferences


def _needs_confirmation(label: str, rationale: str) -> dict:
    """The `needs-confirmation` shape shared by all four fields (§6)."""
    return {
        "label": label,
        "value": None,
        "confidence": None,
        "status": "needs-confirmation",
        "rationale": rationale,
        "sourceLabels": [],
    }


def _unspecified_field_warnings(inferences: list[dict]) -> list[str]:
    """§7: one-to-one with `needs-confirmation` inferences - the visible
    string and the structured payload can never disagree."""
    return [
        f"prompt lacks {entry['label']} - {entry['rationale']}"
        for entry in inferences
        if entry["status"] == "needs-confirmation"
    ]

# =============================================================================
# Readiness (design.md §7)
# =============================================================================


def _database_ok() -> bool:
    """The `/health`-style `SELECT 1` ping (main.py health route pattern)."""
    try:
        with sqlite.connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:  # noqa: BLE001 - health checks report, never raise
        return False


def _blockers(availability: dict[str, bool], database_ok: bool) -> list[str]:
    """Only the two conditions that make a run impossible (design.md §7).
    Missing external-API keys are warnings, never blockers."""
    blockers: list[str] = []
    if not any(availability.values()):
        blockers.append(
            "every LLM provider unavailable (no Groq key, no Gemini key, "
            "Ollama unreachable) - the run cannot make a single model call"
        )
    if not database_ok:
        blockers.append("database unreachable (cannot persist the run)")
    return blockers

# =============================================================================
# build_report
# =============================================================================


async def build_report(
    prompt: str,
    *,
    force_all: bool = False,
    client: LLMClient | None = None,
) -> dict:
    """Build and persist one planning report; returns the stored row.

    At most ONE LLM call (the intent classification). PromptValidationError
    propagates to the route (422). Everything else is composed from the
    generation layer's existing primitives (phases.md Phase 2).
    """
    active_client = client or llm_client

    # 1. Validation (raises PromptValidationError -> 422 at the route).
    cleaned = validate_prompt(prompt)

    # 2. Provider availability snapshot - collected BEFORE classification,
    #    because the classifier's heuristic fallback fires only when every
    #    provider is unavailable, and the report must flag that path.
    availability = await _provider_availability(active_client)

    # 3. Classification - at most one LLM call.
    intent = await classify_intent(cleaned, client=active_client)
    intent_source = _intent_source(availability)

    # 4. Routing + topology (read-only composition; nothing is altered).
    decision = resolve_departments(intent, force_all=force_all)
    routing = describe_graph(decision)
    agents = build_agent_roster(decision.active)

    # 5. Inferences (recomputed at read time; no extra LLM call, no column).
    inferences = build_inferences(cleaned, intent, intent_source)

    # 6. Estimates - upper bounds, never predictions (design.md §4, §6).
    estimated_agent_calls = len(agents)
    estimated_max_tokens = INTENT_MAX_TOKENS + sum(a["max_tokens"] for a in agents)

    # 7. Readiness - hard blockers only (§7).
    database_ok = _database_ok()
    blockers = _blockers(availability, database_ok)
    warnings = list(settings.warnings())
    if intent_source == "heuristic":
        warnings.append(
            "intent came from the keyword heuristic (every provider unavailable) "
            "- low confidence"
        )
    if force_all:
        warnings.append(
            "force_all_departments engaged - 21 agents will run, not 17 "
            "(RQ2 control arm spend)"
        )
    warnings.extend(_unspecified_field_warnings(inferences))

    # 8. Persist the final verdict. No `pending` row is ever stored.
    record = store.create_report(
        raw_prompt=cleaned,
        intent=intent.model_dump(mode="json"),
        intent_source=intent_source,
        status="blocked" if blockers else "ready",
        blockers=blockers,
        warnings=warnings,
        routing=routing,
        agents=agents,
        active_departments=[d.value for d in decision.active],
        skipped_departments=[d.value for d in decision.skipped],
        estimated_agent_calls=estimated_agent_calls,
        estimated_max_completion_tokens=estimated_max_tokens,
    )

    log.info(
        "planning.report_created",
        report_id=record["id"],
        status=record["status"],
        intent_source=intent_source,
        agents=estimated_agent_calls,
        blockers=len(blockers),
        warnings=len(warnings),
    )
    return record

# =============================================================================
# API view shaping (design.md §6)
# =============================================================================


def _expires_at(created_at: str) -> str:
    created = datetime.fromisoformat(created_at)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return (created + timedelta(hours=REPORT_TTL_HOURS)).isoformat()


def to_api_view(record: dict) -> dict:
    """Shape the stored row into the design.md §6 payload: rename raw_prompt
    -> prompt, attach expires_at, and recompute the read-time inferences so
    they can never disagree with the stored intent."""
    intent = (
        BusinessIntent.model_validate(record["intent"]) if record.get("intent") else None
    )
    inferences = build_inferences(
        record["raw_prompt"], intent, record["intent_source"]
    )
    return {
        "id": record["id"],
        "status": record["status"],
        "created_at": record["created_at"],
        "expires_at": _expires_at(record["created_at"]),
        "prompt": record["raw_prompt"],
        "intent": record["intent"],
        "intent_source": record["intent_source"],
        "inferences": inferences,
        "routing": record["routing"],
        "agents": record["agents"],
        "active_departments": record["active_departments"],
        "skipped_departments": record["skipped_departments"],
        "estimates": {
            "intent_llm_calls": 1 if record["intent_source"] == "llm" else 0,
            "agent_llm_calls": record["estimated_agent_calls"],
            "max_completion_tokens": record["estimated_max_completion_tokens"],
        },
        "blockers": record["blockers"],
        "warnings": record["warnings"],
        "confirmed_at": record["confirmed_at"],
        "confirmed_by": record["confirmed_by"],
        "executed_at": record["executed_at"],
        "executed_session_id": record["executed_session_id"],
    }
