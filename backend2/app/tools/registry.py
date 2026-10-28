"""Tool registry + dispatch — DB-backed.

The Executor calls `dispatch(name, input, user_keys, ctx=...)`. Resolution:
  1. Look the tool up in the `tools` table (source of truth).
  2. If missing/disabled → structured error (never raises).
  3. Route by type:
       builtin → the in-process BuiltinTool (safe_run; never raises)
       custom  → HTTP call to the registered endpoint
       mcp     → proxied to the MCP server (connectors phase; stubbed clearly)
Unknown/mis-planned tool names degrade to {error} so a mission continues.

`list_tools()` returns {name, description} for the ENABLED tools so the executor
can advertise them to the LLM. Backwards-compatible with the old API.
"""

from __future__ import annotations

import httpx

from app.tools import store
from app.tools.base import REGISTRY, ToolContext, load_all

# Ensure the in-process builtin map is populated on import.
load_all()


def list_tools(enabled_only: bool = True, full: bool = False) -> list[dict]:
    """Advertised tool list for the LLM prompt. Reads the DB when available,
    falls back to the in-process registry (e.g. before seeding).

    full=False → compact {name, description} (backwards-compatible default).
    full=True  → full records incl. input_schema, type, category, enabled,
                 degraded — used by the executor to show capability tags and
                 arg hints, and by the capability registry for classification."""
    try:
        rows = store.list_tools(enabled=True if enabled_only else None)
        if rows:
            if full:
                return [dict(r) for r in rows]
            return [{"name": r["name"], "description": r["description"]} for r in rows]
    except Exception:  # noqa: BLE001 — DB not ready yet
        pass
    if full:
        return [{"name": bt.name, "description": bt.description, "type": "builtin",
                 "input_schema": getattr(bt, "input_schema", {}) or {},
                 "category": getattr(bt, "category", "utility")}
                for bt in REGISTRY.values()]
    return [{"name": bt.name, "description": bt.description} for bt in REGISTRY.values()]


async def dispatch(tool_name: str, tool_input: dict, user_keys: dict | None = None,
                   ctx: ToolContext | None = None) -> dict:
    ctx = ctx or ToolContext(user_keys=user_keys)
    if user_keys and not ctx.user_keys:
        ctx.user_keys = user_keys

    record = store.get_tool(tool_name)

    # If the DB has no row yet (pre-seed) but we have a builtin, run it directly.
    if record is None:
        bt = REGISTRY.get(tool_name)
        if bt is None:
            return {"error": f"Unknown tool: {tool_name}"}
        return await bt.safe_run(tool_input, ctx)

    if not record["enabled"]:
        return {"error": f"Tool '{tool_name}' is disabled.", "degraded": True}

    ttype = record["type"]
    if ttype == "builtin":
        bt = REGISTRY.get(tool_name)
        if bt is None:
            return {"error": f"Built-in '{tool_name}' has no implementation.", "degraded": True}
        return await bt.safe_run(tool_input, ctx)

    if ttype == "custom":
        return await _dispatch_custom(record, tool_input)

    if ttype == "mcp":
        return await _dispatch_mcp(record, tool_input, ctx)

    return {"error": f"Unsupported tool type: {ttype}", "degraded": True}


async def _dispatch_mcp(record: dict, tool_input: dict, ctx=None) -> dict:
    cfg = record.get("config") or {}
    server_url = cfg.get("server_url")
    remote_name = cfg.get("remote_name") or record["name"]
    if not server_url:
        return {"error": f"MCP tool '{record['name']}' has no server_url.", "degraded": True}

    # Local (self-contained) MCP servers run their underlying built-in in-process.
    if cfg.get("local") or (server_url or "").startswith("local://"):
        impl = cfg.get("impl") or remote_name
        bt = REGISTRY.get(impl)
        if bt is None:
            return {"error": f"Local MCP tool '{impl}' has no implementation.", "degraded": True}
        return await bt.safe_run(tool_input, ctx)

    # stdio (local command) MCP servers spawn a subprocess per call.
    if cfg.get("transport") == "stdio" or (server_url or "").startswith("stdio://"):
        from app.tools import mcp_stdio
        try:
            return await mcp_stdio.call_stdio(
                cfg.get("command", ""), remote_name, tool_input,
                args=cfg.get("args"), env=cfg.get("env"),
            )
        except Exception as e:  # noqa: BLE001
            return {"error": f"stdio MCP tool '{record['name']}' failed: {e}", "degraded": True}

    from app.tools import mcp

    token, scheme = mcp.get_server_auth(server_url)
    try:
        return await mcp.call_tool(server_url, remote_name, tool_input, auth_token=token, auth_scheme=scheme)
    except Exception as e:  # noqa: BLE001
        # If the bearer token expired (auth error), try an OAuth refresh once.
        if "401" in str(e) or "authentication" in str(e).lower():
            try:
                from app.oauth import mcp_oauth
                new_token = await mcp_oauth.refresh(server_url)
                if new_token:
                    return await mcp.call_tool(server_url, remote_name, tool_input,
                                               auth_token=new_token, auth_scheme=scheme)
            except Exception:  # noqa: BLE001
                pass
        return {"error": f"MCP tool '{record['name']}' failed: {e}", "degraded": True}


async def _dispatch_custom(record: dict, tool_input: dict) -> dict:
    cfg = record.get("config") or {}
    endpoint = cfg.get("endpoint")
    method = (cfg.get("method") or "GET").upper()
    if not endpoint:
        return {"error": f"Custom tool '{record['name']}' has no endpoint configured.", "degraded": True}
    headers = {}
    if cfg.get("auth_type") == "bearer" and cfg.get("auth_value"):
        headers[cfg.get("auth_header") or "Authorization"] = f"Bearer {cfg['auth_value']}"
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as c:
            if method == "GET":
                r = await c.get(endpoint, params=tool_input, headers=headers)
            else:
                r = await c.request(method, endpoint, json=tool_input, headers=headers)
        ctype = r.headers.get("content-type", "")
        body = r.json() if "application/json" in ctype else r.text[:8000]
        return {"status_code": r.status_code, "body": body}
    except Exception as e:  # noqa: BLE001
        return {"error": f"custom tool '{record['name']}' failed: {e}", "degraded": True}
