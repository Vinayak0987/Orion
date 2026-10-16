"""Test-aware network timeout helper.

Production code uses generous timeouts (local Ollama inference can take minutes).
Under tests we never want to actually wait on a real socket: if a test forgets
to mock an HTTP call, a 300 s timeout turns a one-second failure into a
multi-minute hang, and across the suite that compounds into tens of minutes.

When the env flag ``ORION_TEST_FAST_TIMEOUTS=1`` is set (the test conftests set
it automatically), every client built through :func:`client_timeout` is capped
to a small ceiling so an unmocked call fails fast instead of hanging.
"""

from __future__ import annotations

import os

import httpx

# Ceiling applied to every timeout when fast-timeout mode is on.
_TEST_TIMEOUT_CEILING_S = 2.0


def fast_timeouts_enabled() -> bool:
    return os.getenv("ORION_TEST_FAST_TIMEOUTS", "") in {"1", "true", "True"}


def client_timeout(seconds: float) -> httpx.Timeout:
    """Return an ``httpx.Timeout`` capped to the test ceiling when enabled.

    Pass the normal production timeout; in fast mode it is clamped down.
    """
    if fast_timeouts_enabled():
        seconds = min(seconds, _TEST_TIMEOUT_CEILING_S)
    return httpx.Timeout(seconds)
