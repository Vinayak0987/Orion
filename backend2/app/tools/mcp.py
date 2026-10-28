"""MCP (Model Context Protocol) client + server registry.

Speaks MCP's JSON-RPC 2.0 over HTTP:
  • tools/list  → discover a server's tools
  • tools/call  → invoke a tool

On connect we discover the server's tools and register each one in the `tools`
table with type='mcp' and config={server_url, mcp_server_id, remote_name}. The
registry's dispatch mcp-branch calls `call_tool` to proxy at runtime.

All network failures degrade to structured results/raised ClientError that the
API layer turns into a clear message — never a 500.
"""

from __future__ import annotations

import json
import uuid

import httpx

from app.db.sqlite import _now, connection

# MCP protocol version we advertise during initialize.
MCP_PROTOCOL_VERSION = "2025-06-18"
_ACCEPT = "application/json, text/event-stream"


class MCPError(Exception):
    pass


def _parse_rpc_body(resp: httpx.Response) -> dict:
    """Parse an MCP response that may be plain JSON OR an SSE event stream.
    Streamable HTTP servers reply with `text/event-stream` where the JSON-RPC
    message is on a `data:` line. We return the first JSON-RPC object found."""
    ctype = resp.headers.get("content-type", "")
    text = resp.text
    if "text/event-stream" in ctype or text.lstrip().startswith("event:") or "\ndata:" in text or text.startswith("data:"):
        # Walk SSE frames; collect `data:` payloads, return the first that parses
        # to a JSON-RPC object (has 'result' or 'error' or 'id').
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                obj = json.loads(payload)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(obj, dict) and ("result" in obj or "error" in obj or "id" in obj):
                return obj
        raise MCPError("MCP server returned an event stream with no JSON-RPC message")
    # Plain JSON
    try:
        return resp.json()
    except Exception as e:  # noqa: BLE001
        raise MCPError("MCP server returned non-JSON response") from e


async def _post(client: httpx.AsyncClient, server_url: str, method: str, params: dict | None,
                *, session_id: str | None, auth_token: str | None, auth_scheme: str,
                notification: bool = False) -> tuple[dict | None, str | None]:
    """POST one JSON-RPC message. Returns (parsed_result_or_none, session_id).
    For notifications (no id) we don't expect a response body."""
    msg = {"jsonrpc": "2.0", "method": method}
    if not notification:
        msg["id"] = uuid.uuid4().hex[:8]
    if params is not None:
        msg["params"] = params
    headers = {"Content-Type": "application/json", "Accept": _ACCEPT}
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    if auth_token:
        if (auth_scheme or "bearer").lower() == "bearer":
            headers["Authorization"] = f"Bearer {auth_token}"
        else:
            headers[auth_scheme] = auth_token
    try:
        r = await client.post(server_url, json=msg, headers=headers)
    except httpx.HTTPError as e:
        raise MCPError(f"could not reach MCP server: {e}") from e

    new_session = r.headers.get("mcp-session-id") or r.headers.get("Mcp-Session-Id") or session_id
    if r.status_code == 401:
        raise MCPError("MCP server requires authentication (401) — provide a valid token.")
    if r.status_code == 404 and session_id:
        raise MCPError("MCP session expired (404).")
    if r.status_code >= 400:
        raise MCPError(f"MCP server returned HTTP {r.status_code}: {r.text[:160]}")
    if notification or r.status_code == 202 or not r.content:
        return (None, new_session)
    data = _parse_rpc_body(r)
    if "error" in data:
        raise MCPError(str(data["error"]))
    return (data.get("result", {}), new_session)


async def _session(client: httpx.AsyncClient, server_url: str, auth_token: str | None, auth_scheme: str) -> str | None:
    """Perform the MCP initialize handshake. Returns the session id (may be None
    for servers that don't use sessions). Safe no-op style: on any handshake
    error we raise MCPError so the caller degrades."""
    result, session_id = await _post(
        client, server_url, "initialize",
        {"protocolVersion": MCP_PROTOCOL_VERSION,
         "capabilities": {},
         "clientInfo": {"name": "Orion", "version": "2.0.0"}},
        session_id=None, auth_token=auth_token, auth_scheme=auth_scheme,
    )
    # Tell the server we're initialized (best-effort notification).
    try:
        await _post(client, server_url, "notifications/initialized", None,
                    session_id=session_id, auth_token=auth_token, auth_scheme=auth_scheme,
                    notification=True)
    except MCPError:
        pass
    return session_id


async def _rpc(server_url: str, method: str, params: dict | None = None, timeout: float = 20.0,
               auth_token: str | None = None, auth_scheme: str = "bearer") -> dict:
    """One full Streamable-HTTP MCP call: initialize handshake, then the method."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        session_id = await _session(client, server_url, auth_token, auth_scheme)
        result, _ = await _post(client, server_url, method, params,
                                session_id=session_id, auth_token=auth_token, auth_scheme=auth_scheme)
        return result or {}


async def discover_tools(server_url: str, auth_token: str | None = None, auth_scheme: str = "bearer") -> list[dict]:
    """Call tools/list. Returns [{name, description, inputSchema}]."""
    result = await _rpc(server_url, "tools/list", auth_token=auth_token, auth_scheme=auth_scheme)
    tools = result.get("tools")
    if not isinstance(tools, list):
        raise MCPError("MCP server did not return a tools list")
    return tools


async def call_tool(server_url: str, remote_name: str, arguments: dict,
                    auth_token: str | None = None, auth_scheme: str = "bearer") -> dict:
    """Call tools/call and normalise the result."""
    result = await _rpc(server_url, "tools/call", {"name": remote_name, "arguments": arguments or {}},
                        auth_token=auth_token, auth_scheme=auth_scheme)
    content = result.get("content")
    if isinstance(content, list):
        texts = [c.get("text") for c in content if isinstance(c, dict) and c.get("type") == "text"]
        return {"content": content, "text": "\n".join(t for t in texts if t), "is_error": result.get("isError", False)}
    return {"result": result}


# ---- mcp_servers store ------------------------------------------------------

def create_server(*, name: str, server_url: str, description: str = "", tool_count: int = 0,
                  auth_token: str | None = None, auth_scheme: str = "bearer",
                  refresh_token: str | None = None, oauth_config: str | None = None) -> str:
    from app.core.crypto import encrypt

    sid = uuid.uuid4().hex
    now = _now()
    enc = encrypt(auth_token) if auth_token else None
    enc_refresh = encrypt(refresh_token) if refresh_token else None
    with connection() as conn:
        conn.execute(
            """INSERT INTO mcp_servers (id, name, description, server_url, status, tool_count, last_active, auth_token, auth_scheme, refresh_token, oauth_config, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(server_url) DO UPDATE SET name=excluded.name, description=excluded.description,
                 status='connected', tool_count=excluded.tool_count, last_active=excluded.last_active,
                 auth_token=excluded.auth_token, auth_scheme=excluded.auth_scheme,
                 refresh_token=excluded.refresh_token, oauth_config=excluded.oauth_config""",
            (sid, name, description, server_url, "connected", tool_count, now, enc, auth_scheme,
             enc_refresh, oauth_config, now),
        )
        row = conn.execute("SELECT id FROM mcp_servers WHERE server_url=?", (server_url,)).fetchone()
    return row["id"]


def update_server_tokens(server_url: str, access_token: str, refresh_token: str | None) -> None:
    """Rotate tokens after a refresh. Keeps the old refresh token if none returned."""
    from app.core.crypto import encrypt

    with connection() as conn:
        row = conn.execute("SELECT refresh_token FROM mcp_servers WHERE server_url=?", (server_url,)).fetchone()
        keep = row["refresh_token"] if row else None
        new_refresh = encrypt(refresh_token) if refresh_token else keep
        conn.execute(
            "UPDATE mcp_servers SET auth_token=?, refresh_token=?, last_active=? WHERE server_url=?",
            (encrypt(access_token), new_refresh, _now(), server_url),
        )


def list_servers() -> list[dict]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM mcp_servers ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        rec = dict(r)
        rec["has_auth"] = bool(rec.pop("auth_token", None))  # never expose the token
        out.append(rec)
    return out


def get_server(server_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM mcp_servers WHERE id=?", (server_id,)).fetchone()
    if not row:
        return None
    rec = dict(row)
    rec["has_auth"] = bool(rec.get("auth_token"))
    rec.pop("auth_token", None)
    return rec


def get_server_auth(server_url: str) -> tuple[str | None, str]:
    """Decrypted (token, scheme) for a server url — for dispatch only, never over API."""
    from app.core.crypto import decrypt

    with connection() as conn:
        row = conn.execute("SELECT auth_token, auth_scheme FROM mcp_servers WHERE server_url=?", (server_url,)).fetchone()
    if not row:
        return (None, "bearer")
    return (decrypt(row["auth_token"]) if row["auth_token"] else None, row["auth_scheme"] or "bearer")


def delete_server(server_id: str) -> bool:
    with connection() as conn:
        cur = conn.execute("DELETE FROM mcp_servers WHERE id=?", (server_id,))
    return cur.rowcount > 0


def set_server_status(server_id: str, status: str) -> bool:
    """Flip connected/disconnected WITHOUT deleting the server or its tools."""
    with connection() as conn:
        cur = conn.execute(
            "UPDATE mcp_servers SET status=?, last_active=? WHERE id=?", (status, _now(), server_id)
        )
    return cur.rowcount > 0
