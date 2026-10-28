"""Orion v2 FastAPI application — the mission-engine backend.

Phase 1 scope: mission engine (planner → router → executor → engine),
built-in tools, default agents, WebSocket streaming, settings, health.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("orion")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    # Seed the 7 default agents (idempotent).
    from app.agents.defaults import seed_defaults

    seed_defaults()

    # Seed default departments + their pre-built Heads (idempotent).
    try:
        from app.departments.defaults import seed_default_departments

        n = seed_default_departments()
        log.info("orion.departments seeded defaults count=%s", n)
    except Exception as exc:  # noqa: BLE001
        log.warning("orion.departments seed failed: %s", exc)

    # Seed the 7 agent templates (idempotent).
    from app.agents.templates import seed_templates

    try:
        seed_templates()
    except Exception as exc:  # noqa: BLE001
        log.warning("orion.agents template seed failed: %s", exc)

    # Seed the built-in tools pool into the tools table (idempotent).
    from app.tools.seed import seed_builtin_tools

    try:
        n = seed_builtin_tools()
        log.info("orion.tools seeded builtin tools count=%s", n)
    except Exception as exc:  # noqa: BLE001 — never block startup on tool seeding
        log.warning("orion.tools seed failed: %s", exc)

    # Seed the integrations catalog (idempotent).
    from app.tools.integrations import seed_integrations

    try:
        seed_integrations()
    except Exception as exc:  # noqa: BLE001
        log.warning("orion.integrations seed failed: %s", exc)

    # Seed the self-contained local MCP servers (idempotent).
    from app.tools.local_mcp import seed_local_mcp_servers

    try:
        n = seed_local_mcp_servers()
        log.info("orion.mcp seeded local servers count=%s", n)
    except Exception as exc:  # noqa: BLE001
        log.warning("orion.mcp local seed failed: %s", exc)

    # Configure the MongoDB auth layer if a URI is set. If not, auth endpoints
    # will fail at call time with a clear message, but the mission engine runs
    # fine without it. Tests inject a mongomock client before startup; respect it.
    from app.auth import store as auth_store

    if auth_store.is_configured():
        log.info("orion.auth already configured (test injection)")
    elif settings.mongo_available:
        try:
            from pymongo import MongoClient

            client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
            auth_store.configure(client)
            log.info("orion.auth mongo configured")
        except Exception as exc:  # noqa: BLE001 - never block startup on Mongo
            log.warning("orion.auth mongo unavailable: %s", exc)
    else:
        log.warning("orion.auth MONGODB_URI not set — auth endpoints disabled until configured")

    # Start the recurring-mission scheduler (cron-ish) in the background.
    import asyncio as _asyncio

    from app.missions import scheduler as _sched
    _sched_task = _asyncio.create_task(_sched.run_scheduler(poll_seconds=30))

    log.info("orion.started env=%s sqlite=%s", settings.app_env, settings.sqlite_file)
    yield
    _sched_task.cancel()
    log.info("orion.stopped")


app = FastAPI(
    title="Orion API v2",
    description="AI company operating system — dynamic mission engine",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Routers are registered as each step is built.
from app.api.agents import router as agents_router  # noqa: E402
from app.api.chat import router as chat_router  # noqa: E402
from app.api.departments import router as departments_router  # noqa: E402
from app.api.oauth import router as oauth_router  # noqa: E402
from app.api.tools import router as tools_router  # noqa: E402
from app.api.health import router as health_router  # noqa: E402
from app.api.knowledge import router as knowledge_router  # noqa: E402
from app.api.missions import router as missions_router  # noqa: E402
from app.api.settings import router as settings_router  # noqa: E402
from app.api.uploads import router as uploads_router  # noqa: E402
from app.api.workspace import router as workspace_router  # noqa: E402
from app.auth.router import router as auth_router  # noqa: E402

app.include_router(health_router)
app.include_router(missions_router)
app.include_router(settings_router)
app.include_router(uploads_router)
app.include_router(workspace_router)
app.include_router(knowledge_router)
app.include_router(agents_router)
app.include_router(departments_router)
app.include_router(tools_router)
app.include_router(oauth_router)
app.include_router(chat_router)
app.include_router(auth_router)


# Serve generated chart images from code_interpreter (workspace/charts).
@app.get("/charts/{filename}")
async def serve_chart(filename: str):
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    # Path-safety: only a bare filename, must be a .png in the charts dir.
    if "/" in filename or "\\" in filename or ".." in filename or not filename.endswith(".png"):
        raise HTTPException(400, "Invalid chart filename.")
    path = settings.workspace_dir / "charts" / filename
    if not path.exists():
        raise HTTPException(404, "Chart not found.")
    return FileResponse(str(path), media_type="image/png")


# Serve any saved artifact file (images reuse /charts; this serves the rest:
# videos, pdfs, csvs, html, etc.). Path-safe: bare filename inside workspace.
@app.get("/artifacts/{filename}")
async def serve_artifact(filename: str):
    import mimetypes

    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    # Path-safety: only a bare filename, no traversal.
    if "/" in filename or "\\" in filename or ".." in filename or not filename:
        raise HTTPException(400, "Invalid artifact filename.")
    # Look in the artifacts dir first, then fall back to the charts dir (pngs).
    candidates = [
        settings.workspace_dir / "artifacts" / filename,
        settings.workspace_dir / "charts" / filename,
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise HTTPException(404, "Artifact not found.")
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return FileResponse(str(path), media_type=media_type)
