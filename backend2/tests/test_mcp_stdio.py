"""stdio (local command) MCP transport tests.

Spawns the mock stdio server (tests/mock_stdio_server.py) as a real subprocess
and verifies discovery + tool calls over stdin/stdout, the safety gate, and
dispatch routing. Uses asyncio.run() per test (fresh loop) to stay robust on
Windows where pytest-asyncio's shared loop + subprocesses interact poorly.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

import app.config as cfg

MOCK = str(Path(__file__).parent / "mock_stdio_server.py")


def _set(v):
    cfg.settings.mcp_stdio_enabled = v


def test_stdio_disabled_by_default():
    from app.tools import mcp_stdio

    _set(False)
    with pytest.raises(mcp_stdio.MCPError):
        asyncio.run(mcp_stdio.discover_stdio(sys.executable, [MOCK]))


def test_stdio_discover_when_enabled():
    from app.tools import mcp_stdio

    _set(True)
    tools = asyncio.run(mcp_stdio.discover_stdio(sys.executable, [MOCK]))
    assert {t["name"] for t in tools} == {"echo", "add"}


def test_stdio_call_tool():
    from app.tools import mcp_stdio

    _set(True)
    r = asyncio.run(mcp_stdio.call_stdio(sys.executable, "add", {"a": 2, "b": 5}, args=[MOCK]))
    assert r["text"] == "7"
    r2 = asyncio.run(mcp_stdio.call_stdio(sys.executable, "echo", {"text": "hi orion"}, args=[MOCK]))
    assert r2["text"] == "hi orion"


def test_stdio_bad_command_degrades():
    from app.tools import mcp_stdio

    _set(True)
    with pytest.raises(mcp_stdio.MCPError):
        asyncio.run(mcp_stdio.discover_stdio("this_command_does_not_exist_xyz", []))


def test_dispatch_routes_stdio_tool():
    """A registered stdio tool dispatches through the subprocess transport.
    (conftest's temp_db fixture already points us at a fresh DB.)"""
    _set(True)
    from app.db import init_db

    init_db()
    from app.tools import registry, store

    store.upsert_tool(
        name="mcp_add", display_name="add", description="add two numbers",
        type="mcp", category="mcp", input_schema={},
        config={"server_url": "stdio://mock", "transport": "stdio",
                "command": sys.executable, "args": [MOCK], "remote_name": "add"},
    )
    out = asyncio.run(registry.dispatch("mcp_add", {"a": 10, "b": 3}))
    assert out.get("text") == "13"
