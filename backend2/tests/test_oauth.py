"""OAuth 2.0 tests with a fully mocked provider (offline).

Covers: authorize URL + state + PKCE, state mismatch/CSRF rejection, code
exchange success/failure, token encryption at rest, auto-refresh + rotation,
user isolation, disconnect, and the tool-execution token provider.

A fake provider 'mock' is injected into the registry and its token/userinfo HTTP
calls are intercepted with respx so nothing hits the network.
"""

from __future__ import annotations

import datetime as dt

import httpx
import pytest
import respx


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "oauth_redirect_base", "http://localhost:8081")
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:5173")
    from app.db import init_db

    init_db()

    # Inject a fully-configured mock provider with PKCE.
    from app.oauth import providers as prov

    prov.reset_registry()
    reg = prov.registry()
    reg["mock"] = prov.Provider(
        id="mock", name="MockProvider",
        authorize_url="https://mock.test/authorize",
        token_url="https://mock.test/token",
        scopes=["read", "write"],
        client_id="mock-client", client_secret="mock-secret",
        pkce=True,
        userinfo_url="https://mock.test/me",
        account_from=lambda tok, info: (info.get("id", ""), info.get("name", "Mock")),
    )
    yield
    prov.reset_registry()


# ---- authorize + PKCE + state ----------------------------------------------
def test_authorize_url_has_state_and_pkce():
    from app.oauth import service, store

    url, state = service.build_authorize_url("user-1", "mock")
    assert "https://mock.test/authorize?" in url
    assert f"state={state}" in url
    assert "code_challenge=" in url and "code_challenge_method=S256" in url
    assert "client_secret" not in url  # secret never in the browser URL
    # State persisted with a PKCE verifier.
    st = store.consume_state(state)
    assert st["user_id"] == "user-1" and st["code_verifier"]


def test_unconfigured_provider_rejected(monkeypatch):
    from app.oauth import providers as prov
    from app.oauth import service

    prov.registry()["mock"].client_id = ""  # unconfigure
    with pytest.raises(service.OAuthError):
        service.build_authorize_url("user-1", "mock")


# ---- code exchange ----------------------------------------------------------
@pytest.mark.asyncio
async def test_exchange_code_stores_encrypted_connection():
    from app.db.sqlite import connection
    from app.oauth import service, store

    url, state = service.build_authorize_url("user-1", "mock")

    with respx.mock:
        respx.post("https://mock.test/token").mock(return_value=httpx.Response(
            200, json={"access_token": "AT-123", "refresh_token": "RT-123",
                       "expires_in": 3600, "scope": "read write"}))
        respx.get("https://mock.test/me").mock(return_value=httpx.Response(
            200, json={"id": "acct-9", "name": "Alice"}))
        result = await service.exchange_code("mock", "the-code", state)

    assert result["account_label"] == "Alice"
    # Token is retrievable decrypted via the private accessor...
    conn = store.get_connection("user-1", "mock")
    assert conn["access_token"] == "AT-123" and conn["refresh_token"] == "RT-123"
    # ...but stored ENCRYPTED (ciphertext != plaintext in the raw row).
    with connection() as c:
        raw = c.execute("SELECT access_token FROM oauth_connections WHERE user_id='user-1'").fetchone()
    assert raw["access_token"] != "AT-123" and raw["access_token"].startswith("enc:")
    # Public view never exposes tokens.
    pub = store.public("user-1", "mock")
    assert "access_token" not in pub and pub["connected"] is True


@pytest.mark.asyncio
async def test_state_mismatch_rejected():
    from app.oauth import service

    with pytest.raises(service.OAuthError):
        await service.exchange_code("mock", "code", "never-issued-state")


@pytest.mark.asyncio
async def test_state_is_one_time_use():
    from app.oauth import service

    _, state = service.build_authorize_url("user-1", "mock")
    with respx.mock:
        respx.post("https://mock.test/token").mock(return_value=httpx.Response(
            200, json={"access_token": "AT", "expires_in": 3600}))
        respx.get("https://mock.test/me").mock(return_value=httpx.Response(200, json={"id": "x", "name": "X"}))
        await service.exchange_code("mock", "code", state)
    # Re-using the same state must now fail (consumed).
    with pytest.raises(service.OAuthError):
        await service.exchange_code("mock", "code", state)


@pytest.mark.asyncio
async def test_exchange_failure_from_provider():
    from app.oauth import service

    _, state = service.build_authorize_url("user-1", "mock")
    with respx.mock:
        respx.post("https://mock.test/token").mock(return_value=httpx.Response(
            400, json={"error": "invalid_grant"}))
        with pytest.raises(service.OAuthError):
            await service.exchange_code("mock", "bad-code", state)


# ---- refresh + rotation -----------------------------------------------------
@pytest.mark.asyncio
async def test_auto_refresh_on_expired_token_and_rotation():
    from app.oauth import service, store

    # Seed a connection that is already expired, with a refresh token.
    past = (dt.datetime.now(dt.UTC) - dt.timedelta(minutes=5)).isoformat()
    store.upsert_connection(user_id="user-1", provider="mock", access_token="OLD-AT",
                            refresh_token="RT-1", expires_at=past, scopes=["read"],
                            account_id="a", account_label="Alice")
    with respx.mock:
        respx.post("https://mock.test/token").mock(return_value=httpx.Response(
            200, json={"access_token": "NEW-AT", "refresh_token": "RT-2", "expires_in": 3600}))
        token = await service.get_valid_access_token("user-1", "mock")
    assert token == "NEW-AT"
    conn = store.get_connection("user-1", "mock")
    assert conn["access_token"] == "NEW-AT" and conn["refresh_token"] == "RT-2"  # rotated


@pytest.mark.asyncio
async def test_refresh_keeps_old_refresh_token_when_none_returned():
    from app.oauth import service, store

    past = (dt.datetime.now(dt.UTC) - dt.timedelta(minutes=5)).isoformat()
    store.upsert_connection(user_id="user-1", provider="mock", access_token="OLD",
                            refresh_token="RT-keep", expires_at=past, scopes=[], account_label="A")
    with respx.mock:
        respx.post("https://mock.test/token").mock(return_value=httpx.Response(
            200, json={"access_token": "NEW", "expires_in": 3600}))  # no new refresh_token
        await service.refresh("user-1", "mock")
    assert store.get_connection("user-1", "mock")["refresh_token"] == "RT-keep"


# ---- user isolation ---------------------------------------------------------
@pytest.mark.asyncio
async def test_user_isolation():
    from app.oauth import store

    store.upsert_connection(user_id="user-1", provider="mock", access_token="A1",
                            refresh_token=None, expires_at=None, scopes=[], account_label="One")
    store.upsert_connection(user_id="user-2", provider="mock", access_token="A2",
                            refresh_token=None, expires_at=None, scopes=[], account_label="Two")
    assert store.get_connection("user-1", "mock")["access_token"] == "A1"
    assert store.get_connection("user-2", "mock")["access_token"] == "A2"
    assert len(store.list_public("user-1")) == 1
    # Deleting user-1's connection leaves user-2 intact.
    store.delete_connection("user-1", "mock")
    assert store.get_connection("user-1", "mock") is None
    assert store.get_connection("user-2", "mock")["access_token"] == "A2"


# ---- disconnect / revoke ----------------------------------------------------
@pytest.mark.asyncio
async def test_disconnect_removes_connection():
    from app.oauth import service, store

    store.upsert_connection(user_id="user-1", provider="mock", access_token="A",
                            refresh_token=None, expires_at=None, scopes=[], account_label="A")
    assert await service.revoke("user-1", "mock") is True
    assert store.public("user-1", "mock") is None


# ---- tool-execution token provider -----------------------------------------
@pytest.mark.asyncio
async def test_tool_token_provider_returns_valid_token():
    from app.oauth import store, tokens

    future = (dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)).isoformat()
    store.upsert_connection(user_id="user-1", provider="mock", access_token="LIVE-AT",
                            refresh_token=None, expires_at=future, scopes=[], account_label="A")
    assert await tokens.token_for("user-1", "mock") == "LIVE-AT"
    # No connection → None (tool degrades, never crashes).
    assert await tokens.token_for("user-1", "github") is None


# ---- API router wiring (auth required) --------------------------------------
def test_authorize_endpoint_requires_auth():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.oauth import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    # No bearer token → 401 from get_current_user.
    assert client.get("/oauth/mock/authorize").status_code == 401


def test_callback_redirects_without_exposing_secrets():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.oauth import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, follow_redirects=False)
    # Error from provider → redirect to frontend with status=failed, no secrets.
    r = client.get("/oauth/mock/callback", params={"error": "access_denied"})
    assert r.status_code in (302, 307)
    loc = r.headers["location"]
    assert "status=failed" in loc and "secret" not in loc
