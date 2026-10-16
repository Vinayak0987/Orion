"""Health API — DB check + LLM provider availability + rate-limit snapshot."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.db.sqlite import connection
from app.llm.ratelimit import tracker

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    try:
        with connection() as conn:
            conn.execute("SELECT 1").fetchone()
        database = "ok"
    except Exception as exc:  # noqa: BLE001 - health must never raise
        database = f"error: {exc}"

    providers = {
        "groq": {"configured": settings.groq_available},
        "gemini": {"configured": settings.gemini_available},
        "ollama": {"configured": True, "note": "local, always attempted last"},
    }
    any_llm = settings.groq_available or settings.gemini_available or True  # ollama fallback

    return {
        "status": "ok" if database == "ok" and any_llm else "degraded",
        "env": settings.app_env,
        "database": database,
        "llm_providers": providers,
        "tools": {
            "web_search": {"configured": settings.serper_available},
            "document_rag": {"configured": True, "note": "ChromaDB local"},
        },
        "rate_limits": tracker.snapshot(),
    }
