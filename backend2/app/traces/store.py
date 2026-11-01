"""Execution traces store — MongoDB-backed.

Every LLM call and tool call the Executor makes writes one row here. This is the
single source of truth for Observability (Phase 5) and Agent Performance.
"""

from __future__ import annotations

import json
import uuid

from app.auth import store as auth_store


def record_llm(mission_id: str, task_id: str, agent_id: str, *, provider: str, model: str,
               input_tokens: int, output_tokens: int, cost_usd: float, latency_ms: int,
               success: bool, error: str | None = None) -> None:
    trace_id = uuid.uuid4().hex
    auth_store.create_execution_trace(
        trace_id=trace_id,
        mission_id=mission_id,
        task_id=task_id,
        agent_id=agent_id,
        trace_type="llm",
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        success=success,
        error_message=error,
    )


def record_tool(mission_id: str, task_id: str, agent_id: str, *, tool_name: str,
                tool_input: dict, tool_output: dict, latency_ms: int, success: bool,
                error: str | None = None) -> None:
    trace_id = uuid.uuid4().hex
    auth_store.create_execution_trace(
        trace_id=trace_id,
        mission_id=mission_id,
        task_id=task_id,
        agent_id=agent_id,
        trace_type="tool",
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        latency_ms=latency_ms,
        success=success,
        error_message=error,
    )


def list_traces(mission_id: str) -> list[dict]:
    traces = auth_store.get_execution_traces(mission_id)
    # Convert success from int to bool for API compatibility
    for trace in traces:
        trace["success"] = bool(trace.get("success", 1))
    return traces


def delete_traces(mission_id: str) -> int:
    """Delete all traces for a mission."""
    return auth_store.delete_execution_traces(mission_id)
