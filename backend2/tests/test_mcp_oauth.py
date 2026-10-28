"""MCP OAuth (auto-discovery + Dynamic Client Registration) tests — mocked.

Simulates an OAuth-protected MCP server (401 + RFC 9728 metadata + RFC 8414
AS metadata + RFC 7591 registration + token endpoint) with respx, and verifies
the full begin() → authorize URL and exchange() → tokens flow offline.
"""

from __future__ import annotations

import httpx
import pytest
import respx

MCP_URL = "https://mcp.fake.ai/mcp"
AS = "https://auth.fake.ai"


def _mount(respx_mock):
    # 1) MCP probe → 401 advertising the protected-resource metadata.
    respx_mock.post(MCP_URL).mock(return_value=httpx.Response(
        401, headers={"www-authenticate": f'Bearer resource_metadata="{AS}/.well-known/oauth-protected-resource/mcp"'},
        json={"error": "Authentication required"}))
    # 2) protected-resource metadata
    respx_mock.get(f"{AS}/.well-known/oauth-protected-resource/mcp").mock(return_value=httpx.Response(
        200, json={"resource": MCP_URL, "authorization_servers": [AS],
                   "scopes_supported": ["openid", "offline_access"]}))
    # 3) authorization-server metadata
    respx_mock.get(f"{AS}/.well-known/oauth-authorization-server").mock(return_value=httpx.Response(
        200, json={"issuer": AS, "authorization_endpoint": f"{AS}/authorize",
                   "token_endpoint": f"{AS}/token", "registration_endpoint": f"{AS}/register",
                   "code_challenge_methods_supported": ["S256"]}))
    # 4) dynamic client registration
    respx_mock.post(f"{AS}/register").mock(return_value=httpx.Response(
        201, json={"client_id": "dyn-client-123"}))


@pytest.mark.asyncio
async def test_begin_discovers_registers_and_builds_authorize_url():
    from app.oauth import mcp_oauth

    with respx.mock(assert_all_called=False) as rmock:
        _mount(rmock)
        url = await mcp_oauth.begin(MCP_URL, "FakeFal")

    assert url.startswith(f"{AS}/authorize?")
    assert "client_id=dyn-client-123" in url
    assert "code_challenge=" in url and "code_challenge_method=S256" in url
    assert "response_type=code" in url and "state=" in url


@pytest.mark.asyncio
async def test_exchange_code_returns_tokens():
    from app.oauth import mcp_oauth

    with respx.mock(assert_all_called=False) as rmock:
        _mount(rmock)
        url = await mcp_oauth.begin(MCP_URL, "FakeFal")
        # Pull the state the flow persisted out of the URL.
        from urllib.parse import parse_qs, urlparse
        state = parse_qs(urlparse(url).query)["state"][0]

        rmock.post(f"{AS}/token").mock(return_value=httpx.Response(
            200, json={"access_token": "AT-xyz", "refresh_token": "RT-xyz", "expires_in": 3600}))
        res = await mcp_oauth.exchange(state, "the-auth-code")

    assert res["access_token"] == "AT-xyz"
    assert res["refresh_token"] == "RT-xyz"
    assert res["mcp_url"] == MCP_URL


@pytest.mark.asyncio
async def test_exchange_rejects_bad_state():
    from app.oauth import mcp_oauth

    with pytest.raises(mcp_oauth.MCPOAuthError):
        await mcp_oauth.exchange("never-issued", "code")


@pytest.mark.asyncio
async def test_begin_errors_when_server_not_oauth():
    from app.oauth import mcp_oauth

    with respx.mock(assert_all_called=False) as rmock:
        rmock.post(MCP_URL).mock(return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": "x", "result": {}}))
        with pytest.raises(mcp_oauth.MCPOAuthError):
            await mcp_oauth.begin(MCP_URL, "x")
