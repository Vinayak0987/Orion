"""Planning API routes (design.md §8, phases.md Phase 3).

Thin wrappers over `app.planning.service` and `app.planning.store`, following
the operating router's rule: no business logic here - every route calls one
existing function and shapes the result.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.planning import store
from app.planning.service import build_report, to_api_view

router = APIRouter(prefix="/planning", tags=["planning"])


class CreateReportRequest(BaseModel):
    prompt: str = Field(min_length=1)
    force_all_departments: bool = False


class ConfirmRequest(BaseModel):
    by: str = "operator"


# =============================================================================
# POST /planning/reports
# =============================================================================


@router.post("/reports", status_code=status.HTTP_201_CREATED)
async def create_report_route(request: CreateReportRequest) -> dict:
    """Build and persist one planning report (at most one LLM call).

    422 carries the classifier's PromptValidationError message verbatim,
    like `/intent`.
    """
    from app.intent.classifier import PromptValidationError

    try:
        record = await build_report(
            request.prompt, force_all=request.force_all_departments
        )
    except PromptValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return to_api_view(record)


# =============================================================================
# GET /planning/reports
# =============================================================================


@router.get("/reports")
def list_reports_route(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """Summary rows only: id, status, prompt, agent count, created_at."""
    return store.list_reports(limit, offset)


# =============================================================================
# GET /planning/reports/{report_id}
# =============================================================================


@router.get("/reports/{report_id}")
def get_report_route(report_id: str) -> dict:
    record = store.get_report(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Planning report '{report_id}' not found")
    return to_api_view(record)


# =============================================================================
# POST /planning/reports/{report_id}/confirm
# =============================================================================


@router.post("/reports/{report_id}/confirm")
def confirm_report_route(report_id: str, request: ConfirmRequest | None = None) -> dict:
    """ready -> confirmed. Zero LLM calls; re-checks only status and TTL.

    409 when the report is blocked, already confirmed, executed, or expired.
    """
    by = request.by if request is not None else "operator"
    try:
        confirmed = store.confirm_report(report_id, by=by)
    except store.IllegalTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if confirmed is None:
        raise HTTPException(status_code=404, detail=f"Planning report '{report_id}' not found")
    return to_api_view(confirmed)
