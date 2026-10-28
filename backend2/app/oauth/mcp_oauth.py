"""MCP OAuth — auto-discovery + Dynamic Client Registration (DCR).

Lets Orion connect OAuth-protected MCP servers (fal.ai, etc.) with just a URL +
a browser sign-in — no pre-registered client id. Implements the MCP auth spec:

  1. Probe the MCP URL → 401 with `WWW-Authenticate: Bearer resource_metadata=...`
  2. Fetch the protected-resource metadata (RFC 9728) → authorization server(s)
  3. Fetch the authorization-server metadata (RFC 8414) → authorize/token/register
  4. Dynamically register a client (RFC 7591) at registration_endpoint
  5. Build the Authorization Code + PKCE (S256) authorize URL
  6. After browser consent, exchange the code → bearer (+ refresh) token
  7. Use the bearer token on the MCP connection (mcp.py already supports it)

All network/parse failures raise MCPOAuthError (callers turn into clear errors).
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import secrets
import uuid

import httpx

from app.config import settings
from app.core.crypto import decrypt, encrypt
from app.db.sqlite import _now, connection


class MCPOAuthError(Exception):
    pass


def redirect_uri() -> str:
    return f"{settings.oauth_redirect_base.rstrip('/')}/oauth/mcp/callback"


# ---- PKCE -------------------------------------------------------------------

def _verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()


def _challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


# ---- discovery --------------------------------------------------------------

async def _get_json(client: httpx.AsyncClient, url: str) -> dict:
    r = await client.get(url, headers={"Accept": "application/json"})
    if r.status_code >= 400:
        raise MCPOAuthError(f"metadata fetch failed ({r.status_code}) at {url}")
    return r.json()


def _parse_resource_metadata_url(www_auth: str) -> str | None:
    # WWW-Authenticate: Bearer resource_metadata="https://.../.well-known/..."
    for part in www_auth.split(","):
        part = part.strip()
        if part.lower().startswith("bearer") and "resource_metadata=" in part:
            frag = part.split("resource_metadata=", 1)[1].strip().strip('"')
            return frag
        if part.startswith("resource_metadata="):
            return part.split("=", 1)[1].strip().strip('"')
    return None


async def discover(mcp_url: str) -> dict:
    """Probe the MCP server and discover its OAuth endpoints. Returns a dict with
    authorization_endpoint, token_endpoint, registration_endpoint, scopes, resource.
    Raises MCPOAuthError if the server isn't OAuth-protected or metadata is missing."""
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c:
        # 1) Probe → expect 401 + resource_metadata
        probe = {"jsonrpc": "2.0", "id": "probe", "method": "initialize",
                 "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                            "clientInfo": {"name": "Orion", "version": "2.0.0"}}}
        r = await c.post(mcp_url, json=probe,
                         headers={"Accept": "application/json, text/event-stream",
                                  "Content-Type": "application/json"})
        if r.status_code != 401:
            raise MCPOAuthError(f"server did not request OAuth (HTTP {r.status_code})")
        www = r.headers.get("www-authenticate", "")
        rm_url = _parse_resource_metadata_url(www)

        # 2) Protected-resource metadata → authorization server
        as_base = None
        scopes = ["openid", "profile", "email", "offline_access"]
        resource = mcp_url
        if rm_url:
            prm = await _get_json(c, rm_url)
            resource = prm.get("resource") or mcp_url
            servers = prm.get("authorization_servers") or []
            if servers:
                as_base = servers[0]
            scopes = prm.get("scopes_supported") or scopes
        if not as_base:
            # Fall back to the MCP host's origin.
            from urllib.parse import urlparse
            p = urlparse(mcp_url)
            as_base = f"{p.scheme}://{p.netloc}"

        # 3) Authorization-server metadata
        meta = None
        for path in ("/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"):
            try:
                meta = await _get_json(c, as_base.rstrip("/") + path)
                break
            except MCPOAuthError:
                continue
        if not meta:
            raise MCPOAuthError("could not fetch authorization-server metadata")

        return {
            "authorization_endpoint": meta["authorization_endpoint"],
            "token_endpoint": meta["token_endpoint"],
            "registration_endpoint": meta.get("registration_endpoint"),
            "scopes": scopes,
            "resource": resource,
            "issuer": meta.get("issuer", as_base),
        }


# ---- dynamic client registration (RFC 7591) ---------------------------------

async def register_client(registration_endpoint: str, redirect: str) -> dict:
    body = {
        "client_name": "Orion",
        "redirect_uris": [redirect],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",  # public client + PKCE
        "application_type": "web",
    }
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(registration_endpoint, json=body, headers={"Content-Type": "application/json"})
    if r.status_code >= 400:
        raise MCPOAuthError(f"dynamic client registration failed ({r.status_code}): {r.text[:200]}")
    d = r.json()
    cid = d.get("client_id")
    if not cid:
        raise MCPOAuthError("registration response had no client_id")
    return {"client_id": cid, "client_secret": d.get("client_secret")}


# ---- begin flow: discover + register + authorize URL ------------------------

async def begin(mcp_url: str, server_name: str | None = None) -> str:
    """Full pre-auth setup. Returns the authorize URL to open in the browser.
    Persists the one-time flow state (PKCE verifier + client creds)."""
    info = await discover(mcp_url)
    redirect = redirect_uri()

    client_id, client_secret = None, None
    if info.get("registration_endpoint"):
        reg = await register_client(info["registration_endpoint"], redirect)
        client_id, client_secret = reg["client_id"], reg.get("client_secret")
    else:
        raise MCPOAuthError("server has no dynamic registration endpoint and no pre-set client id")

    verifier = _verifier()
    state = uuid.uuid4().hex + uuid.uuid4().hex
    now = dt.datetime.now(dt.UTC)
    with connection() as conn:
        conn.execute(
            """INSERT INTO mcp_oauth_flows
               (state, mcp_url, server_name, code_verifier, client_id, client_secret,
                token_endpoint, redirect_uri, resource, created_at, expires_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (state, mcp_url, server_name or mcp_url, verifier, client_id,
             encrypt(client_secret) if client_secret else None,
             info["token_endpoint"], redirect, info.get("resource"),
             now.isoformat(), (now + dt.timedelta(minutes=10)).isoformat()),
        )

    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "state": state,
        "scope": " ".join(info["scopes"]),
        "code_challenge": _challenge(verifier),
        "code_challenge_method": "S256",
    }
    if info.get("resource"):
        params["resource"] = info["resource"]
    return f"{info['authorization_endpoint']}?{urlencode(params)}"


def _consume_flow(state: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM mcp_oauth_flows WHERE state=?", (state,)).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM mcp_oauth_flows WHERE state=?", (state,))
        rec = dict(row)
    if rec["expires_at"] <= _now():
        return None
    rec["client_secret"] = decrypt(rec["client_secret"]) if rec.get("client_secret") else None
    return rec


# ---- complete flow: exchange code -> tokens ---------------------------------

async def exchange(state: str, code: str) -> dict:
    """Exchange the authorization code for tokens. Returns
    {mcp_url, server_name, access_token, refresh_token, oauth_config}."""
    flow = _consume_flow(state)
    if flow is None:
        raise MCPOAuthError("invalid or expired MCP OAuth state")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": flow["redirect_uri"],
        "client_id": flow["client_id"],
        "code_verifier": flow["code_verifier"],
    }
    if flow.get("client_secret"):
        data["client_secret"] = flow["client_secret"]
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(flow["token_endpoint"], data=data, headers={"Accept": "application/json"})
    if r.status_code >= 400:
        raise MCPOAuthError(f"token exchange failed ({r.status_code}): {r.text[:200]}")
    tok = r.json()
    access = tok.get("access_token")
    if not access:
        raise MCPOAuthError("token response had no access_token")
    return {
        "mcp_url": flow["mcp_url"], "server_name": flow["server_name"],
        "access_token": access, "refresh_token": tok.get("refresh_token"),
        "oauth_config": json.dumps({
            "token_endpoint": flow["token_endpoint"], "client_id": flow["client_id"],
            "client_secret": flow.get("client_secret"), "resource": flow.get("resource"),
        }),
    }


async def refresh(mcp_url: str) -> str | None:
    """Refresh an expired MCP bearer token using the stored refresh token + oauth_config.
    Returns the new access token, or None if not refreshable."""
    from app.tools import mcp as mcpstore
    row = None
    with connection() as conn:
        r = conn.execute("SELECT refresh_token, oauth_config FROM mcp_servers WHERE server_url=?", (mcp_url,)).fetchone()
        if r:
            row = dict(r)
    if not row or not row.get("refresh_token") or not row.get("oauth_config"):
        return None
    cfg = json.loads(row["oauth_config"])
    data = {"grant_type": "refresh_token", "refresh_token": decrypt(row["refresh_token"]),
            "client_id": cfg["client_id"]}
    if cfg.get("client_secret"):
        data["client_secret"] = cfg["client_secret"]
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            resp = await c.post(cfg["token_endpoint"], data=data, headers={"Accept": "application/json"})
        if resp.status_code >= 400:
            return None
        tok = resp.json()
        access = tok.get("access_token")
        if access:
            mcpstore.update_server_tokens(mcp_url, access, tok.get("refresh_token"))
        return access
    except Exception:  # noqa: BLE001
        return None
