"""Offline regression tests for the authentication module.

Fully offline: the user data layer is backed by an in-process mongomock client
(no server, no socket), and JWT/Argon2 are local. These tests import only
app.auth + app.generation.config, so they run without the agent stack
(langgraph/chromadb/structlog).

A minimal FastAPI app mounts just the auth router, so we exercise the real HTTP
surface (cookies, status codes, dependencies) without booting the full app.
"""

from __future__ import annotations

import mongomock
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import security, store
from app.auth.deps import get_current_user
from app.auth.models import UserPublic
from app.auth.router import router as auth_router


@pytest.fixture
def client(monkeypatch) -> TestClient:
    # Deterministic cookie behavior regardless of the developer's .env: in
    # development the refresh cookie is not marked Secure, so it flows over the
    # TestClient's http transport.
    from app.generation.config import settings as _settings

    monkeypatch.setattr(_settings, "app_env", "development")

    # Fresh in-memory Mongo per test.
    store.reset_for_tests()
    store.configure(mongomock.MongoClient(), db_name="orion_test")

    app = FastAPI()
    app.include_router(auth_router)

    # A protected probe route to exercise get_current_user without the real app.
    @app.get("/protected")
    def protected(user: UserPublic = Depends(get_current_user)):
        return {"email": user.email}

    with TestClient(app) as c:
        yield c

    store.reset_for_tests()


SIGNUP = {"full_name": "Ada Lovelace", "email": "ada@example.com", "password": "Sup3rSecret"}


# --------------------------------------------------------------------------- #
# Signup
# --------------------------------------------------------------------------- #
def test_signup_creates_user_and_returns_token(client):
    r = client.post("/auth/signup", json=SIGNUP)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["full_name"] == "Ada Lovelace"
    assert "password" not in body["user"]
    # Refresh token delivered as an httpOnly cookie, not in the body.
    assert "orion_refresh" in r.cookies
    assert "password_hash" not in body["user"]


def test_signup_password_is_hashed_not_stored_plaintext(client):
    client.post("/auth/signup", json=SIGNUP)
    user = store.get_user_by_email("ada@example.com")
    assert user is not None
    assert user["password_hash"] != SIGNUP["password"]
    assert security.verify_password(SIGNUP["password"], user["password_hash"])


def test_signup_duplicate_email_conflicts(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/signup", json=SIGNUP)
    assert r.status_code == 409


def test_signup_email_is_case_insensitive(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post(
        "/auth/signup",
        json={**SIGNUP, "email": "ADA@example.com"},
    )
    assert r.status_code == 409


def test_signup_rejects_invalid_email(client):
    r = client.post("/auth/signup", json={**SIGNUP, "email": "not-an-email"})
    assert r.status_code == 422


def test_signup_rejects_short_password(client):
    r = client.post("/auth/signup", json={**SIGNUP, "password": "short"})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# Server-side password strength (cannot be bypassed by calling the API directly)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "weak",
    [
        "alllowercase1",   # no uppercase
        "ALLUPPERCASE1",   # no lowercase
        "NoDigitsHere",    # no digit
        "aaaaaaaa",        # lowercase only, no upper/digit
        "Ab1",             # too short
    ],
)
def test_signup_rejects_weak_password_even_via_direct_api(client, weak):
    # These requests skip the frontend entirely (the TestClient posts straight to
    # the API), proving the policy is enforced server-side.
    r = client.post("/auth/signup", json={**SIGNUP, "password": weak})
    assert r.status_code == 422, f"weak password {weak!r} should be rejected"


def test_signup_accepts_strong_password(client):
    r = client.post(
        "/auth/signup",
        json={**SIGNUP, "email": "strong@example.com", "password": "Str0ngPass"},
    )
    assert r.status_code == 201, r.text


def test_login_password_has_no_composition_rules(client):
    # Sign up with a compliant password, then confirm login accepts it back
    # without re-imposing composition checks (login must not reject existing
    # passwords that predate any policy).
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #
def test_login_success(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]
    assert "orion_refresh" in r.cookies


def test_login_wrong_password(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/login", json={"email": SIGNUP["email"], "password": "WrongPass1"})
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
# Protected route / me
# --------------------------------------------------------------------------- #
def test_me_requires_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_with_valid_token(client):
    token = client.post("/auth/signup", json=SIGNUP).json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "ada@example.com"


def test_protected_route_rejects_bad_token(client):
    r = client.get("/protected", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_protected_route_rejects_refresh_token_as_access(client):
    # A refresh token must not be accepted where an access token is required.
    _, _, _ = None, None, None
    token, _jti, _exp = security.create_refresh_token("someuser")
    r = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
# Refresh + logout (cookie flow)
# --------------------------------------------------------------------------- #
def test_refresh_rotates_and_returns_new_access_token(client):
    client.post("/auth/signup", json=SIGNUP)  # sets refresh cookie on the client
    r = client.post("/auth/refresh")
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]


def test_refresh_without_cookie_fails(client):
    # A brand-new client with no cookie jar entry.
    app = client.app
    with TestClient(app) as fresh:
        r = fresh.post("/auth/refresh")
    assert r.status_code == 401


def test_old_refresh_token_revoked_after_rotation(client):
    client.post("/auth/signup", json=SIGNUP)
    old_cookie = client.cookies.get("orion_refresh")
    # First refresh rotates (revokes old, issues new).
    client.post("/auth/refresh")
    # Replay the OLD refresh token explicitly — must be rejected.
    r = client.post("/auth/refresh", cookies={"orion_refresh": old_cookie})
    assert r.status_code == 401


def test_logout_revokes_refresh_token(client):
    client.post("/auth/signup", json=SIGNUP)
    used_cookie = client.cookies.get("orion_refresh")
    assert client.post("/auth/logout").status_code == 200
    r = client.post("/auth/refresh", cookies={"orion_refresh": used_cookie})
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
# security.py units
# --------------------------------------------------------------------------- #
def test_password_hash_roundtrip():
    h = security.hash_password("correct horse battery staple")
    assert security.verify_password("correct horse battery staple", h)
    assert not security.verify_password("wrong", h)


def test_expired_access_token_rejected(monkeypatch):
    from app.generation.config import settings

    monkeypatch.setattr(settings, "access_token_ttl_minutes", -1)  # already expired
    token = security.create_access_token("user123")
    with pytest.raises(security.TokenError):
        security.decode_token(token, expected_type=security.ACCESS_TOKEN_TYPE)


def test_token_type_mismatch_rejected():
    access = security.create_access_token("user123")
    with pytest.raises(security.TokenError):
        security.decode_token(access, expected_type=security.REFRESH_TOKEN_TYPE)
