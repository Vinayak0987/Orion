"""Execution-plan API routes (Planner Subsystem, Step 6).

Thin wrappers over compile.py / plan_store.py / executor.py, following the
existing planning router's rule: no business logic in a handler - every route
calls one existing function and shapes the result.

    POST /planning/plans              compile a plan from a CONFIRMED report (409 otherwise)
    GET  /planning/plans              list plan summaries
    GET  /planning/plans/{id}         full plan (nodes + statuses)
    POST /planning/plans/{id}/run     execute the plan (reuses orchestrate)
    GET  /planning/plans/{id}/events  the append-only execution trace
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.llm.chain import llm_client
from app.planning import plan_store, store
from app.planning.compile import compile_plan
from app.planning.executor import BudgetError, run_plan

router = APIRouter(prefix="/planning", tags=["planning"])


class CreatePlanRequest(BaseModel):
    report_id: str = Field(min_length=1)


# =============================================================================
# POST /planning/plans - compile from a confirmed report
# =============================================================================


@router.post("/plans", status_code=status.HTTP_201_CREATED)
def create_plan_route(request: CreatePlanRequest) -> dict:
    """Compile a confirmed report into an ExecutionPlan and persist it.

    404 if the report is unknown; 409 unless the report is 'confirmed' - a plan
    may only be built from a report the operator has explicitly approved.
    """
    report = store.get_report(request.report_id)
    if report is None:
        raise HTTPException(
            status_code=404, detail=f"Planning report '{request.report_id}' not found"
        )
    if report["status"] != "confirmed":
        raise HTTPException(
            status_code=409,
            detail=(
                f"report '{request.report_id}' is '{report['status']}' - only a "
                "confirmed report can be compiled into an execution plan"
            ),
        )
    plan = compile_plan(report)
    plan_store.create_plan(plan)
    return plan.model_dump(mode="json")


# =============================================================================
# GET /planning/plans
# =============================================================================


@router.get("/plans")
def list_plans_route(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """Summary rows only: id, report_id, status, prompt, node count, created_at."""
    return plan_store.list_plans(limit, offset)


# =============================================================================
# GET /planning/plans/{plan_id}
# =============================================================================


@router.get("/plans/{plan_id}")
def get_plan_route(plan_id: str) -> dict:
    plan = plan_store.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Execution plan '{plan_id}' not found")
    return plan.model_dump(mode="json")


# =============================================================================
# POST /planning/plans/{plan_id}/run
# =============================================================================


@router.post("/plans/{plan_id}/run")
async def run_plan_route(plan_id: str) -> dict:
    """Execute the plan (reusing orchestrate). Returns the plan with node
    statuses filled in. 404 unknown; 409 if the plan is not runnable or the
    token estimate exceeds the policy ceiling."""
    plan = plan_store.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Execution plan '{plan_id}' not found")
    if plan.status not in ("draft", "ready"):
        raise HTTPException(
            status_code=409,
            detail=f"plan '{plan_id}' is '{plan.status}' - only a draft/ready plan can run",
        )
    try:
        result = await run_plan(plan, client=llm_client, persist=True)
    except BudgetError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result.model_dump(mode="json")


# =============================================================================
# GET /planning/plans/{plan_id}/events
# =============================================================================


@router.get("/plans/{plan_id}/events")
def plan_events_route(plan_id: str) -> list[dict]:
    """The append-only execution trace for a plan (oldest first)."""
    if plan_store.get_plan(plan_id) is None:
        raise HTTPException(status_code=404, detail=f"Execution plan '{plan_id}' not found")
    return plan_store.get_events(plan_id)
