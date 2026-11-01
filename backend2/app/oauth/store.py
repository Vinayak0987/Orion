"""OAuth connections + states store.

Tokens are encrypted at rest with the shared Fernet crypto. The public accessors
NEVER return token values — `public()` strips them and exposes only metadata.
Decrypted tokens are available solely to the token service (runtime use).
Connections are isolated by user_id; a user has at most one per provider.

Now uses MongoDB instead of SQLite for persistence.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid

from app.auth import store as auth_store
from app.core.crypto import decrypt, encrypt


# ---- states (one-time CSRF + PKCE) -----------------------------------------

def create_state(*, user_id: str, provider: str, code_verifier: str | None,
                 redirect_uri: str, ttl_minutes: int = 10) -> str:
    state = uuid.uuid4().hex + uuid.uuid4().hex
    auth_store.create_oauth_state(state, user_id, provider, code_verifier, redirect_uri, ttl_minutes)
    return state


def consume_state(state: str) -> dict | None:
    """Fetch AND delete a state (one-time use). Returns None if missing/expired."""
    return auth_store.consume_oauth_state(state)


def purge_expired_states() -> int:
    return auth_store.purge_expired_oauth_states()


# ---- connections ------------------------------------------------------------

def upsert_connection(*, user_id: str, provider: str, access_token: str,
                      refresh_token: str | None, expires_at: str | None,
                      scopes: list[str], account_id: str = "", account_label: str = "") -> str:
    return auth_store.upsert_oauth_connection(
        user_id=user_id,
        provider=provider,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        scopes=scopes,
        account_id=account_id,
        account_label=account_label,
    )


def update_tokens(*, user_id: str, provider: str, access_token: str,
                  refresh_token: str | None, expires_at: str | None) -> None:
    """Token rotation after a refresh. Keeps the existing refresh token if the
    provider did not return a new one."""
    auth_store.update_oauth_tokens(
        user_id=user_id,
        provider=provider,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )


def set_status(user_id: str, provider: str, status: str) -> None:
    auth_store.set_oauth_connection_status(user_id, provider, status)


def get_connection(user_id: str, provider: str) -> dict | None:
    """Full row INCLUDING decrypted tokens — for the token service only. Never
    return this over the API."""
    rec = auth_store.get_oauth_connection(user_id, provider)
    if rec is None:
        return None
    # MongoDB already decrypts tokens in get_oauth_connection
    rec["scopes"] = rec.get("scopes", [])
    return rec


def public(user_id: str, provider: str) -> dict | None:
    """Safe metadata — NO token values."""
    return auth_store.get_oauth_connection_public(user_id, provider)


def list_public(user_id: str) -> list[dict]:
    return auth_store.list_oauth_connections_public(user_id)


def delete_connection(user_id: str, provider: str) -> bool:
    return auth_store.delete_oauth_connection(user_id, provider)
