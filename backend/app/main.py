"""MABGP FastAPI application.

Phase 2 scope: app wiring, health check (F64), session history endpoints (F51).
The /generate pipeline lands in Phase 3-4 once the intent classifier and
orchestrator exist.

SECURITY NOTE: the generation/operating/planning routes are OPEN (no auth) and
are intended to run only on localhost for a research project. Authentication
(app.auth) currently gates the UI, not these APIs. Do not expose this service to
a public network without gating the routes first.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.apis.cache import knowledge_cache
from app.apis.places import select_provider
from app.config import settings
from app.core.logging import configure_logging
from app.db import sqlite
from app.intent import PromptValidationError, classify_intent
from app.llm.chain import llm_client
from app.output import (
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
from app.orchestrator import (
    ProgressEvent,
    describe_graph,
    orchestrate,
    resolve_departments,
    run_summary,
)

log = structlog.get_logger(__name__)

# Import the operating-layer router (added for §5.5)
from app.operating.api import router as operating_router

# Import the authentication router (user/website data layer — MongoDB Atlas).
from app.auth.router import router as auth_router

# Planning Report layer (design.md §8) - the pre-execution flow.
from app.planning import init_planning
from app.planning.api import router as planning_router
from app.planning.plan_api import router as plan_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    sqlite.init_db()
    from app.operating import init_all
    init_all()
    init_planning()
    for warning in settings.warnings():
        log.warning("config.warning", detail=warning)
    log.info(
        "app.started",
        env=settings.app_env,
        sqlite=str(settings.sqlite_file),
        dynamic_routing=settings.enable_dynamic_routing,
    )
    yield
    await llm_client.aclose()
    log.info("app.stopped")


app = FastAPI(
    title="MABGP API",
    description="Multi-Agent Autonomous Business Generation Platform",
    version="0.2.0",
    lifespan=lifespan,
)

# Local-only CORS: the Vite dev server and the compose frontend.
# allow_credentials=True is required so the browser sends/receives the httpOnly
# refresh-token cookie used by the auth flow. With credentials enabled, origins
# must be explicit (no "*"), which is already the case here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(operating_router)
app.include_router(auth_router)
app.include_router(planning_router)
app.include_router(plan_router)


# =============================================================================
# F64 - health check
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


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    try:
        with sqlite.connection() as conn:
            conn.execute("SELECT 1").fetchone()
        database = "ok"
    except Exception as exc:  # noqa: BLE001 - health must never raise
        database = f"error: {exc}"

    providers = await llm_client.health()
    any_llm = any(p["available"] for p in providers.values())

    # F38: which competitor source the next run would actually use.
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


@app.post("/intent", tags=["intent"])
async def classify(request: IntentRequest) -> dict:
    """Classify a prompt into structured intent (F1-F5).

    Exposed separately from /generate so the routing decision can be inspected
    before committing to a full multi-agent run - and so the evaluation harness
    can measure intent accuracy in isolation.
    """
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


@app.post("/generate", tags=["generate"])
async def generate(request: GenerateRequest) -> dict:
    """Run the full multi-agent pipeline (F10-F13).

    Department agents are Phase 5; until then the DAG executes placeholder
    runners, so `plan` is empty and `completeness_score` is 0. Routing,
    parallelism, timing, telemetry and persistence are all live.
    """
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
    """Rebuild a package from a stored session (F59)."""
    record = sqlite.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    if not record.get("plan"):
        raise HTTPException(
            status_code=409,
            detail=f"Session '{session_id}' has status '{record['status']}' and no stored plan",
        )
    return record


@app.get("/sections", tags=["output"])
async def list_section_catalogue() -> dict:
    """F45 - the section catalogue. Drives the frontend's tab layout."""
    return {"count": len(SECTION_ORDER), "sections": describe_sections()}


@app.get("/sessions/{session_id}/package", tags=["output"])
async def get_package(session_id: str) -> dict:
    """F42 - the assembled JSON business package with generation metadata (F46)."""
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


@app.get("/sessions/{session_id}/sections/{section_key}", tags=["output"])
async def get_section(session_id: str, section_key: str) -> dict:
    """F45 - one section, so the frontend can fetch or refresh it alone."""
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


@app.get("/sessions/{session_id}/report", response_class=HTMLResponse, tags=["output"])
async def get_html_report(session_id: str) -> HTMLResponse:
    """F43 - the formatted HTML report."""
    html = _render_report(session_id)
    return HTMLResponse(content=html)


@app.get("/sessions/{session_id}/report.pdf", tags=["output"])
async def get_pdf_report(session_id: str) -> Response:
    """F44 - PDF export.

    Returns 503 with guidance rather than a 500 when no PDF backend is installed;
    the HTML report remains available and prints to PDF from any browser.
    """
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
    """Rebuild a BusinessPackage from the stored session and render it."""
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


@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket) -> None:
    """Stream progress events while a generation runs.

    Protocol:
        client -> {"prompt": str, "force_all_departments": bool}
        server -> {"event": "...", "department": ..., "completed": n, "total": n, ...}
        server -> {"event": "result", "summary": {...}}      on success
        server -> {"event": "error", "detail": "..."}        on failure

    This reuses the `ProgressEmitter` callback the orchestrator already accepts
    (F12), so the socket is a transport detail rather than a second code path.
    A dropped connection cannot abort a run: the emitter swallows callback
    failures, because free-tier quota has already been spent by that point.
    """
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


@app.get("/sessions", response_model=list[SessionSummary], tags=["sessions"])
async def list_sessions(limit: int = 50, offset: int = 0) -> list[SessionSummary]:
    limit = max(1, min(limit, 200))
    return [SessionSummary(**row) for row in sqlite.list_sessions(limit, offset)]


@app.get("/sessions/{session_id}", tags=["sessions"])
async def get_session(session_id: str) -> dict:
    record = sqlite.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return record


@app.delete("/sessions/{session_id}", tags=["sessions"])
async def delete_session(session_id: str) -> dict:
    if not sqlite.delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"deleted": session_id}
