"""Tools API tests (Plan 06) — list/execute/enable/custom/mcp/integrations."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "workspace_path", str(tmp_path / "ws"))
    from app.db import init_db

    init_db()
    from app.tools.integrations import seed_integrations
    from app.tools.seed import seed_builtin_tools

    seed_builtin_tools()
    seed_integrations()
    yield


@pytest.fixture
def client():
    from fastapi import FastAPI

    from app.api.tools import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---- Core -------------------------------------------------------------------
def test_list_tools_with_facets(client):
    r = client.get("/tools")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 100
    assert "category" in body["facets"] and body["facets"]["total"] >= 100


def test_filter_by_category(client):
    r = client.get("/tools?category=web")
    assert r.status_code == 200
    assert all(t["category"] == "web" for t in r.json()["tools"])


def test_get_single_tool(client):
    assert client.get("/tools/calculator").json()["name"] == "calculator"
    assert client.get("/tools/nope").status_code == 404


def test_enable_disable(client):
    assert client.put("/tools/calculator", json={"enabled": False}).status_code == 200
    assert client.get("/tools/calculator").json()["enabled"] is False
    client.put("/tools/calculator", json={"enabled": True})
    assert client.get("/tools/calculator").json()["enabled"] is True


def test_execute_tool(client):
    r = client.post("/tools/execute", json={"name": "calculator", "input": {"expression": "9*9"}})
    assert r.status_code == 200
    assert r.json()["ok"] and r.json()["result"]["result"] == 81


def test_execute_unknown_tool_404(client):
    assert client.post("/tools/execute", json={"name": "ghost", "input": {}}).status_code == 404


def test_builtin_cannot_be_deleted(client):
    assert client.delete("/tools/calculator").status_code == 422


# ---- Custom tools -----------------------------------------------------------
def test_create_and_delete_custom_tool(client):
    r = client.post("/tools/custom", json={
        "name": "inventory_lookup", "display_name": "Inventory Lookup",
        "description": "Query internal inventory by SKU for stock levels.",
        "category": "data", "endpoint": "https://api.example.com/inv", "method": "GET",
        "input_schema": {"sku": {"type": "string"}},
    })
    assert r.status_code == 201
    assert r.json()["tool"]["type"] == "custom"
    # Appears in the list filtered by custom
    assert any(t["name"] == "inventory_lookup" for t in client.get("/tools?type=custom").json()["tools"])
    # Deletable (unlike builtins)
    assert client.delete("/tools/inventory_lookup").status_code == 200


def test_custom_duplicate_name_rejected(client):
    assert client.post("/tools/custom", json={
        "name": "calculator", "display_name": "x", "description": "dup name should fail here",
        "endpoint": "https://x.com"}).status_code == 409


# ---- MCP (discovery mocked) -------------------------------------------------
def test_mcp_connect_discovers_and_registers(client, monkeypatch):
    import app.tools.mcp as mcp_mod

    async def fake_discover(url, auth_token=None, auth_scheme="bearer"):
        return [{"name": "read_file", "description": "Read a file", "inputSchema": {"type": "object"}},
                {"name": "write_file", "description": "Write a file", "inputSchema": {"type": "object"}}]

    monkeypatch.setattr(mcp_mod, "discover_tools", fake_discover)
    r = client.post("/tools/mcp", json={"server_url": "http://localhost:9000", "name": "FS"})
    assert r.status_code == 201
    assert r.json()["count"] == 2
    # Registered as mcp_* tools
    mcp_tools = client.get("/tools?type=mcp").json()["tools"]
    assert {t["name"] for t in mcp_tools} == {"mcp_read_file", "mcp_write_file"}
    # Listed as a server; disconnect DISABLES its tools (keeps them) so it can reconnect.
    servers = client.get("/tools/mcp").json()["servers"]
    assert len(servers) == 1
    sid = servers[0]["id"]
    r = client.delete(f"/tools/mcp/{sid}")
    assert r.json()["status"] == "disconnected" and r.json()["tools_disabled"] == 2
    # Tools still exist but are disabled; server stays in the list.
    assert client.get("/tools?type=mcp").json()["count"] == 2
    assert all(not t["enabled"] for t in client.get("/tools?type=mcp").json()["tools"])
    assert len(client.get("/tools/mcp").json()["servers"]) == 1
    # Reconnect re-enables them.
    r = client.post(f"/tools/mcp/{sid}/connect")
    assert r.json()["status"] == "connected" and r.json()["tools_enabled"] == 2
    assert all(t["enabled"] for t in client.get("/tools?type=mcp").json()["tools"])
    # Permanent remove deletes server + tools.
    r = client.delete(f"/tools/mcp/{sid}/remove")
    assert r.json()["tools_removed"] == 2
    assert client.get("/tools?type=mcp").json()["count"] == 0


def test_mcp_connect_unreachable_502(client, monkeypatch):
    import app.tools.mcp as mcp_mod

    async def boom(url, auth_token=None, auth_scheme="bearer"):
        raise mcp_mod.MCPError("connection refused")

    monkeypatch.setattr(mcp_mod, "discover_tools", boom)
    assert client.post("/tools/mcp", json={"server_url": "http://localhost:1"}).status_code == 502


def test_mcp_connect_with_auth_token_stored(client, monkeypatch):
    """A hosted MCP server with a bearer token: token is passed to discovery and
    stored encrypted (never returned)."""
    import app.tools.mcp as mcp_mod

    seen = {}

    async def fake_discover(url, auth_token=None, auth_scheme="bearer"):
        seen["token"] = auth_token
        return [{"name": "generate_image", "description": "make an image", "inputSchema": {}}]

    monkeypatch.setattr(mcp_mod, "discover_tools", fake_discover)
    r = client.post("/tools/mcp", json={"server_url": "https://mcp.example.ai/mcp", "name": "Imagen", "auth_token": "hf_secret"})
    assert r.status_code == 201 and r.json()["count"] == 1
    assert seen["token"] == "hf_secret"
    # Server lists with has_auth=True but no token value.
    servers = client.get("/tools/mcp").json()["servers"]
    s = next(x for x in servers if x["name"] == "Imagen")
    assert s["has_auth"] is True and "auth_token" not in s
    # The dispatch path can retrieve the decrypted token (internal only).
    tok, scheme = mcp_mod.get_server_auth("https://mcp.example.ai/mcp")
    assert tok == "hf_secret" and scheme == "bearer"


# ---- Catalog ----------------------------------------------------------------
def test_catalog_lists_everything_with_methods(client):
    body = client.get("/tools/catalog").json()
    items = {i["id"]: i for i in body["catalog"]}
    assert len(items) >= 30
    assert items["gmail"]["connect_method"] == "oauth" and items["gmail"]["oauth_provider"] == "google"
    assert items["stripe"]["connect_method"] == "api_key"
    assert items["higgsfield"]["connect_method"] == "mcp" and items["higgsfield"]["mcp_url"].startswith("https://")
    assert body["summary"]["connected"] == 0
    assert "communication" in body["groups"] and "social" in body["groups"]


def test_catalog_connect_api_key(client, monkeypatch):
    import app.tools.integrations as intg_mod

    async def fake_validate(integration_id, credential):
        return {"ok": True, "account_label": "acct"}

    monkeypatch.setattr(intg_mod, "validate_token", fake_validate)
    r = client.post("/tools/catalog/stripe/connect", json={"credential": "sk_test"})
    assert r.status_code == 200 and r.json()["status"] == "connected"
    stripe = next(i for i in client.get("/tools/catalog").json()["catalog"] if i["id"] == "stripe")
    assert stripe["status"] == "connected" and stripe["has_credential"] is True
    assert "credential" not in stripe


def test_catalog_connect_oauth_returns_provider(client):
    # google OAuth may or may not be configured in the test env; either way the
    # response is honest (provider ref, or a 501 'not configured').
    r = client.post("/tools/catalog/gmail/connect", json={})
    assert r.status_code in (200, 501)
    if r.status_code == 200:
        assert r.json()["method"] == "oauth" and r.json()["provider"] == "google"


def test_catalog_connect_mcp_discovers(client, monkeypatch):
    import app.tools.mcp as mcp_mod

    async def fake_discover(url, auth_token=None, auth_scheme="bearer"):
        return [{"name": "gen_video", "description": "make a video", "inputSchema": {}}]

    monkeypatch.setattr(mcp_mod, "discover_tools", fake_discover)
    r = client.post("/tools/catalog/higgsfield/connect", json={"credential": "hf_tok"})
    assert r.status_code == 200 and r.json()["status"] == "connected"
    # Its MCP tool is now registered + usable by agents.
    assert any(t["name"] == "mcp_gen_video" for t in client.get("/tools?type=mcp").json()["tools"])
    hf = next(i for i in client.get("/tools/catalog").json()["catalog"] if i["id"] == "higgsfield")
    assert hf["status"] == "connected"


def test_catalog_connect_disconnect(client, monkeypatch):
    import app.tools.integrations as intg_mod

    async def ok_validate(integration_id, credential):
        return {"ok": True, "account_label": "x"}

    monkeypatch.setattr(intg_mod, "validate_token", ok_validate)
    client.post("/tools/catalog/sendgrid/connect", json={"credential": "SG.x"})
    r = client.post("/tools/catalog/sendgrid/disconnect")
    assert r.json()["status"] == "available"


def test_connect_rejects_invalid_token(client, monkeypatch):
    import app.tools.integrations as intg_mod

    async def fake_validate(integration_id, credential):
        return {"ok": False, "error": "Stripe rejected the key (HTTP 401)."}

    monkeypatch.setattr(intg_mod, "validate_token", fake_validate)
    r = client.post("/tools/integrations/stripe/connect", json={"credential": "sk_bad"})
    assert r.status_code == 400
    assert "rejected" in r.json()["detail"]


def test_connect_requires_credential(client):
    assert client.post("/tools/integrations/stripe/connect", json={}).status_code == 422
