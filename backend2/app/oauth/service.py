"""Shared OAuth 2.0 service — one abstraction for all providers.

Flow:
  build_authorize_url(user_id, provider) → (url, state)   [stores state + PKCE verifier]
  exchange_code(provider, code, state)   → stores an encrypted connection
  get_valid_access_token(user_id, provider) → refreshes if expired, returns token
  refresh(user_id, provider)             → rotates tokens
  revoke(user_id, provider)              → best-effort provider revoke + delete

Security: Authorization Code flow + one-time `state` (CSRF) + PKCE S256 where the
provider supports it + redirect-URI validation. Tokens never logged or returned.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import logging
import secrets

import httpx

from app.oauth import store
from app.oauth.providers import Provider, get_provider

log = logging.getLogger("orion.oauth")


class OAuthError(Exception):
    pass


# ---- PKCE helpers -----------------------------------------------------------

def _gen_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


# ---- authorize --------------------------------------------------------------

def build_authorize_url(user_id: str, provider_id: str) -> tuple[str, str]:
    p = _require_configured(provider_id)
    from urllib.parse import urlencode

    verifier = _gen_verifier() if p.pkce else None
    redirect_uri = p.redirect_uri()
    state = store.create_state(user_id=user_id, provider=p.id, code_verifier=verifier,
                               redirect_uri=redirect_uri)
    params = {
        "client_id": p.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
    }
    if p.scopes:
        params["scope"] = " ".join(p.scopes)
    if p.pkce and verifier:
        params["code_challenge"] = _challenge(verifier)
        params["code_challenge_method"] = "S256"
    params.update(p.extra_authorize_params)
    return f"{p.authorize_url}?{urlencode(params)}", state


# ---- callback / code exchange ----------------------------------------------

async def exchange_code(provider_id: str, code: str, state: str,
                        client: httpx.AsyncClient | None = None) -> dict:
    p = _require_configured(provider_id)
    st = store.consume_state(state)
    if st is None:
        raise OAuthError("Invalid or expired state (possible CSRF or reused callback).")
    if st["provider"] != p.id:
        raise OAuthError("State/provider mismatch.")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": st["redirect_uri"],
        "client_id": p.client_id,
    }
    if st.get("code_verifier"):
        data["code_verifier"] = st["code_verifier"]

    token_resp = await _token_request(p, data, client)
    access = token_resp.get("access_token")
    if not access:
        raise OAuthError(f"{p.name} did not return an access token.")

    account_id, account_label = await _resolve_account(p, token_resp, access, client)
    expires_at = _expiry_from(token_resp)
    scopes = _scopes_from(token_resp, p)

    store.upsert_connection(
        user_id=st["user_id"], provider=p.id, access_token=access,
        refresh_token=token_resp.get("refresh_token"), expires_at=expires_at,
        scopes=scopes, account_id=account_id, account_label=account_label,
    )
    log.info("oauth.connected provider=%s user=%s account=%s", p.id, st["user_id"], account_label)
    return {"user_id": st["user_id"], "provider": p.id, "account_label": account_label}


async def _token_request(p: Provider, data: dict, client: httpx.AsyncClient | None) -> dict:
    headers = {"Accept": "application/json"}
    auth = None
    if p.uses_basic_auth:
        auth = (p.client_id, p.client_secret)
    else:
        data = {**data, "client_secret": p.client_secret}
    owns = client is None
    client = client or httpx.AsyncClient(timeout=15.0)
    try:
        r = await client.post(p.token_url, data=data, headers=headers, auth=auth)
    finally:
        if owns:
            await client.aclose()
    try:
        body = r.json()
    except Exception as e:  # noqa: BLE001
        raise OAuthError(f"{p.name} returned a non-JSON token response.") from e
    # Slack signals failure with ok=false even on HTTP 200.
    if r.status_code >= 400 or body.get("ok") is False or body.get("error"):
        raise OAuthError(f"{p.name} token exchange failed: {body.get('error', r.status_code)}")
    return body


async def _resolve_account(p: Provider, token_resp: dict, access: str,
                           client: httpx.AsyncClient | None) -> tuple[str, str]:
    info: dict = {}
    if p.userinfo_url:
        owns = client is None
        client = client or httpx.AsyncClient(timeout=12.0)
        try:
            headers = {"Authorization": f"Bearer {access}", "Accept": "application/json"}
            if p.id == "github":
                headers["Accept"] = "application/vnd.github+json"
            r = await client.get(p.userinfo_url, headers=headers)
            if r.status_code < 300:
                info = r.json()
        except Exception:  # noqa: BLE001 — identity is best-effort
            info = {}
        finally:
            if owns:
                await client.aclose()
    if p.account_from:
        try:
            return p.account_from(token_resp, info)
        except Exception:  # noqa: BLE001
            pass
    return ("", p.name)


# ---- refresh / rotation -----------------------------------------------------

async def refresh(user_id: str, provider_id: str, client: httpx.AsyncClient | None = None) -> bool:
    p = _require_configured(provider_id)
    conn = store.get_connection(user_id, provider_id)
    if conn is None:
        raise OAuthError("No connection to refresh.")
    if not conn.get("refresh_token"):
        return False  # provider issues non-expiring tokens (e.g. Notion/Slack)
    data = {"grant_type": "refresh_token", "refresh_token": conn["refresh_token"],
            "client_id": p.client_id}
    try:
        token_resp = await _token_request(p, data, client)
    except OAuthError:
        store.set_status(user_id, provider_id, "expired")
        raise
    access = token_resp.get("access_token")
    if not access:
        store.set_status(user_id, provider_id, "expired")
        raise OAuthError("Refresh did not return an access token.")
    store.update_tokens(user_id=user_id, provider=provider_id, access_token=access,
                        refresh_token=token_resp.get("refresh_token"),
                        expires_at=_expiry_from(token_resp))
    log.info("oauth.refreshed provider=%s user=%s", provider_id, user_id)
    return True


async def get_valid_access_token(user_id: str, provider_id: str) -> str | None:
    """Return a usable access token, auto-refreshing when expired. None if no
    connection or refresh impossible."""
    conn = store.get_connection(user_id, provider_id)
    if conn is None or not conn.get("access_token"):
        return None
    if _is_expired(conn.get("expires_at")) and conn.get("refresh_token"):
        try:
            await refresh(user_id, provider_id)
            conn = store.get_connection(user_id, provider_id)
        except OAuthError:
            return None
    return conn.get("access_token")


# ---- revoke / disconnect ----------------------------------------------------

async def revoke(user_id: str, provider_id: str) -> bool:
    p = get_provider(provider_id)
    conn = store.get_connection(user_id, provider_id)
    if conn and p and p.revoke_url and conn.get("access_token"):
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                if p.id == "google":
                    await c.post(p.revoke_url, data={"token": conn["access_token"]})
                elif p.id == "slack":
                    await c.post(p.revoke_url, headers={"Authorization": f"Bearer {conn['access_token']}"})
        except Exception:  # noqa: BLE001 — revoke is best-effort
            pass
    return store.delete_connection(user_id, provider_id)


# ---- helpers ----------------------------------------------------------------

def _require_configured(provider_id: str) -> Provider:
    p = get_provider(provider_id)
    if p is None:
        raise OAuthError(f"Unknown provider '{provider_id}'.")
    if not p.configured:
        raise OAuthError(f"{p.name} OAuth is not configured (missing client id/secret).")
    return p


def _expiry_from(token_resp: dict) -> str | None:
    exp = token_resp.get("expires_in")
    if not exp:
        return None
    return (dt.datetime.now(dt.UTC) + dt.timedelta(seconds=int(exp))).isoformat()


def _scopes_from(token_resp: dict, p: Provider) -> list[str]:
    scope = token_resp.get("scope")
    if isinstance(scope, str) and scope:
        return scope.replace(",", " ").split()
    return list(p.scopes)


def _is_expired(expires_at: str | None, skew_seconds: int = 60) -> bool:
    if not expires_at:
        return False  # non-expiring
    try:
        exp = dt.datetime.fromisoformat(expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=dt.UTC)
        return dt.datetime.now(dt.UTC) >= exp - dt.timedelta(seconds=skew_seconds)
    except Exception:  # noqa: BLE001
        return True
