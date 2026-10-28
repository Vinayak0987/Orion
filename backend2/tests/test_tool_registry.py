"""Tests for the DB-backed tool registry + store (seed, dispatch, enable/disable)."""

from __future__ import annotations

import pytest

from app.tools import registry, store
from app.tools.seed import seed_builtin_tools


@pytest.fixture(autouse=True)
def _seeded(tmp_path, monkeypatch):
    # Each test gets an isolated sqlite DB + workspace.
    from app.config import settings

    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "workspace_path", str(tmp_path / "ws"))
    from app.db import init_db

    init_db()
    seed_builtin_tools()
    yield


def test_seed_populates_table():
    tools = store.list_tools()
    assert len(tools) >= 100
    names = {t["name"] for t in tools}
    assert {"web_search", "document_rag", "calculator", "file_reader", "code_interpreter"} <= names


def test_last_used_fields_present():
    tools = store.list_tools()
    assert all("last_used" in t and "usage_count" in t for t in tools)


@pytest.mark.asyncio
async def test_dispatch_known_builtin():
    r = await registry.dispatch("calculator", {"expression": "6*7"})
    assert r["result"] == 42


@pytest.mark.asyncio
async def test_dispatch_unknown_tool():
    r = await registry.dispatch("does_not_exist", {})
    assert "error" in r


@pytest.mark.asyncio
async def test_disabled_tool_is_blocked():
    assert store.set_enabled("calculator", False)
    r = await registry.dispatch("calculator", {"expression": "1+1"})
    assert "error" in r and r.get("degraded")
    store.set_enabled("calculator", True)
    r2 = await registry.dispatch("calculator", {"expression": "1+1"})
    assert r2["result"] == 2


def test_list_filters():
    web = store.list_tools(category="web")
    assert web and all(t["category"] == "web" for t in web)
