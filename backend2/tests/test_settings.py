"""Settings tests: encryption roundtrip, API key store/mask/delete, key-flow
into missions, and the password-change endpoint. All offline."""

from __future__ import annotations

import mongomock
import pytest
from fastapi.testclient import TestClient


# --- crypto ------------------------------------------------------------------

def test_crypto_roundtrip():
    from app.core.crypto import decrypt, encrypt

    secret = "gsk_live_abcd1234"
    enc = encrypt(secret)
    assert enc.startswith("enc:")
    assert enc != secret
    assert decrypt(enc) == secret


def test_crypto_legacy_plaintext_passthrough():
    from app.core.crypto import decrypt

    # A value stored before encryption (no enc: prefix) is returned as-is.
    assert decrypt("plain_old_key") == "plain_old_key"


def test_crypto_empty():
    from app.core.crypto import decrypt, encrypt

    assert encrypt("") == ""
    assert decrypt("") == ""


# --- settings store ----------------------------------------------------------

def test_store_set_and_decrypt():
    from app.settings import store

    store.set_keys({"groq_api_key": "gsk_secret9999"})
    plain = store.decrypted_keys()
    assert plain["groq_api_key"] == "gsk_secret9999"


def test_store_masks_keys():
    from app.settings import store

    store.set_keys({"serper_api_key": "srp_abcd1234"})
    masked = store.masked_keys()
    assert masked["serper"] == "...1234"
    assert masked["groq"] is None  # unset


def test_store_stored_encrypted_not_plaintext():
    import json

    from app.db.sqlite import connection
    from app.settings import store

    store.set_keys({"gemini_api_key": "AIza_plaintext_xyz"})
    with connection() as conn:
        row = conn.execute(
            "SELECT api_keys FROM user_settings WHERE user_id = 'default-user'"
        ).fetchone()
    raw = json.loads(row["api_keys"])["gemini_api_key"]
    assert raw.startswith("enc:")
    assert "plaintext" not in raw


def test_store_delete_key():
    from app.settings import store

    store.set_keys({"groq_api_key": "gsk_todelete"})
    assert store.delete_key("groq") is True
    assert store.decrypted_keys().get("groq_api_key") is None
    assert store.delete_key("groq") is False  # already gone


# --- settings API ------------------------------------------------------------

def test_settings_api_put_get_delete():
    from app.main import app

    with TestClient(app) as c:
        c.put("/settings/api-keys", json={"groq_api_key": "gsk_apitest1234"})
        masked = c.get("/settings/api-keys").json()
        assert masked["groq"] == "...1234"

        d = c.delete("/settings/api-keys/groq")
        assert d.status_code == 200
        assert c.get("/settings/api-keys").json()["groq"] is None


def test_settings_api_delete_unknown_provider_404():
    from app.main import app

    with TestClient(app) as c:
        assert c.delete("/settings/api-keys/notreal").status_code == 404


# --- key-flow into missions --------------------------------------------------

async def test_user_keys_flow_into_mission(monkeypatch):
    """The engine must load the user's stored keys onto the mission so the
    LLMClient receives them."""
    from app.settings import store as settings_store

    settings_store.set_keys({"groq_api_key": "gsk_mission_key"})

    captured = {}

    class FakeLLM:
        def __init__(self, user_keys=None):
            captured["user_keys"] = user_keys

        async def call_structured(self, *a, **k):
            return []  # empty plan → mission fails fast, enough to check keys loaded

        async def call_text(self, *a, **k):
            from app.llm.providers import LLMResult
            return LLMResult(text="t", provider="x", model="x")

    import app.missions.engine as engine_mod
    monkeypatch.setattr(engine_mod, "LLMClient", FakeLLM)

    from app.missions import engine, store

    mid = store.create_mission("do something", "default-user")
    await engine.run_mission(mid)

    assert captured["user_keys"]["groq_api_key"] == "gsk_mission_key"


# --- password change ---------------------------------------------------------

@pytest.fixture
def auth_client():
    from app.auth import store as auth_store

    auth_store.reset_for_tests()
    mongo = mongomock.MongoClient()
    auth_store.configure(mongo, db_name="orion_test")
    mongo["orion_test"].users.delete_many({})
    mongo["orion_test"].refresh_tokens.delete_many({})

    from app.main import app

    with TestClient(app) as c:
        yield c

    mongo["orion_test"].users.delete_many({})
    mongo["orion_test"].refresh_tokens.delete_many({})
    auth_store.reset_for_tests()


def test_change_password(auth_client):
    signup = auth_client.post(
        "/auth/signup",
        json={"full_name": "P W", "email": "pw@example.com", "password": "Secret123"},
    ).json()
    token = signup["access_token"]

    resp = auth_client.put(
        "/auth/password",
        json={"current_password": "Secret123", "new_password": "NewSecret456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Old password now fails, new one works.
    assert auth_client.post(
        "/auth/login", json={"email": "pw@example.com", "password": "Secret123"}
    ).status_code == 401
    assert auth_client.post(
        "/auth/login", json={"email": "pw@example.com", "password": "NewSecret456"}
    ).status_code == 200


def test_change_password_wrong_current(auth_client):
    token = auth_client.post(
        "/auth/signup",
        json={"full_name": "P W", "email": "pw2@example.com", "password": "Secret123"},
    ).json()["access_token"]

    resp = auth_client.put(
        "/auth/password",
        json={"current_password": "WrongOne9", "new_password": "NewSecret456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
