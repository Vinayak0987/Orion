"""Chat layer tests — conversations, messages, global context. Fully offline."""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    # Isolated SQLite file per test module run.
    db = os.path.join(tempfile.mkdtemp(), "chat.db")
    monkeypatch.setenv("SQLITE_PATH", db)

    # Reload settings + db so they pick up the temp path.
    import importlib

    from app import config as config_mod
    importlib.reload(config_mod)
    from app.db import sqlite as sqlite_mod
    importlib.reload(sqlite_mod)
    from app.stores.chat import store as store_mod
    importlib.reload(store_mod)

    sqlite_mod.init_db()
    yield store_mod


def test_conversation_crud(client):
    store = client
    conv = store.create_conversation("default-user", "First chat")
    assert conv["title"] == "First chat"

    convs = store.list_conversations("default-user")
    assert len(convs) == 1
    assert convs[0]["message_count"] == 0

    assert store.rename_conversation(conv["id"], "Renamed") is True
    assert store.get_conversation(conv["id"])["title"] == "Renamed"

    assert store.delete_conversation(conv["id"]) is True
    assert store.get_conversation(conv["id"]) is None


def test_messages_roundtrip(client):
    store = client
    conv = store.create_conversation("default-user")
    u = store.add_message(conv["id"], "user", "Analyze my competitors")
    a = store.add_message(conv["id"], "assistant", "", mission_id="m123", status="running")

    msgs = store.list_messages(conv["id"])
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "Analyze my competitors"

    store.update_message(a["id"], content="Done.", status="done",
                         outputs=[{"task": "T1", "result": {"data": "x"}}])
    msgs = store.list_messages(conv["id"])
    assert msgs[1]["status"] == "done"
    assert msgs[1]["outputs"][0]["task"] == "T1"

    # listing updates ordering by updated_at — conversation should have 2 messages
    convs = store.list_conversations("default-user")
    assert convs[0]["message_count"] == 2


def test_global_context(client):
    store = client
    store.set_context("default-user", "company", "Acme Corp")
    store.set_context("default-user", "tone", "concise")
    store.set_context("default-user", "company", "Acme Inc")  # upsert

    facts = store.list_context("default-user")
    keys = {f["key"]: f["value"] for f in facts}
    assert keys["company"] == "Acme Inc"  # upserted, not duplicated
    assert keys["tone"] == "concise"
    assert len(facts) == 2

    block = store.context_block("default-user")
    assert "company: Acme Inc" in block
    assert "tone: concise" in block

    assert store.delete_context("default-user", "tone") is True
    assert len(store.list_context("default-user")) == 1


def test_chat_api_routes(client):
    # Build a TestClient against the app (uses the same temp DB via env).
    from app.main import app

    with TestClient(app) as c:
        r = c.post("/conversations", json={"title": "API chat"})
        assert r.status_code == 201
        cid = r.json()["id"]

        r = c.post(f"/conversations/{cid}/messages", json={"role": "user", "content": "hi"})
        assert r.status_code == 201

        r = c.get(f"/conversations/{cid}")
        assert r.status_code == 200
        assert len(r.json()["messages"]) == 1

        r = c.put("/context", json={"key": "company", "value": "Acme"})
        assert r.status_code == 200
        r = c.get("/context")
        assert any(f["key"] == "company" for f in r.json()["context"])

        r = c.delete(f"/conversations/{cid}")
        assert r.status_code == 200
