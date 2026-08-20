"""Fail the test run if any test opens a real outbound network connection.

The suite must consume zero free-tier quota. Phase 6 introduced grounding hooks
that call Serper, Overpass and ChromaDB, so this guard exists to catch a test
that forgets to disable them - which would otherwise spend real credits silently
and make results network-dependent.

respx intercepts httpx at the transport layer, so mocked HTTP never reaches here.
"""

from __future__ import annotations

import socket

import pytest

_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


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
