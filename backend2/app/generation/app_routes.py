"""HTTP routes for the v1 generation pipeline.

These endpoints were originally defined inline in the v1 ``app.main`` module.
They are repackaged here as an ``APIRouter`` so the v2 application can mount the
whole generation surface with ``app.include_router(generation_router)``.

Routes: /health-gen, /intent, /generate, /sections, /sessions*, /ws/generate.
(The health route is renamed to avoid clashing with the v2 /health route.)
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.generation.apis.cache import knowledge_cache
from app.generation.apis.places import select_provider
from app.generation.config import settings
from app.generation.db import sqlite
from app.generation.intent import PromptValidationError, classify_intent
from app.generation.llm.chain import llm_client
from app.generation.output import (
    SECTION_ORDER,
    SECTIONS_BY_KEY,
    BusinessPackage,
    GenerationMetadata,
    PdfUnavailable,
    describe_sections,
    pdf_health,
    render_html,
    render_pdf,
)
from app.generation.orchestrator import (
    ProgressEvent,
    describe_graph,
    orchestrate,
    resolve_departments,
    run_summary,
)

log = structlog.get_logger(__name__)

router = APIRouter(tags=["generation"])


# =============================================================================
# F64 - health check (generation layer)
# =============================================================================


class HealthResponse(BaseModel):
    status: str = Field(description="ok | degraded")
    env: str
    database: str
    llm_providers: dict
    external_apis: dict
    knowledge_cache: dict
    pdf_export: dict
    grounding: dict
    feature_flags: dict
    warnings: list[str]


@router.get("/health-gen", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    try:
        with sqlite.connection() as conn:
            conn.execute("SELECT 1").fetchone()
        database = "ok"
    except Exception as exc:  # noqa: BLE001 - health must never raise
        database = f"error: {exc}"

    providers = await llm_client.health()
    any_llm = any(p["available"] for p in providers.values())

    places_provider = select_provider()

    return HealthResponse(
        status="ok" if (any_llm and database == "ok") else "degraded",
        env=settings.app_env,
        database=database,
        llm_providers=providers,
        external_apis={
            "google_places": {
                "configured": settings.places_available,
                "note": "$200/month free credit, billing account required",
            },
            "serper": {
                "configured": settings.serper_available,
                "note": "2500 searches/month free, no card required",
            },
            "openstreetmap": {
                "configured": settings.enable_overpass,
                "note": "no key required; sparser Indian coverage, no ratings",
            },
        },
        knowledge_cache=knowledge_cache.health(),
        pdf_export=pdf_health(),
        grounding={
            "competitor_source": places_provider.name if places_provider else "llm_inferred",
            "market_research_source": "serper" if settings.serper_available else "llm_inferred",
            "rq3_arm": "grounded" if places_provider is not None else "text_only",
        },
        feature_flags={
            "places_api": settings.enable_places_api,
            "overpass": settings.enable_overpass,
            "serper_api": settings.enable_serper_api,
            "chroma_cache": settings.enable_chroma_cache,
            "dynamic_routing": settings.enable_dynamic_routing,
        },
        warnings=settings.warnings(),
    )


# =============================================================================
# F1/F2 - intent classification
# =============================================================================


class IntentRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=1000,
        description="Free-form business prompt",
        examples=["Ice cream shop in Andheri, Rs 15L budget"],
    )


@router.post("/intent", tags=["intent"])
async def classify(request: IntentRequest) -> dict:
    try:
        intent = await classify_intent(request.prompt)
    except PromptValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    decision = resolve_departments(intent)
    return {
        "intent": intent.model_dump(mode="json"),
        "derived": {
            "budget_display": intent.budget.display if intent.budget.specified else None,
            "scale": intent.scale.value,
            "places_query": intent.location.query_string,
            "active_departments": [d.value for d in decision.active],
            "skipped_departments": [d.value for d in decision.skipped],
        },
        "execution_plan": describe_graph(decision),
    }


# =============================================================================
# F10-F13 - full generation pipeline
# =============================================================================


class GenerateRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=1000,
        examples=["Ice cream shop in Andheri, Rs 15L budget"],
    )
    force_all_departments: bool = Field(
        default=False,
        description="Run every department regardless of intent. This is the RQ2 "
        "control arm; leave false for normal dynamic routing.",
    )


@router.post("/generate", tags=["generate"])
async def generate(request: GenerateRequest) -> dict:
    try:
        state = await orchestrate(
            request.prompt, force_all_departments=request.force_all_departments
        )
    except PromptValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    decision = resolve_departments(
        state["intent"], force_all=request.force_all_departments
    )
    return run_summary(state, decision)


# =============================================================================
# F42-F46 - output layer
# =============================================================================


def _load_state_or_404(session_id: str):
    record = sqlite.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    if not record.get("plan"):
        raise HTTPException(
            status_code=409,
            detail=f"Session '{session_id}' has status '{record['status']}' and no stored plan",
        )
    return record


@router.get("/sections", tags=["output"])
async def list_section_catalogue() -> dict:
    return {"count": len(SECTION_ORDER), "sections": describe_sections()}


@router.get("/sessions/{session_id}/package", tags=["output"])
async def get_package(session_id: str) -> dict:
    record = _load_state_or_404(session_id)
    return {
        "session_id": session_id,
        "business_name": (record.get("plan") or {}).get("branding", {}).get(
            "recommended_name"
        )
        or (record.get("intent") or {}).get("business_type_label")
        or "Untitled Business",
        "prompt": record["raw_prompt"],
        "intent": record.get("intent") or {},
        "plan": record.get("plan") or {},
        "metadata": record.get("metadata") or {},
    }


@router.get("/sessions/{session_id}/sections/{section_key}", tags=["output"])
async def get_section(session_id: str, section_key: str) -> dict:
    spec = SECTIONS_BY_KEY.get(section_key)
    if spec is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown section '{section_key}'. Valid keys: {', '.join(SECTION_ORDER)}",
        )

    record = _load_state_or_404(session_id)
    department = (record.get("plan") or {}).get(spec.department.value) or {}
    payload = {name: department.get(name) for name in spec.fields if name in department}

    if not payload:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' has no content for section '{section_key}'",
        )

    return {
        "session_id": session_id,
        "key": spec.key,
        "title": spec.title,
        "department": spec.department.value,
        "features": list(spec.features),
        "data": payload,
    }


@router.get("/sessions/{session_id}/report", response_class=HTMLResponse, tags=["output"])
async def get_html_report(session_id: str) -> HTMLResponse:
    html = _render_report(session_id)
    return HTMLResponse(content=html)


@router.get("/sessions/{session_id}/report.pdf", tags=["output"])
async def get_pdf_report(session_id: str) -> Response:
    html = _render_report(session_id)
    try:
        pdf, backend = render_pdf(html)
    except PdfUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    filename = f"mabgp-business-plan-{session_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-PDF-Backend": backend,
        },
    )


def _render_report(session_id: str) -> str:
    record = _load_state_or_404(session_id)
    plan = record.get("plan") or {}
    metadata = record.get("metadata") or {}

    sections: dict[str, dict] = {}
    for key in SECTION_ORDER:
        spec = SECTIONS_BY_KEY[key]
        department = plan.get(spec.department.value) or {}
        payload = {
            name: department.get(name)
            for name in spec.fields
            if department.get(name) not in (None, [], "", {})
        }
        if payload:
            sections[key] = payload

    package = BusinessPackage(
        session_id=session_id,
        business_name=(plan.get("branding") or {}).get("recommended_name")
        or (record.get("intent") or {}).get("business_type_label")
        or "Untitled Business",
        prompt=record["raw_prompt"],
        intent=record.get("intent") or {},
        sections=sections,
        metadata=GenerationMetadata(
            session_id=session_id,
            status=record.get("status", "unknown"),
            generated_at=record.get("completed_at") or record.get("created_at") or "",
            total_duration_ms=record.get("total_duration_ms"),
            completeness_score=record.get("completeness_score"),
            total_tokens=record.get("total_tokens") or 0,
            active_departments=record.get("active_departments") or [],
            skipped_departments=record.get("skipped_departments") or [],
            routing_reason=metadata.get("routing_reason", ""),
            validation_warnings=metadata.get("validation_warnings") or [],
        ),
    )
    return render_html(package)


# =============================================================================
# F48 - live generation over WebSocket
# =============================================================================


@router.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        request = await websocket.receive_json()
    except (WebSocketDisconnect, ValueError):
        await websocket.close()
        return

    prompt = str(request.get("prompt", ""))
    force_all = bool(request.get("force_all_departments", False))

    async def send_event(event: ProgressEvent) -> None:
        payload = event.model_dump(mode="json")
        payload["percent"] = event.percent
        await websocket.send_json(payload)

    try:
        state = await orchestrate(
            prompt,
            force_all_departments=force_all,
            progress_callback=send_event,
        )
        decision = resolve_departments(state["intent"], force_all=force_all)
        await websocket.send_json(
            {"event": "result", "summary": run_summary(state, decision)}
        )
    except PromptValidationError as exc:
        await websocket.send_json({"event": "error", "detail": str(exc), "kind": "validation"})
    except WebSocketDisconnect:
        log.info("ws.client_disconnected")
        return
    except Exception as exc:  # noqa: BLE001 - report, never crash the socket
        log.error("ws.generate_failed", error=str(exc)[:300])
        await websocket.send_json(
            {"event": "error", "detail": str(exc)[:400], "kind": "generation"}
        )

    try:
        await websocket.close()
    except RuntimeError:
        pass


# =============================================================================
# F51 - session history
# =============================================================================


class SessionSummary(BaseModel):
    id: str
    raw_prompt: str
    status: str
    completeness_score: float | None = None
    total_duration_ms: int | None = None
    created_at: str
    completed_at: str | None = None


@router.get("/sessions", response_model=list[SessionSummary], tags=["sessions"])
async def list_sessions(limit: int = 50, offset: int = 0) -> list[SessionSummary]:
    limit = max(1, min(limit, 200))
    return [SessionSummary(**row) for row in sqlite.list_sessions(limit, offset)]


@router.get("/sessions/{session_id}", tags=["sessions"])
async def get_session(session_id: str) -> dict:
    record = sqlite.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return record


@router.delete("/sessions/{session_id}", tags=["sessions"])
async def delete_session(session_id: str) -> dict:
    if not sqlite.delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"deleted": session_id}
