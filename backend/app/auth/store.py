"""MongoDB access layer for the user/website data layer.

The Mongo client is created lazily and can be swapped — real pymongo against
Atlas at runtime, or in-process mongomock in tests. Nothing else talks to Mongo
directly; go through this module.

Collections
-----------
users           { _id, email (unique, lowercased), full_name, password_hash,
                  created_at, ... }
refresh_tokens  { _id=jti, user_id, expires_at, revoked, created_at }
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from app.config import settings

_client: Any = None
_db: Any = None


def _now() -> datetime:
    return datetime.now(UTC)


def configure(client: Any, db_name: str | None = None) -> None:
    """Inject a Mongo client (real or mongomock). Tests use mongomock."""
    global _client, _db
    _client = client
    _db = client[db_name or settings.mongo_db_name]
    _ensure_indexes()


def _create_real_client() -> Any:
    from pymongo import MongoClient

    if not settings.mongodb_uri.strip():
        raise RuntimeError(
            "MONGODB_URI is not set — the user/auth data layer is unavailable. "
            "Add it to .env."
        )
    return MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)


def get_db() -> Any:
    global _client, _db
    if _db is None:
        _client = _create_real_client()
        _db = _client[settings.mongo_db_name]
        _ensure_indexes()
    return _db


def _ensure_indexes() -> None:
    if _db is None:
        return
    _db.users.create_index("email", unique=True)
    _db.refresh_tokens.create_index("user_id")


def reset_for_tests() -> None:
    global _client, _db
    _client = None
    _db = None


def is_configured() -> bool:
    """True if a client has been injected (tests) — lifespan should not override."""
    return _db is not None


# --- Users -------------------------------------------------------------------
def _normalise_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(email: str) -> Optional[dict]:
    return get_db().users.find_one({"email": _normalise_email(email)})


def get_user_by_id(user_id: str) -> Optional[dict]:
    return get_db().users.find_one({"_id": user_id})


def create_user(email: str, full_name: str, password_hash: str) -> dict:
    db = get_db()
    normalised = _normalise_email(email)
    if db.users.find_one({"email": normalised}):
        raise ValueError("Email already registered")

    doc = {
        "_id": uuid.uuid4().hex,
        "email": normalised,
        "full_name": full_name.strip(),
        "password_hash": password_hash,
        "created_at": _now(),
    }
    try:
        db.users.insert_one(doc)
    except Exception as exc:
        if "duplicate" in str(exc).lower() or "E11000" in str(exc):
            raise ValueError("Email already registered") from exc
        raise
    return doc


def update_user_password(user_id: str, password_hash: str) -> None:
    get_db().users.update_one(
        {"_id": user_id}, {"$set": {"password_hash": password_hash}}
    )


def update_user(user_id: str, **fields) -> None:
    """Update profile fields. Used by PUT /auth/me and the avatar endpoint."""
    allowed = {
        k: v
        for k, v in fields.items()
        if k in {"full_name", "email", "avatar_url", "job_title", "bio"}
    }
    if not allowed:
        return
    if "email" in allowed:
        allowed["email"] = _normalise_email(allowed["email"])
    allowed["updated_at"] = _now()
    get_db().users.update_one({"_id": user_id}, {"$set": allowed})


# --- Refresh tokens (revocable) ---------------------------------------------
def store_refresh_token(jti: str, user_id: str, expires_at: datetime) -> None:
    get_db().refresh_tokens.insert_one(
        {
            "_id": jti,
            "user_id": user_id,
            "expires_at": expires_at,
            "revoked": False,
            "created_at": _now(),
        }
    )


def is_refresh_token_active(jti: str) -> bool:
    doc = get_db().refresh_tokens.find_one({"_id": jti})
    if not doc or doc.get("revoked"):
        return False
    expires_at = doc.get("expires_at")
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < _now():
            return False
    return True


def revoke_refresh_token(jti: str) -> None:
    get_db().refresh_tokens.update_one({"_id": jti}, {"$set": {"revoked": True}})


def revoke_all_user_tokens(user_id: str) -> None:
    get_db().refresh_tokens.update_many(
        {"user_id": user_id}, {"$set": {"revoked": True}}
    )
