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

# Fail fast instead of hanging on unmocked network calls (see app.net_timeouts).
os.environ.setdefault("ORION_TEST_FAST_TIMEOUTS", "1")

_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", ""}

# Ports that must NOT be reachable even on localhost: a test hitting a real
# local service (e.g. Ollama on 11434) would otherwise wait out the full client
# timeout. Blocking turns that into an instant, mockable failure. A test that
# genuinely needs one can mark itself with @pytest.mark.allow_network.
_BLOCKED_LOCAL_PORTS = {11434}  # Ollama


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

    def _port_of(address):
        return address[1] if isinstance(address, tuple) and len(address) > 1 else None

    def guard(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) and address else ""
        port = _port_of(address)
        if str(host) not in _ALLOWED_HOSTS:
            raise NetworkAccessAttempted(
                f"Test attempted an outbound connection to {host}. "
                f"Mock it with respx or disable the feature flag - the suite must "
                f"consume no API quota."
            )
        if port in _BLOCKED_LOCAL_PORTS:
            raise NetworkAccessAttempted(
                f"Test attempted to reach a real local service on port {port} "
                f"(e.g. Ollama). Mock the provider or mark the test "
                f"@pytest.mark.allow_network."
            )
        return real_connect(self, address, *args, **kwargs)

    def guard_ex(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) and address else ""
        port = _port_of(address)
        if str(host) not in _ALLOWED_HOSTS:
            raise NetworkAccessAttempted(f"Test attempted an outbound connection to {host}")
        if port in _BLOCKED_LOCAL_PORTS:
            raise NetworkAccessAttempted(
                f"Test attempted to reach a real local service on port {port}"
            )
        return real_connect_ex(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_ex)
