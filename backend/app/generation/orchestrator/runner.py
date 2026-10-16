"""F13 - Session and state initialization, plus run finalization.

`orchestrate()` is the single entry point for a full generation run:

    validate prompt (F1)
      -> classify intent (F2)
        -> resolve routing (F10)
          -> build DAG (F11)
            -> stream execution with timeout (F12)
              -> validate + score + persist (F16, F59)

The graph is driven with `astream(stream_mode="values")` rather than `ainvoke()`
so the latest full state snapshot is retained after every superstep. On timeout
that snapshot is what gets returned and persisted, which is what makes F52
partial results real rather than aspirational.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime

import structlog

from app.generation.agents.registry import DepartmentRunner
from app.generation.config import settings
from app.generation.core.logging import bind_session, clear_session
from app.generation.db import sqlite
from app.generation.intent import classify_intent
from app.generation.llm.chain import LLMClient
from app.generation.models.intent import BusinessIntent
from app.generation.models.state import (
    Department,
    RunStatus,
    SharedBusinessState,
    has_content,
    new_state,
)
from app.generation.orchestrator.completeness import detect_contradictions, score_completeness
from app.generation.orchestrator.graph import build_graph, describe_graph
from app.generation.orchestrator.progress import ProgressCallback, ProgressEmitter
from app.generation.orchestrator.routing import RoutingDecision, resolve_departments

log = structlog.get_logger(__name__)


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


async def orchestrate(
    prompt: str,
    *,
    session_id: str | None = None,
    client: LLMClient | None = None,
    force_all_departments: bool = False,
    progress_callback: ProgressCallback | None = None,
    runners: dict[Department, DepartmentRunner] | None = None,
    persist: bool = True,
) -> SharedBusinessState:
    """Run the full multi-agent pipeline for one prompt.

    Args:
        prompt: raw user prompt.
        session_id: reuse an existing id, otherwise one is generated.
        client: LLM client override (tests inject a fake).
        force_all_departments: RQ2 control arm - run all five departments.
        progress_callback: async sink for F12 progress events.
        runners: department runner overrides (tests inject fakes).
        persist: write session rows to SQLite (F59). Off for unit tests.

    Returns:
        The final SharedBusinessState, with metadata.status set to COMPLETED,
        PARTIAL, TIMEOUT or FAILED.

    Raises:
        PromptValidationError: if the prompt fails F1 validation. Raised before
            any LLM call, so no free-tier quota is spent on an invalid prompt.
    """
    sid = session_id or new_session_id()
    bind_session(sid)
    started = time.perf_counter()

    try:
        if persist:
            sqlite.create_session(sid, prompt)

        # --- F2 intent -------------------------------------------------------
        intent = await classify_intent(prompt, client=client)

        # --- F10 routing -----------------------------------------------------
        decision = resolve_departments(intent, force_all=force_all_departments)

        # --- F13 state init --------------------------------------------------
        state = new_state(sid, prompt)
        state["intent"] = intent
        state["metadata"].status = RunStatus.RUNNING
        state["metadata"].active_departments = list(decision.active)
        state["metadata"].skipped_departments = list(decision.skipped)
        state["metadata"].routing_reason = decision.reason

        emitter = ProgressEmitter(sid, len(decision.active), progress_callback)
        await emitter.session_started(prompt)
        await emitter.intent_resolved(
            f"{intent.business_type} / {intent.sector.value} / "
            f"{intent.location.query_string}"
        )
        await emitter.routing_resolved(decision.reason)

        if persist:
            sqlite.update_session(
                sid,
                status=RunStatus.RUNNING.value,
                intent_json=intent.model_dump(mode="json"),
                active_departments=[d.value for d in decision.active],
                skipped_departments=[d.value for d in decision.skipped],
            )

        # --- F11/F12 execution ----------------------------------------------
        graph = build_graph(decision, emitter, runners=runners)
        final_state: SharedBusinessState = state
        timed_out = False

        try:
            async with asyncio.timeout(settings.generation_timeout_seconds):
                async for snapshot in graph.astream(state, stream_mode="values"):
                    final_state = snapshot
        except TimeoutError:
            timed_out = True
            log.warning(
                "orchestrate.timeout",
                seconds=settings.generation_timeout_seconds,
                completed_departments=emitter.completed,
            )

        # --- F16 finalize ----------------------------------------------------
        duration_ms = int((time.perf_counter() - started) * 1000)
        _finalize(final_state, intent, decision, duration_ms, timed_out)

        metadata = final_state["metadata"]
        if metadata.status is RunStatus.TIMEOUT:
            await emitter.session_failed(
                f"timed out after {settings.generation_timeout_seconds}s"
            )
        else:
            await emitter.session_completed(
                f"{metadata.status.value} - completeness {metadata.completeness_score}%"
            )

        if persist:
            _persist_final(sid, final_state)

        return final_state

    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        log.error("orchestrate.failed", error=str(exc)[:300], duration_ms=duration_ms)
        if persist:
            sqlite.update_session(
                sid,
                status=RunStatus.FAILED.value,
                total_duration_ms=duration_ms,
                completed_at=datetime.now(UTC).isoformat(),
            )
        raise
    finally:
        clear_session()


def _finalize(
    state: SharedBusinessState,
    intent: BusinessIntent,
    decision: RoutingDecision,
    duration_ms: int,
    timed_out: bool,
) -> None:
    """Populate RunMetadata with the run's verdict. Single-writer, post-graph."""
    metadata = state["metadata"]

    # astream snapshots carry the metadata object created at init; re-assert the
    # routing decision in case a snapshot predates it.
    metadata.active_departments = list(decision.active)
    metadata.skipped_departments = list(decision.skipped)
    metadata.routing_reason = decision.reason

    report = score_completeness(state, decision.active)
    contradictions = detect_contradictions(state, intent)

    metadata.completeness_score = report.score
    metadata.validation_warnings = contradictions + [
        f"missing: {key}" for key in report.missing
    ]
    metadata.total_duration_ms = duration_ms
    metadata.completed_at = datetime.now(UTC).isoformat()

    errors = state.get("errors") or []
    if timed_out:
        metadata.status = RunStatus.TIMEOUT
    elif errors:
        metadata.status = RunStatus.PARTIAL
    elif report.missing:
        # Every department ran, but not every expected field is substantive.
        metadata.status = (
            RunStatus.PARTIAL if report.score < 100.0 else RunStatus.COMPLETED
        )
    else:
        metadata.status = RunStatus.COMPLETED

    log.info(
        "orchestrate.finalized",
        status=metadata.status.value,
        completeness=report.score,
        present=report.present_count,
        expected=report.expected_count,
        contradictions=len(contradictions),
        duration_ms=duration_ms,
        total_tokens=total_tokens(state),
    )


def total_tokens(state: SharedBusinessState) -> int:
    """F58 - token total for the routing-efficiency comparison."""
    return sum(trace.total_tokens for trace in state.get("agent_traces") or [])


def _persist_final(session_id: str, state: SharedBusinessState) -> None:
    metadata = state["metadata"]
    sqlite.update_session(
        session_id,
        status=metadata.status.value,
        plan_json=export_plan(state),
        metadata_json=metadata.model_dump(mode="json"),
        total_tokens=total_tokens(state),
        total_duration_ms=metadata.total_duration_ms,
        completeness_score=metadata.completeness_score,
        completed_at=metadata.completed_at,
    )


def export_plan(state: SharedBusinessState) -> dict:
    """Serialize the department sections of a finished run (precursor to F42).

    Sections with no populated fields are omitted. LangGraph seeds a
    reducer-backed channel with an all-defaults instance, so without this check a
    run where a department produced nothing still stored a full set of empty
    sections - and `/package` then reported a plan that had no content in it.
    """
    plan: dict[str, object] = {}
    for department in Department:
        section = state.get(department.value)
        if has_content(section):
            plan[department.value] = section.model_dump(mode="json")
    return plan


def run_summary(state: SharedBusinessState, decision: RoutingDecision) -> dict:
    """Compact API/CLI view of a completed run."""
    metadata = state["metadata"]
    intent = state.get("intent")
    return {
        "session_id": state["session_id"],
        "status": metadata.status.value,
        "intent": intent.model_dump(mode="json") if intent else None,
        "routing": describe_graph(decision),
        "completeness_score": metadata.completeness_score,
        "validation_warnings": metadata.validation_warnings,
        "total_duration_ms": metadata.total_duration_ms,
        "total_tokens": total_tokens(state),
        "departments_completed": len(
            [t for t in state.get("agent_traces") or [] if t.status == "completed"]
        ),
        "errors": state.get("errors") or [],
        "plan": export_plan(state),
    }
