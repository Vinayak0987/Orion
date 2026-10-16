"""Fail the test run if any test opens a real outbound network connection.

The suite must consume zero free-tier quota. Phase 6 introduced grounding hooks
that call Serper, Overpass and ChromaDB, so this guard exists to catch a test
that forgets to disable them - which would otherwise spend real credits silently
and make results network-dependent.

respx intercepts httpx at the transport layer, so mocked HTTP never reaches here.
"""

from __future__ import annotations

import importlib
import os
import socket
import tempfile
from pathlib import Path

import pytest

_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


@pytest.fixture(autouse=True)
def gen_temp_db(monkeypatch):
    """Point the generation engine at a throwaway SQLite file per test.

    Mirrors the v1 suite's fixture but targets the namespaced
    ``app.generation.config`` / ``app.generation.db.sqlite`` modules and also
    creates the operating + planning tables the v1 engine expects.
    """
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    chroma_path = os.path.join(tmpdir, "chroma")

    monkeypatch.setenv("SQLITE_PATH", db_path)
    monkeypatch.setenv("CHROMA_PATH", chroma_path)

    import app.generation.config as config

    config.get_settings.cache_clear()
    config.settings = config.get_settings()

    import app.generation.db.sqlite as sqlite_mod
    importlib.reload(sqlite_mod)

    sqlite_mod.init_db()
    from app.generation.operating import init_all
    from app.generation.planning import init_planning

    init_all()
    init_planning()

    yield

    try:
        Path(db_path).unlink(missing_ok=True)
    except OSError:
        pass


class NetworkAccessAttempted(RuntimeError):
    """A test tried to open a real outbound socket."""


@pytest.fixture(autouse=True)
def block_outbound_network(monkeypatch, request):
    """Block non-local socket connections for the whole suite."""
    if request.node.get_closest_marker("allow_network"):
        return

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guard(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) and address else ""
        if str(host) not in _ALLOWED_HOSTS:
            raise NetworkAccessAttempted(
                f"Test attempted an outbound connection to {host}. "
                f"Mock it with respx or disable the feature flag - the suite must "
                f"consume no API quota."
            )
        return real_connect(self, address, *args, **kwargs)

    def guard_ex(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) and address else ""
        if str(host) not in _ALLOWED_HOSTS:
            raise NetworkAccessAttempted(f"Test attempted an outbound connection to {host}")
        return real_connect_ex(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_ex)
