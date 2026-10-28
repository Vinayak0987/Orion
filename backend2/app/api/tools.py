"""Tools API (Plan 06) — the full Tools section backend.

Core:        GET /tools, GET /tools/{name}, PUT /tools/{name}, DELETE /tools/{name},
             POST /tools/execute
Custom:      POST /tools/custom, PUT /tools/custom/{name}
MCP:         GET /tools/mcp, POST /tools/mcp, DELETE /tools/mcp/{id}
Integrations: GET /tools/integrations, POST /tools/integrations/{id}/connect,
             POST /tools/integrations/{id}/disconnect
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.crypto import encrypt
from app.tools import integrations as intg
from app.tools import mcp
from app.tools import store
from app.tools.base import ToolContext

router = APIRouter(tags=["tools"])
DEFAULT_USER = "default-user"


# ============================================================================
# Core
# ============================================================================

@router.get("/tools")
async def list_tools(type: str | None = None, category: str | None = None,
                     enabled: bool | None = None, search: str | None = None) -> dict:
    tools = store.list_tools(type=type, category=category, enabled=enabled, search=search)
    # Lightweight facet counts for the UI filter chips.
    all_tools = store.list_tools()
    by_type: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for t in all_tools:
        by_type[t["type"]] = by_type.get(t["type"], 0) + 1
        by_cat[t["category"]] = by_cat.get(t["category"], 0) + 1
    return {"tools": tools, "count": len(tools),
            "facets": {"type": by_type, "category": by_cat, "total": len(all_tools)}}


class UpdateToolRequest(BaseModel):
    enabled: bool | None = None
    description: str | None = None
    display_name: str | None = None
    category: str | None = None


class ExecuteToolRequest(BaseModel):
    name: str
    input: dict = Field(default_factory=dict)


@router.post("/tools/execute")
async def execute_tool(req: ExecuteToolRequest) -> dict:
    """Run any tool directly (the Test button). Uses the real dispatch path."""
    from app.tools import registry

    t = store.get_tool(req.name)
    if t is None:
        raise HTTPException(404, f"Tool '{req.name}' not found")
    import time

    t0 = time.monotonic()
    result = await registry.dispatch(req.name, req.input, ctx=ToolContext(user_id=DEFAULT_USER))
    latency = int((time.monotonic() - t0) * 1000)
    return {"ok": "error" not in result, "result": result, "latency_ms": latency}


# ============================================================================
# Custom tools
# ============================================================================

class CustomToolRequest(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str
    description: str = Field(min_length=10)
    category: str = "custom"
    endpoint: str
    method: str = "GET"
    input_schema: dict = Field(default_factory=dict)
    auth_type: str | None = None   # none | bearer
    auth_header: str | None = None
    auth_value: str | None = None


@router.post("/tools/custom", status_code=201)
async def create_custom_tool(req: CustomToolRequest) -> dict:
    if store.get_tool(req.name):
        raise HTTPException(409, f"A tool named '{req.name}' already exists.")
    if not req.endpoint.lower().startswith(("http://", "https://")):
        raise HTTPException(422, "endpoint must be an http(s) URL")
    config = {"endpoint": req.endpoint, "method": req.method.upper(),
              "auth_type": req.auth_type, "auth_header": req.auth_header}
    if req.auth_type == "bearer" and req.auth_value:
        config["auth_value"] = encrypt(req.auth_value)  # stored encrypted
    store.upsert_tool(name=req.name, display_name=req.display_name, description=req.description,
                      type="custom", category=req.category, input_schema=req.input_schema, config=config)
    return {"tool": store.get_tool(req.name)}


@router.put("/tools/custom/{name}")
async def update_custom_tool(name: str, req: CustomToolRequest) -> dict:
    t = store.get_tool(name)
    if t is None or t["type"] != "custom":
        raise HTTPException(404, f"Custom tool '{name}' not found")
    config = {"endpoint": req.endpoint, "method": req.method.upper(),
              "auth_type": req.auth_type, "auth_header": req.auth_header}
    if req.auth_type == "bearer" and req.auth_value:
        config["auth_value"] = encrypt(req.auth_value)
    elif t["config"].get("auth_value"):
        config["auth_value"] = t["config"]["auth_value"]  # preserve existing
    store.upsert_tool(name=name, display_name=req.display_name, description=req.description,
                      type="custom", category=req.category, input_schema=req.input_schema, config=config)
    return {"tool": store.get_tool(name)}


# ============================================================================
# MCP servers
# ============================================================================

class McpConnectRequest(BaseModel):
    server_url: str | None = None
    name: str | None = None
    description: str | None = None
    auth_token: str | None = None
    auth_scheme: str = "bearer"
    transport: str = "http"          # http | stdio
    command: str | None = None       # stdio: the program/command
    args: list[str] | None = None    # stdio: explicit arg list
    env: dict | None = None          # stdio: extra environment vars


@router.get("/tools/mcp")
async def list_mcp() -> dict:
    servers = mcp.list_servers()
    all_mcp = store.list_tools(type="mcp")
    for s in servers:
        s["tools"] = [t for t in all_mcp if (t.get("config") or {}).get("mcp_server_id") == s["id"]]
        s["is_local"] = str(s.get("server_url", "")).startswith("local://")
        s["transport"] = "stdio" if str(s.get("server_url", "")).startswith("stdio://") else ("local" if s["is_local"] else "http")
    return {"servers": servers, "count": len(servers)}


@router.post("/tools/mcp", status_code=201)
async def connect_mcp(req: McpConnectRequest) -> dict:
    # --- stdio (local command) transport — gated behind a settings flag ---
    if req.transport == "stdio":
        from app.config import settings as _settings
        if not _settings.mcp_stdio_enabled:
            raise HTTPException(501, "Local command (stdio) MCP servers are disabled. "
                                     "Set MCP_STDIO_ENABLED=true in the backend to allow them.")
        if not req.command:
            raise HTTPException(422, "stdio transport requires a 'command'.")
        from app.tools import mcp_stdio
        try:
            discovered = await mcp_stdio.discover_stdio(req.command, req.args, req.env)
        except mcp_stdio.MCPError as e:
            raise HTTPException(502, str(e)) from e
        slug = (req.name or req.command).strip().lower().replace(" ", "-")[:40]
        pseudo_url = f"stdio://{slug}"
        server_id = mcp.create_server(name=req.name or req.command, server_url=pseudo_url,
                                      description=req.description or f"Local command: {req.command}",
                                      tool_count=len(discovered))
        registered = []
        for d in discovered:
            rn = d.get("name")
            if not rn:
                continue
            local_name = f"mcp_{rn}"
            store.upsert_tool(
                name=local_name, display_name=rn,
                description=d.get("description") or f"stdio MCP tool ({req.command})",
                type="mcp", category="mcp", input_schema=d.get("inputSchema") or {},
                config={"server_url": pseudo_url, "mcp_server_id": server_id, "remote_name": rn,
                        "transport": "stdio", "command": req.command, "args": req.args, "env": req.env},
            )
            registered.append(local_name)
        return {"server_id": server_id, "tools_discovered": registered, "count": len(registered), "transport": "stdio"}

    # --- remote URL (http/sse) transport ---
    if not req.server_url or not req.server_url.lower().startswith(("http://", "https://")):
        raise HTTPException(422, "server_url must be an http(s) URL")
    try:
        discovered = await mcp.discover_tools(req.server_url, auth_token=req.auth_token, auth_scheme=req.auth_scheme)
    except mcp.MCPError as e:
        # If the server requires OAuth (401), begin the MCP OAuth flow and return
        # an authorize_url for the browser sign-in instead of failing.
        if not req.auth_token and "authentication" in str(e).lower() or "401" in str(e):
            from app.oauth import mcp_oauth
            try:
                authorize_url = await mcp_oauth.begin(req.server_url, req.name)
                return {"needs_oauth": True, "authorize_url": authorize_url}
            except mcp_oauth.MCPOAuthError as oe:
                raise HTTPException(502, f"OAuth discovery failed: {oe}") from oe
        raise HTTPException(502, str(e)) from e

    server_id = mcp.create_server(name=req.name or req.server_url, server_url=req.server_url,
                                  description=req.description or "", tool_count=len(discovered),
                                  auth_token=req.auth_token, auth_scheme=req.auth_scheme)
    registered = []
    for d in discovered:
        remote_name = d.get("name")
        if not remote_name:
            continue
        local_name = f"mcp_{remote_name}"
        store.upsert_tool(
            name=local_name, display_name=remote_name,
            description=d.get("description") or f"MCP tool from {req.server_url}",
            type="mcp", category="mcp", input_schema=d.get("inputSchema") or {},
            config={"server_url": req.server_url, "mcp_server_id": server_id, "remote_name": remote_name},
        )
        registered.append(local_name)
    return {"server_id": server_id, "tools_discovered": registered, "count": len(registered)}


@router.delete("/tools/mcp/{server_id}")
async def disconnect_mcp(server_id: str) -> dict:
    """Disconnect (deactivate) a server WITHOUT deleting it. Its tools are disabled
    so agents won't use them, but the server stays in the list to reconnect later."""
    server = mcp.get_server(server_id)
    if server is None:
        raise HTTPException(404, f"MCP server '{server_id}' not found")
    disabled = 0
    for t in store.list_tools(type="mcp"):
        if (t["config"] or {}).get("mcp_server_id") == server_id:
            store.set_enabled(t["name"], False)
            disabled += 1
    mcp.set_server_status(server_id, "disconnected")
    return {"status": "disconnected", "tools_disabled": disabled}


@router.post("/tools/mcp/{server_id}/connect")
async def reconnect_mcp(server_id: str) -> dict:
    """Reconnect a previously-disconnected server: re-enable its tools."""
    server = mcp.get_server(server_id)
    if server is None:
        raise HTTPException(404, f"MCP server '{server_id}' not found")
    enabled = 0
    for t in store.list_tools(type="mcp"):
        if (t["config"] or {}).get("mcp_server_id") == server_id:
            store.set_enabled(t["name"], True)
            enabled += 1
    mcp.set_server_status(server_id, "connected")
    return {"status": "connected", "tools_enabled": enabled}


@router.delete("/tools/mcp/{server_id}/remove")
async def remove_mcp(server_id: str) -> dict:
    """Permanently remove a server and all its tools (not for local servers)."""
    server = mcp.get_server(server_id)
    if server is None:
        raise HTTPException(404, f"MCP server '{server_id}' not found")
    if str(server.get("server_url", "")).startswith("local://"):
        raise HTTPException(422, "Local servers can't be removed — disconnect instead.")
    removed = 0
    for t in store.list_tools(type="mcp"):
        if (t["config"] or {}).get("mcp_server_id") == server_id:
            store.delete_tool(t["name"])
            removed += 1
    mcp.delete_server(server_id)
    return {"deleted": True, "tools_removed": removed}


# ============================================================================
# Integrations
# ============================================================================

@router.get("/tools/integrations")
async def list_integrations() -> dict:
    return {"integrations": intg.list_integrations(), "summary": intg.summary()}


@router.get("/tools/catalog")
async def tool_catalog() -> dict:
    """The unified connectable catalog: every external tool, grouped by category,
    each with its connect_method + current status. Agents can use connected ones."""
    items = intg.list_integrations()
    groups: dict[str, list] = {}
    for it in items:
        groups.setdefault(it.get("category") or "other", []).append(it)
    return {"catalog": items, "groups": groups, "summary": intg.summary(),
            "categories": sorted(groups.keys())}


class CatalogConnectRequest(BaseModel):
    credential: str | None = None   # api_key / token / mcp token (optional)


@router.post("/tools/catalog/{integration_id}/connect")
async def catalog_connect(integration_id: str, req: CatalogConnectRequest) -> dict:
    """Method-routed connect. For oauth tools, returns an authorize_url the UI
    opens; for api_key/mcp tools, validates + stores + (for mcp) registers tools."""
    row = intg.get_integration(integration_id)
    if row is None:
        raise HTTPException(404, f"Unknown integration '{integration_id}'")
    method = row.get("connect_method") or "api_key"

    if method == "oauth":
        from app.oauth.providers import get_provider
        provider = row.get("oauth_provider")
        p = get_provider(provider) if provider else None
        if p is None:
            raise HTTPException(422, f"No OAuth provider configured for {row['name']}.")
        if not p.configured:
            raise HTTPException(501, f"{row['name']} OAuth is not configured yet "
                                     f"(add {provider} client id/secret to the backend .env).")
        return {"method": "oauth", "provider": provider,
                "note": "Open the authorize URL from GET /oauth/{provider}/authorize (requires login)."}

    res = await intg.connect(integration_id, credential=req.credential)
    if not res["ok"]:
        raise HTTPException(res.get("code", 400), res["error"])
    return {"method": method, "status": "connected", "account_label": res.get("account_label")}


@router.post("/tools/catalog/{integration_id}/disconnect")
async def catalog_disconnect(integration_id: str) -> dict:
    if not intg.disconnect(integration_id):
        raise HTTPException(404, f"Integration '{integration_id}' not found")
    return {"status": "available"}


class ConnectIntegrationRequest(BaseModel):
    credential: str | None = None
    skip_validation: bool = False


@router.post("/tools/integrations/{integration_id}/connect")
async def connect_integration(integration_id: str, req: ConnectIntegrationRequest) -> dict:
    res = await intg.connect(integration_id, credential=req.credential,
                             skip_validation=req.skip_validation)
    if not res["ok"]:
        raise HTTPException(res.get("code", 400), res["error"])
    row = intg.get_integration(integration_id) or {}
    return {"status": "connected", "account_label": res.get("account_label"),
            "integration": {k: v for k, v in row.items() if k != "credential"}}


@router.post("/tools/integrations/{integration_id}/disconnect")
async def disconnect_integration(integration_id: str) -> dict:
    if not intg.disconnect(integration_id):
        raise HTTPException(404, f"Integration '{integration_id}' not found")
    return {"status": "available"}



# ============================================================================
# Parametrized /tools/{name} — declared LAST so literal paths (/tools/execute,
# /tools/custom, /tools/mcp, /tools/integrations) match first.
# ============================================================================

@router.get("/tools/{name}")
async def get_tool(name: str) -> dict:
    t = store.get_tool(name)
    if t is None:
        raise HTTPException(404, f"Tool '{name}' not found")
    return t


@router.put("/tools/{name}")
async def update_tool(name: str, req: UpdateToolRequest) -> dict:
    t = store.get_tool(name)
    if t is None:
        raise HTTPException(404, f"Tool '{name}' not found")
    if req.enabled is not None:
        store.set_enabled(name, req.enabled)
    changes = req.model_dump(exclude_unset=True)
    if any(k in changes for k in ("description", "display_name", "category")):
        store.upsert_tool(
            name=name,
            display_name=changes.get("display_name", t["display_name"]),
            description=changes.get("description", t["description"]),
            type=t["type"], category=changes.get("category", t["category"]),
            input_schema=t["input_schema"], config=t["config"],
            requires_key=t.get("requires_key"), degraded=t["degraded"],
        )
    return {"tool": store.get_tool(name)}


@router.delete("/tools/{name}")
async def delete_tool(name: str) -> dict:
    t = store.get_tool(name)
    if t is None:
        raise HTTPException(404, f"Tool '{name}' not found")
    if t["type"] == "builtin":
        raise HTTPException(422, "Built-in tools cannot be deleted — disable it instead.")
    store.delete_tool(name)
    return {"deleted": name}
