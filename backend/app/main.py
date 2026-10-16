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

    # Boot the v1 generation + operating engine (merged under app.generation).
    from app.generation.lifecycle import init_generation

    init_generation()
    log.info("orion.generation engine initialised")

    log.info("orion.started env=%s sqlite=%s", settings.app_env, settings.sqlite_file)
    yield
    from app.generation.lifecycle import shutdown_generation

    await shutdown_generation()
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
from app.api.chat import router as chat_router  # noqa: E402
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
app.include_router(chat_router)
app.include_router(auth_router)

# v1 generation + operating + planning engine (merged under app.generation).
from app.generation.app_routes import router as generation_router  # noqa: E402
from app.generation.operating.api import router as gen_operating_router  # noqa: E402
from app.generation.planning.api import router as gen_planning_router  # noqa: E402
from app.generation.planning.plan_api import router as gen_plan_router  # noqa: E402

app.include_router(generation_router)
app.include_router(gen_operating_router)
app.include_router(gen_planning_router)
app.include_router(gen_plan_router)
