"""Operating-layer API routes.

Thin wrappers over existing functions in `app.operating.*`. No business logic here
— every route is a GET or POST calling one existing function and shaping the result.

Added to `app.main.app` via `include_router` rather than inline, because main.py is
already 400 lines of generation-layer endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.operating import (
    anchors,
    constitution,
    departments,
    governance,
    ledger,
    loops,
    memory,
    monitoring,
    scheduler,
)
from app.operating.anchors import AnchorSet
from app.operating.governance import (
    Decision,
    DecisionState,
    IllegalTransition,
    get_decision_row,
)
from app.operating.ledger import LedgerEntry

router = APIRouter(prefix="/operating", tags=["operating"])


# =============================================================================
# GET /operating/anchors
# =============================================================================


@router.get("/anchors")
def get_anchors(company_id: str = Query(...)) -> dict[str, Any]:
    """Current anchor set, computed from the ledger."""
    anchor_set = AnchorSet.compute(company_id)
    return {
        "company_id": company_id,
        "entry_count": anchor_set.entry_count,
        "is_thin": anchor_set.is_thin,
        "anchors": {
            name: {
                "name": a.name,
                "value": a.value,
                "unit": a.unit,
                "entries": a.entries,
                "thin": a.thin,
                "note": a.note,
            }
            for name, a in anchor_set.anchors.items()
        },
    }


# =============================================================================
# GET /operating/anchors/history
# =============================================================================


@router.get("/anchors/history")
def get_anchor_history(
    company_id: str = Query(...),
    points: int = Query(default=30, ge=2, le=100),
) -> dict[str, Any]:
    """Anchor values sampled at evenly spaced ledger positions.

    Used by the trend chart. Returns `points` samples from the ledger, each being
    the anchor set computed up to that sequence number. No anchor values are stored;
    they are recomputed here.
    """
    entries = ledger.read(company_id)
    if not entries:
        return {"company_id": company_id, "points": 0, "series": {}}

    seqs = [e.seq or 0 for e in entries]
    max_seq = max(seqs)
    if max_seq == 0:
        return {"company_id": company_id, "points": 0, "series": {}}

    # Sample at evenly spaced sequence numbers
    step = max(1, max_seq // points)
    sample_points = list(range(step, max_seq + 1, step))
    if sample_points and sample_points[-1] != max_seq:
        sample_points.append(max_seq)

    series: dict[str, list[dict]] = {}
    for seq in sample_points:
        subset = [e for e in entries if (e.seq or 0) <= seq]
        anchor_set = AnchorSet.compute(company_id, subset)
        for name, a in anchor_set.anchors.items():
            if a.value is not None:
                series.setdefault(name, []).append({
                    "seq": seq,
                    "value": a.value,
                    "entries": a.entries,
                })

    return {"company_id": company_id, "points": len(sample_points), "series": series}


# =============================================================================
# GET /operating/findings
# =============================================================================


@router.get("/findings")
def get_findings(
    company_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    """Open findings, worst severity first."""
    return monitoring.open_findings(company_id, limit=limit)


# =============================================================================
# GET /operating/decisions
# =============================================================================


@router.get("/decisions")
def get_decisions(
    company_id: str = Query(...),
    state: str | None = Query(default=None),
) -> list[dict]:
    """Decisions, optionally filtered by state."""
    if state == "pending_review":
        return governance.review_queue(company_id)
    from app.db.sqlite import connection
    sql = "SELECT * FROM decisions WHERE company_id = ?"
    params: list[Any] = [company_id]
    if state:
        sql += " AND state = ?"
        params.append(state)
    sql += " ORDER BY created_at DESC"
    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# =============================================================================
# POST /operating/decisions/{id}/approve
# =============================================================================


class ApproveRequest(BaseModel):
    by: str = Field(..., min_length=1, description="Name of the human approving")


@router.post("/decisions/{decision_id}/approve")
def approve_decision(decision_id: str, body: ApproveRequest) -> dict:
    """Approve a pending decision. Requires a named human."""
    row = get_decision_row(decision_id)
    if row is None:
        raise HTTPException(404, f"decision '{decision_id}' not found")
    if row["state"] != str(DecisionState.PENDING_REVIEW):
        raise HTTPException(
            422, f"decision is '{row['state']}', not pending_review")
    decision = _row_to_decision(row)
    try:
        governance.approve(decision, by=body.by)
    except (ValueError, IllegalTransition) as exc:
        raise HTTPException(422, str(exc)) from exc
    return _decision_dict(decision_id)


# =============================================================================
# POST /operating/decisions/{id}/reject
# =============================================================================


class RejectRequest(BaseModel):
    by: str = Field(..., min_length=1)
    reason: str = Field(default="")


@router.post("/decisions/{decision_id}/reject")
def reject_decision(decision_id: str, body: RejectRequest) -> dict:
    row = get_decision_row(decision_id)
    if row is None:
        raise HTTPException(404, f"decision '{decision_id}' not found")
    if row["state"] != str(DecisionState.PENDING_REVIEW):
        raise HTTPException(
            422, f"decision is '{row['state']}', not pending_review")
    decision = _row_to_decision(row)
    try:
        governance.reject(decision, by=body.by, reason=body.reason)
    except (ValueError, IllegalTransition) as exc:
        raise HTTPException(422, str(exc)) from exc
    return _decision_dict(decision_id)


# =============================================================================
# POST /operating/decisions/{id}/return
# =============================================================================


class ReturnRequest(BaseModel):
    by: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)


@router.post("/decisions/{decision_id}/return")
def return_decision(decision_id: str, body: ReturnRequest) -> dict:
    row = get_decision_row(decision_id)
    if row is None:
        raise HTTPException(404, f"decision '{decision_id}' not found")
    if row["state"] != str(DecisionState.PENDING_REVIEW):
        raise HTTPException(
            422, f"decision is '{row['state']}', not pending_review")
    decision = _row_to_decision(row)
    try:
        governance.return_for_revision(decision, by=body.by, reason=body.reason)
    except (ValueError, IllegalTransition) as exc:
        raise HTTPException(422, str(exc)) from exc
    return _decision_dict(decision_id)


# =============================================================================
# GET /operating/audit/{decision_id}
# =============================================================================


@router.get("/audit/{decision_id}")
def get_audit(decision_id: str) -> list[dict]:
    """Ordered audit trail for one decision."""
    rows = governance.audit_for(decision_id)
    if not rows:
        raise HTTPException(404, f"no audit entries for '{decision_id}'")
    return rows


# =============================================================================
# GET /operating/constitution
# =============================================================================


@router.get("/constitution")
def get_constitution() -> list[dict]:
    """The 7 hard constraints. Code, not settings."""
    return constitution.describe()


# =============================================================================
# GET /operating/loops
# =============================================================================


@router.get("/loops")
def get_loops() -> dict:
    """The control topology: loops, edges, cycles, validity."""
    return loops.default_graph().describe()


# =============================================================================
# GET /operating/schedule
# =============================================================================


@router.get("/schedule")
def get_schedule(company_id: str = Query(...)) -> list[dict]:
    """Per-loop cadence state."""
    from app.operating import build_scheduler
    sched = build_scheduler()
    return sched.status(company_id)


# =============================================================================
# GET /operating/runs
# =============================================================================


@router.get("/runs")
def get_runs(
    company_id: str = Query(...),
    loop_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    """Loop run history, newest first."""
    return scheduler.run_history(company_id, loop_id=loop_id, limit=limit)


# =============================================================================
# GET /operating/ledger
# =============================================================================


@router.get("/ledger")
def get_ledger(
    company_id: str = Query(...),
    limit: int = Query(default=100, ge=1, le=5000),
) -> list[dict]:
    """Ledger tail, newest first. Append-only: no PUT/DELETE exists."""
    entries = ledger.read(company_id)
    # Reverse so newest is first; apply limit
    entries = list(reversed(entries))[:limit]
    return [
        {
            "seq": e.seq,
            "kind": str(e.kind),
            "department": e.department,
            "actor": e.actor,
            "amount_minor": e.amount_minor,
            "quantity": e.quantity,
            "currency": e.currency,
            "occurred_at": e.occurred_at,
            "memo": e.memo,
        }
        for e in entries
    ]


# =============================================================================
# GET /operating/memory
# =============================================================================


@router.get("/memory")
def get_memory(
    company_id: str = Query(...),
    department: str = Query(...),
) -> dict:
    """Typed memory counts and entries for one department."""
    stats = memory.stats(company_id)
    dept_stats = stats.get(department, {})
    # Retrieve recent entries
    from datetime import UTC, datetime
    entries = memory.retrieve(
        company_id, department, "", limit=50,
        now=datetime.now(UTC), record_retrieval=False,
    )
    return {
        "company_id": company_id,
        "department": department,
        "counts": dept_stats,
        "entries": entries,
    }


# =============================================================================
# GET /operating/departments
# =============================================================================


@router.get("/departments")
def get_departments() -> list[dict]:
    """The five department profiles with proxy and anchor."""
    return [
        {
            "name": name,
            "objective": p.objective,
            "proxy_metric": p.proxy_metric,
            "serves_anchor": p.serves_anchor,
            "task_budget_minor": p.task_budget_minor,
        }
        for name, p in departments.PROFILES.items()
    ]


# =============================================================================
# POST /operating/tick
# =============================================================================


class TickRequest(BaseModel):
    company_id: str = Field(..., min_length=1)


@router.post("/tick")
def manual_tick(body: TickRequest) -> list[dict]:
    """Run due loops once. Manual trigger for demonstrations.

    The real driver is the scheduler; this is the inspection/demo endpoint, not
    "run the business". The frontend should label it as a manual tick.
    """
    from app.operating import build_scheduler
    sched = build_scheduler()
    runs = sched.run_due(body.company_id)
    return [
        {
            "loop_id": r.loop_id,
            "status": str(r.status),
            "duration_ms": r.duration_ms,
            "detail": r.detail,
        }
        for r in runs
    ]


# =============================================================================
# Helpers
# =============================================================================


def _row_to_decision(row: dict) -> Decision:
    """Reconstruct a Decision from a DB row so governance.approve/reject work."""
    from app.operating.constitution import ActionKind, ProposedAction
    import json

    action = ProposedAction(
        kind=ActionKind(row["action_kind"]),
        department=row["department"],
        actor=row["actor"],
        company_id=row["company_id"],
        amount_minor=row["amount_minor"],
        description=row.get("description", ""),
        payload=json.loads(row["payload_json"]) if row.get("payload_json") else {},
    )
    return Decision(
        id=row["id"],
        action=action,
        state=DecisionState(row["state"]),
        risk=governance.Risk(row["risk"]),
        reason=row.get("reason", ""),
        decided_by=row.get("decided_by"),
    )


def _decision_dict(decision_id: str) -> dict:
    row = get_decision_row(decision_id)
    return dict(row) if row else {}
