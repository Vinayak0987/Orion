"""MongoDB access layer for the user/website data layer.

The Mongo client is created lazily and can be swapped out — real pymongo against
Atlas at runtime, or an in-process mongomock client in tests. Nothing else in
the codebase talks to Mongo directly; go through this module.

Collections
-----------
users           { _id, email (unique, lowercased), full_name, password_hash,
                  created_at, ... free to grow }
refresh_tokens  { _id=jti, user_id, expires_at, revoked, created_at }
                  Stored so refresh tokens can be revoked (logout / rotation).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from app.config import settings

# The active client + db. `configure()` sets these; `get_db()` lazily creates a
# real client on first use if none was injected.
_client: Any = None
_db: Any = None


def _now() -> datetime:
    return datetime.now(UTC)


def configure(client: Any, db_name: str | None = None) -> None:
    """Inject a Mongo client (real or mongomock). Tests call this with a
    mongomock client so no network or server is needed."""
    global _client, _db
    _client = client
    _db = client[db_name or settings.mongo_db_name]
    _ensure_indexes()


def _create_real_client() -> Any:
    """Create a real pymongo client from settings. Imported lazily so mongomock
    tests never require pymongo's server-selection machinery to touch a network."""
    from pymongo import MongoClient

    if not settings.mongodb_uri.strip():
        raise RuntimeError(
            "MONGODB_URI is not set — the user/auth data layer is unavailable. "
            "Add it to .env (see .env.example)."
        )
    return MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)


def get_db() -> Any:
    """Return the active database, creating a real client on first use."""
    global _client, _db
    if _db is None:
        _client = _create_real_client()
        _db = _client[settings.mongo_db_name]
        _ensure_indexes()
    return _db


def _ensure_indexes() -> None:
    if _db is None:
        return
    # Unique email prevents duplicate accounts at the storage layer, regardless
    # of any race in the application check.
    _db.users.create_index("email", unique=True)
    _db.refresh_tokens.create_index("user_id")


def reset_for_tests() -> None:
    """Drop the injected client/db so each test starts clean."""
    global _client, _db
    _client = None
    _db = None


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
def _normalise_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(email: str) -> Optional[dict]:
    return get_db().users.find_one({"email": _normalise_email(email)})


def get_user_by_id(user_id: str) -> Optional[dict]:
    return get_db().users.find_one({"_id": user_id})


def create_user(email: str, full_name: str, password_hash: str) -> dict:
    """Insert a new user. Returns the stored document.

    Raises ValueError if the email already exists.
    """
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
    except Exception as exc:  # unique-index race -> surface as ValueError
        if "duplicate" in str(exc).lower() or "E11000" in str(exc):
            raise ValueError("Email already registered") from exc
        raise
    return doc


def update_user_password(user_id: str, password_hash: str) -> None:
    get_db().users.update_one(
        {"_id": user_id}, {"$set": {"password_hash": password_hash}}
    )


# --------------------------------------------------------------------------- #
# Refresh tokens (revocable)
# --------------------------------------------------------------------------- #
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
    """True only if the token exists, is not revoked, and has not expired."""
    doc = get_db().refresh_tokens.find_one({"_id": jti})
    if not doc or doc.get("revoked"):
        return False
    expires_at = doc.get("expires_at")
    if expires_at is not None:
        # Mongo may return naive UTC datetimes; compare in UTC.
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
