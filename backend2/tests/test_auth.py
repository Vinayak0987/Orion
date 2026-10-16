"""Auth tests — fully offline using mongomock (no network, no real Atlas)."""

from __future__ import annotations

import mongomock
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """App with an in-process mongomock-backed auth store, fully isolated."""
    from app.auth import store as auth_store

    auth_store.reset_for_tests()
    mongo = mongomock.MongoClient()
    auth_store.configure(mongo, db_name="orion_test")

    # mongomock state can persist across clients in one process — drop clean.
    db = mongo["orion_test"]
    db.users.delete_many({})
    db.refresh_tokens.delete_many({})

    from app.main import app

    with TestClient(app) as c:
        yield c

    db.users.delete_many({})
    db.refresh_tokens.delete_many({})
    auth_store.reset_for_tests()


GOOD = {"full_name": "Test User", "email": "test@example.com", "password": "Secret123"}


def test_signup_returns_token_and_user(client):
    resp = client.post("/auth/signup", json=GOOD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == "test@example.com"
    assert body["user"]["full_name"] == "Test User"


def test_signup_rejects_weak_password(client):
    resp = client.post("/auth/signup", json={**GOOD, "password": "weak"})
    assert resp.status_code == 422


def test_signup_duplicate_email_409(client):
    client.post("/auth/signup", json=GOOD)
    resp = client.post("/auth/signup", json=GOOD)
    assert resp.status_code == 409


def test_login_succeeds_with_correct_password(client):
    client.post("/auth/signup", json=GOOD)
    resp = client.post("/auth/login", json={"email": GOOD["email"], "password": GOOD["password"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_wrong_password_401(client):
    client.post("/auth/signup", json=GOOD)
    resp = client.post("/auth/login", json={"email": GOOD["email"], "password": "WrongPass9"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_user_with_token(client):
    token = client.post("/auth/signup", json=GOOD).json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == GOOD["email"]


def test_update_me(client):
    token = client.post("/auth/signup", json=GOOD).json()["access_token"]
    resp = client.put(
        "/auth/me",
        json={"full_name": "Renamed User"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Renamed User"


def test_refresh_rotates_token(client):
    signup = client.post("/auth/signup", json=GOOD)
    # The refresh cookie is set by signup; TestClient keeps cookies.
    resp = client.post("/auth/refresh")
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_logout_clears_session(client):
    client.post("/auth/signup", json=GOOD)
    resp = client.post("/auth/logout")
    assert resp.status_code == 200
    # After logout the refresh token is revoked.
    refresh = client.post("/auth/refresh")
    assert refresh.status_code == 401
