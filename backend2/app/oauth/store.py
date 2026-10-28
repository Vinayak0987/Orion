"""OAuth connections + states store.

Tokens are encrypted at rest with the shared Fernet crypto. The public accessors
NEVER return token values — `public()` strips them and exposes only metadata.
Decrypted tokens are available solely to the token service (runtime use).
Connections are isolated by user_id; a user has at most one per provider.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid

from app.core.crypto import decrypt, encrypt
from app.db.sqlite import _now, connection


# ---- states (one-time CSRF + PKCE) -----------------------------------------

def create_state(*, user_id: str, provider: str, code_verifier: str | None,
                 redirect_uri: str, ttl_minutes: int = 10) -> str:
    state = uuid.uuid4().hex + uuid.uuid4().hex
    now = dt.datetime.now(dt.UTC)
    expires = (now + dt.timedelta(minutes=ttl_minutes)).isoformat()
    with connection() as conn:
        conn.execute(
            """INSERT INTO oauth_states (state, user_id, provider, code_verifier, redirect_uri, created_at, expires_at)
               VALUES (?,?,?,?,?,?,?)""",
            (state, user_id, provider, code_verifier, redirect_uri, now.isoformat(), expires),
        )
    return state


def consume_state(state: str) -> dict | None:
    """Fetch AND delete a state (one-time use). Returns None if missing/expired."""
    with connection() as conn:
        row = conn.execute("SELECT * FROM oauth_states WHERE state=?", (state,)).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM oauth_states WHERE state=?", (state,))
        rec = dict(row)
    if rec["expires_at"] <= _now():
        return None
    return rec


def purge_expired_states() -> int:
    with connection() as conn:
        cur = conn.execute("DELETE FROM oauth_states WHERE expires_at <= ?", (_now(),))
    return cur.rowcount


# ---- connections ------------------------------------------------------------

def upsert_connection(*, user_id: str, provider: str, access_token: str,
                      refresh_token: str | None, expires_at: str | None,
                      scopes: list[str], account_id: str = "", account_label: str = "") -> str:
    now = _now()
    with connection() as conn:
        existing = conn.execute(
            "SELECT id FROM oauth_connections WHERE user_id=? AND provider=?", (user_id, provider)
        ).fetchone()
        conn_id = existing["id"] if existing else uuid.uuid4().hex
        conn.execute(
            """INSERT INTO oauth_connections
               (id, user_id, provider, account_id, account_label, access_token, refresh_token,
                expires_at, scopes, status, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,'connected',?,?)
               ON CONFLICT(user_id, provider) DO UPDATE SET
                 account_id=excluded.account_id, account_label=excluded.account_label,
                 access_token=excluded.access_token, refresh_token=excluded.refresh_token,
                 expires_at=excluded.expires_at, scopes=excluded.scopes,
                 status='connected', updated_at=excluded.updated_at""",
            (conn_id, user_id, provider, account_id, account_label,
             encrypt(access_token), encrypt(refresh_token) if refresh_token else None,
             expires_at, json.dumps(scopes), now, now),
        )
    return conn_id


def update_tokens(*, user_id: str, provider: str, access_token: str,
                  refresh_token: str | None, expires_at: str | None) -> None:
    """Token rotation after a refresh. Keeps the existing refresh token if the
    provider did not return a new one."""
    with connection() as conn:
        row = conn.execute(
            "SELECT refresh_token FROM oauth_connections WHERE user_id=? AND provider=?",
            (user_id, provider),
        ).fetchone()
        keep_refresh = row["refresh_token"] if row else None
        new_refresh = encrypt(refresh_token) if refresh_token else keep_refresh
        conn.execute(
            """UPDATE oauth_connections SET access_token=?, refresh_token=?, expires_at=?,
               status='connected', updated_at=? WHERE user_id=? AND provider=?""",
            (encrypt(access_token), new_refresh, expires_at, _now(), user_id, provider),
        )


def set_status(user_id: str, provider: str, status: str) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE oauth_connections SET status=?, updated_at=? WHERE user_id=? AND provider=?",
            (status, _now(), user_id, provider),
        )


def _row(user_id: str, provider: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM oauth_connections WHERE user_id=? AND provider=?", (user_id, provider)
        ).fetchone()
    return dict(row) if row else None


def get_connection(user_id: str, provider: str) -> dict | None:
    """Full row INCLUDING decrypted tokens — for the token service only. Never
    return this over the API."""
    rec = _row(user_id, provider)
    if rec is None:
        return None
    rec["access_token"] = decrypt(rec["access_token"]) if rec.get("access_token") else ""
    rec["refresh_token"] = decrypt(rec["refresh_token"]) if rec.get("refresh_token") else None
    rec["scopes"] = json.loads(rec["scopes"]) if rec.get("scopes") else []
    return rec


def public(user_id: str, provider: str) -> dict | None:
    """Safe metadata — NO token values."""
    rec = _row(user_id, provider)
    return _strip(rec) if rec else None


def list_public(user_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM oauth_connections WHERE user_id=? ORDER BY provider", (user_id,)
        ).fetchall()
    return [_strip(dict(r)) for r in rows]


def _strip(rec: dict) -> dict:
    return {
        "id": rec["id"], "provider": rec["provider"], "account_id": rec.get("account_id"),
        "account_label": rec.get("account_label"), "status": rec["status"],
        "expires_at": rec.get("expires_at"), "scopes": json.loads(rec["scopes"]) if rec.get("scopes") else [],
        "connected": rec["status"] == "connected", "created_at": rec.get("created_at"),
        "updated_at": rec.get("updated_at"),
    }


def delete_connection(user_id: str, provider: str) -> bool:
    with connection() as conn:
        cur = conn.execute(
            "DELETE FROM oauth_connections WHERE user_id=? AND provider=?", (user_id, provider)
        )
    return cur.rowcount > 0
