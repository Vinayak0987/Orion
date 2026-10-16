"""Workspace + extended-profile tests — offline via mongomock."""

from __future__ import annotations

import mongomock
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.auth import store as auth_store

    auth_store.reset_for_tests()
    mongo = mongomock.MongoClient()
    auth_store.configure(mongo, db_name="orion_test")
    for coll in ("users", "refresh_tokens", "workspaces", "members"):
        mongo["orion_test"][coll].delete_many({})

    from app.main import app

    with TestClient(app) as c:
        yield c

    for coll in ("users", "refresh_tokens", "workspaces", "members"):
        mongo["orion_test"][coll].delete_many({})
    auth_store.reset_for_tests()


def _signup(client):
    body = client.post(
        "/auth/signup",
        json={"full_name": "Jane Doe", "email": "jane@example.com", "password": "Secret123"},
    ).json()
    return body["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# --- extended profile fields -------------------------------------------------

def test_profile_job_title_and_bio(client):
    token = _signup(client)
    resp = client.put(
        "/auth/me",
        json={"job_title": "AI Engineer", "bio": "Builds agents."},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_title"] == "AI Engineer"
    assert body["bio"] == "Builds agents."

    me = client.get("/auth/me", headers=_auth(token)).json()
    assert me["job_title"] == "AI Engineer"
    assert me["bio"] == "Builds agents."


# --- workspace settings ------------------------------------------------------

def test_workspace_autocreates_with_defaults(client):
    token = _signup(client)
    ws = client.get("/workspace", headers=_auth(token)).json()
    assert ws["name"] == "My Workspace"
    assert ws["timezone"]
    assert ws["language"]


def test_workspace_update(client):
    token = _signup(client)
    resp = client.put(
        "/workspace",
        json={"name": "Acme Corp", "description": "We build things", "timezone": "(GMT+00:00) UTC"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    ws = resp.json()
    assert ws["name"] == "Acme Corp"
    assert ws["description"] == "We build things"
    assert ws["timezone"] == "(GMT+00:00) UTC"


# --- members -----------------------------------------------------------------

def test_members_owner_seeded(client):
    token = _signup(client)
    members = client.get("/workspace/members", headers=_auth(token)).json()["members"]
    assert len(members) == 1
    assert members[0]["role"] == "Owner"
    assert members[0]["email"] == "jane@example.com"


def test_add_and_remove_member(client):
    token = _signup(client)
    add = client.post(
        "/workspace/members",
        json={"name": "Bob", "email": "bob@example.com", "role": "Admin"},
        headers=_auth(token),
    )
    assert add.status_code == 201
    member_id = add.json()["id"]
    assert add.json()["role"] == "Admin"

    members = client.get("/workspace/members", headers=_auth(token)).json()["members"]
    assert len(members) == 2

    rm = client.delete(f"/workspace/members/{member_id}", headers=_auth(token))
    assert rm.status_code == 200
    members = client.get("/workspace/members", headers=_auth(token)).json()["members"]
    assert len(members) == 1


def test_cannot_add_duplicate_member(client):
    token = _signup(client)
    client.post(
        "/workspace/members",
        json={"name": "Bob", "email": "bob@example.com", "role": "Member"},
        headers=_auth(token),
    )
    dup = client.post(
        "/workspace/members",
        json={"name": "Bob 2", "email": "bob@example.com", "role": "Member"},
        headers=_auth(token),
    )
    assert dup.status_code == 409


def test_cannot_remove_owner(client):
    token = _signup(client)
    members = client.get("/workspace/members", headers=_auth(token)).json()["members"]
    owner_id = members[0]["id"]
    resp = client.delete(f"/workspace/members/{owner_id}", headers=_auth(token))
    assert resp.status_code == 409


def test_update_member_role(client):
    token = _signup(client)
    member_id = client.post(
        "/workspace/members",
        json={"name": "Bob", "email": "bob@example.com", "role": "Member"},
        headers=_auth(token),
    ).json()["id"]
    resp = client.put(
        f"/workspace/members/{member_id}", json={"role": "Admin"}, headers=_auth(token)
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "Admin"


def test_workspace_requires_auth(client):
    assert client.get("/workspace").status_code == 401
    assert client.get("/workspace/members").status_code == 401
