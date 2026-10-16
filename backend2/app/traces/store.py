"""Execution traces store — write-only during Phase 1.

Every LLM call and tool call the Executor makes writes one row here. This is the
single source of truth for Observability (Phase 5) and Agent Performance.
"""

from __future__ import annotations

import json
import uuid

from app.db.sqlite import _now, connection


def record_llm(mission_id: str, task_id: str, agent_id: str, *, provider: str, model: str,
               input_tokens: int, output_tokens: int, cost_usd: float, latency_ms: int,
               success: bool, error: str | None = None) -> None:
    _insert(
        mission_id, task_id, agent_id, trace_type="llm", provider=provider, model=model,
        input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost_usd,
        latency_ms=latency_ms, success=success, error_message=error,
    )


def record_tool(mission_id: str, task_id: str, agent_id: str, *, tool_name: str,
                tool_input: dict, tool_output: dict, latency_ms: int, success: bool,
                error: str | None = None) -> None:
    _insert(
        mission_id, task_id, agent_id, trace_type="tool", tool_name=tool_name,
        tool_input=json.dumps(tool_input), tool_output=json.dumps(tool_output)[:4000],
        latency_ms=latency_ms, success=success, error_message=error,
    )


def _insert(mission_id, task_id, agent_id, **fields) -> None:
    cols = {
        "id": uuid.uuid4().hex,
        "mission_id": mission_id,
        "task_id": task_id,
        "agent_id": agent_id,
        "provider": None, "model": None, "input_tokens": None, "output_tokens": None,
        "cost_usd": None, "tool_name": None, "tool_input": None, "tool_output": None,
        "latency_ms": None, "error_message": None,
        "created_at": _now(),
    }
    cols.update(fields)
    cols["success"] = 1 if cols.get("success") else 0
    keys = ", ".join(cols.keys())
    marks = ", ".join("?" for _ in cols)
    with connection() as conn:
        conn.execute(
            f"INSERT INTO execution_traces ({keys}) VALUES ({marks})",  # noqa: S608 - static keys
            tuple(cols.values()),
        )


def list_traces(mission_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM execution_traces WHERE mission_id = ? ORDER BY created_at", (mission_id,)
        ).fetchall()
    return [dict(r) for r in rows]
