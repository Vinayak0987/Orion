"""MCP Streamable-HTTP transport tests (mocked, offline).

Verifies the client does the initialize handshake, parses SSE-framed responses,
reuses the Mcp-Session-Id header, and surfaces tool discovery + calls — without
touching the network.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx


def _sse(obj: dict) -> httpx.Response:
    """An SSE-framed JSON-RPC response (what Streamable HTTP servers return)."""
    body = f"event: message\ndata: {json.dumps(obj)}\n\n"
    return httpx.Response(200, headers={"content-type": "text/event-stream", "mcp-session-id": "sess-123"}, text=body)


@pytest.mark.asyncio
async def test_streamable_discover_and_handshake():
    from app.tools import mcp

    url = "https://mcp.example.ai/mcp"
    calls = {"methods": []}

    def router(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload.get("method")
        calls["methods"].append(method)
        # Client must advertise it accepts an event stream.
        assert "text/event-stream" in request.headers.get("accept", "")
        if method == "initialize":
            return _sse({"jsonrpc": "2.0", "id": payload["id"],
                         "result": {"protocolVersion": "2025-06-18", "capabilities": {}}})
        if method == "notifications/initialized":
            return httpx.Response(202)  # notification → no body
        if method == "tools/list":
            # Session id from initialize must be echoed back.
            assert request.headers.get("mcp-session-id") == "sess-123"
            return _sse({"jsonrpc": "2.0", "id": payload["id"], "result": {"tools": [
                {"name": "ask_question", "description": "Ask the wiki", "inputSchema": {}},
            ]}})
        return httpx.Response(400)

    with respx.mock:
        respx.post(url).mock(side_effect=router)
        tools = await mcp.discover_tools(url)

    assert [t["name"] for t in tools] == ["ask_question"]
    assert "initialize" in calls["methods"] and "tools/list" in calls["methods"]


@pytest.mark.asyncio
async def test_streamable_call_tool_parses_sse_content():
    from app.tools import mcp

    url = "https://mcp.example.ai/mcp"

    def router(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload.get("method")
        if method == "initialize":
            return _sse({"jsonrpc": "2.0", "id": payload["id"], "result": {}})
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "tools/call":
            return _sse({"jsonrpc": "2.0", "id": payload["id"],
                         "result": {"content": [{"type": "text", "text": "hello from mcp"}]}})
        return httpx.Response(400)

    with respx.mock:
        respx.post(url).mock(side_effect=router)
        out = await mcp.call_tool(url, "ask_question", {"q": "hi"})

    assert out["text"] == "hello from mcp"


@pytest.mark.asyncio
async def test_plain_json_still_supported():
    """Older/simple MCP servers that reply with plain application/json still work."""
    from app.tools import mcp

    url = "http://localhost:9000/mcp"

    def router(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload.get("method")
        if method == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": {}})
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "tools/list":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"],
                                             "result": {"tools": [{"name": "ping", "description": "p", "inputSchema": {}}]}})
        return httpx.Response(400)

    with respx.mock:
        respx.post(url).mock(side_effect=router)
        tools = await mcp.discover_tools(url)

    assert tools[0]["name"] == "ping"


@pytest.mark.asyncio
async def test_auth_401_surfaces_clear_error():
    from app.tools import mcp

    url = "https://mcp.secure.ai/mcp"
    with respx.mock:
        respx.post(url).mock(return_value=httpx.Response(401))
        with pytest.raises(mcp.MCPError):
            await mcp.discover_tools(url)
