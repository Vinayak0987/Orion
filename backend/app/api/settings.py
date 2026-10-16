"""Settings API — user API keys.

Keys are encrypted at rest (app.stores.settings.store) and only ever returned masked.
The decrypted values are loaded directly by the mission key-loader, never
exposed over this API.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.stores.settings import store

router = APIRouter(prefix="/settings", tags=["settings"])


class ApiKeysRequest(BaseModel):
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    serper_api_key: str | None = None
    google_places_api_key: str | None = None


@router.get("/api-keys")
async def get_api_keys() -> dict:
    return store.masked_keys()


@router.put("/api-keys")
async def put_api_keys(req: ApiKeysRequest) -> dict:
    store.set_keys(req.model_dump())
    return {"updated": True}


@router.delete("/api-keys/{provider}")
async def delete_api_key(provider: str) -> dict:
    short = provider.replace("_api_key", "")
    if short not in {p.replace("_api_key", "") for p in store.PROVIDERS}:
        raise HTTPException(404, f"Unknown provider '{provider}'")
    removed = store.delete_key(provider)
    if not removed:
        raise HTTPException(404, f"No key set for '{provider}'")
    return {"deleted": short}
