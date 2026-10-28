"""OAuth 2.0 API (Plan 06 extension).

All endpoints except the browser callback require a logged-in user
(get_current_user). The callback is a browser redirect — it carries no Bearer
header, so the one-time `state` (created during the authenticated /authorize
call) binds the callback to the right user. Connection ownership is enforced by
scoping every query to the authenticated user's id.

Tokens are never returned by any endpoint.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.auth.deps import get_current_user
from app.auth.models import UserPublic
from app.config import settings
from app.oauth import service, store
from app.oauth.providers import get_provider, registry

router = APIRouter(prefix="/oauth", tags=["oauth"])
log = logging.getLogger("orion.oauth")


@router.get("/providers")
async def list_providers(user: UserPublic = Depends(get_current_user)) -> dict:
    """Catalog of OAuth providers with their configuration + this user's connection state."""
    out = []
    for p in registry().values():
        conn = store.public(user.id, p.id)
        out.append({
            "id": p.id, "name": p.name, "configured": p.configured,
            "scopes": p.scopes, "pkce": p.pkce,
            "connection": conn,
            "status": (conn["status"] if conn else ("available" if p.configured else "not_configured")),
        })
    return {"providers": out}


@router.get("/connections")
async def list_connections(user: UserPublic = Depends(get_current_user)) -> dict:
    return {"connections": store.list_public(user.id)}


# NOTE: declared BEFORE the parametrized /{provider}/* routes so the literal
# "/oauth/mcp/callback" is matched here (not as provider="mcp").
@router.get("/mcp/callback")
async def mcp_oauth_callback(code: str | None = None, state: str | None = None,
                             error: str | None = None) -> RedirectResponse:
    """Browser redirect target for MCP OAuth (fal.ai etc.). Exchanges the code,
    connects the server with the bearer token, discovers + registers its tools,
    then redirects back to the MCP Servers page. No secrets in the redirect URL."""
    frontend = settings.frontend_url.rstrip("/")
    base = f"{frontend}/tools?tab=mcp"
    if error or not code or not state:
        return RedirectResponse(f"{base}&mcp=oauth&status=failed")

    from app.oauth import mcp_oauth
    from app.tools import mcp as mcpstore
    from app.tools import store as toolstore

    try:
        res = await mcp_oauth.exchange(state, code)
        access = res["access_token"]
        mcp_url = res["mcp_url"]
        discovered = await mcpstore.discover_tools(mcp_url, auth_token=access)
        server_id = mcpstore.create_server(
            name=res.get("server_name") or mcp_url, server_url=mcp_url,
            description="OAuth-connected MCP server", tool_count=len(discovered),
            auth_token=access, refresh_token=res.get("refresh_token"),
            oauth_config=res.get("oauth_config"),
        )
        for d in discovered:
            rn = d.get("name")
            if not rn:
                continue
            toolstore.upsert_tool(
                name=f"mcp_{rn}", display_name=rn,
                description=d.get("description") or f"MCP tool ({res.get('server_name')})",
                type="mcp", category="mcp", input_schema=d.get("inputSchema") or {},
                config={"server_url": mcp_url, "mcp_server_id": server_id, "remote_name": rn},
            )
        log.info("oauth.mcp_connected url=%s tools=%s", mcp_url, len(discovered))
        return RedirectResponse(f"{base}&mcp=oauth&status=connected")
    except Exception as e:  # noqa: BLE001
        log.warning("oauth.mcp_callback_failed err=%s", e)
        return RedirectResponse(f"{base}&mcp=oauth&status=failed")


@router.get("/{provider}/status")
async def connection_status(provider: str, user: UserPublic = Depends(get_current_user)) -> dict:
    p = get_provider(provider)
    if p is None:
        raise HTTPException(404, f"Unknown provider '{provider}'")
    conn = store.public(user.id, provider)
    return {"provider": provider, "configured": p.configured,
            "status": conn["status"] if conn else ("available" if p.configured else "not_configured"),
            "connection": conn}


@router.get("/{provider}/authorize")
async def authorize(provider: str, user: UserPublic = Depends(get_current_user)) -> dict:
    """Return the provider authorization URL (frontend opens it in a popup/redirect)."""
    try:
        url, state = service.build_authorize_url(user.id, provider)
    except service.OAuthError as e:
        raise HTTPException(400, str(e)) from e
    return {"authorize_url": url, "state": state}


@router.get("/{provider}/callback")
async def callback(provider: str, code: str | None = None, state: str | None = None,
                   error: str | None = None) -> RedirectResponse:
    """Browser redirect target. Validates state, exchanges the code, stores the
    connection, then redirects back to the frontend Integrations page with a
    status flag. No secrets ever appear in the redirect URL."""
    frontend = settings.frontend_url.rstrip("/")
    base = f"{frontend}/integrations"

    if error:
        log.warning("oauth.callback_error provider=%s error=%s", provider, error)
        return RedirectResponse(f"{base}?oauth={provider}&status=failed")
    if not code or not state:
        return RedirectResponse(f"{base}?oauth={provider}&status=failed")
    try:
        await service.exchange_code(provider, code, state)
        return RedirectResponse(f"{base}?oauth={provider}&status=connected")
    except service.OAuthError as e:
        log.warning("oauth.exchange_failed provider=%s err=%s", provider, e)
        return RedirectResponse(f"{base}?oauth={provider}&status=failed")


@router.post("/{provider}/refresh")
async def refresh_connection(provider: str, user: UserPublic = Depends(get_current_user)) -> dict:
    if store.public(user.id, provider) is None:
        raise HTTPException(404, "No connection to refresh.")
    try:
        refreshed = await service.refresh(user.id, provider)
    except service.OAuthError as e:
        raise HTTPException(400, str(e)) from e
    return {"refreshed": refreshed, "connection": store.public(user.id, provider)}


@router.post("/{provider}/reconnect")
async def reconnect(provider: str, user: UserPublic = Depends(get_current_user)) -> dict:
    """Start a fresh authorization (used when a connection expired/was revoked)."""
    try:
        url, _ = service.build_authorize_url(user.id, provider)
    except service.OAuthError as e:
        raise HTTPException(400, str(e)) from e
    return {"authorize_url": url}


@router.delete("/{provider}")
async def disconnect(provider: str, user: UserPublic = Depends(get_current_user)) -> dict:
    if store.public(user.id, provider) is None:
        raise HTTPException(404, "No connection to disconnect.")
    await service.revoke(user.id, provider)
    return {"disconnected": provider}
