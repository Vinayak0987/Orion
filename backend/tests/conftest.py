"""Shared test fixtures. Every test runs against a fresh temp database."""

from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path

import pytest

# Fail fast instead of hanging on unmocked network calls (see app.net_timeouts).
os.environ.setdefault("ORION_TEST_FAST_TIMEOUTS", "1")


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, request):
    """Point the app at a throwaway SQLite file for the duration of each test.

    Generation-engine tests live under ``tests/generation/`` and manage their
    own namespaced database via that package's ``gen_temp_db`` fixture, so this
    v2 fixture steps aside for them.
    """
    if "tests/generation/" in request.node.nodeid or "tests\\generation\\" in request.node.nodeid:
        yield
        return

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    chroma_path = os.path.join(tmpdir, "chroma")

    monkeypatch.setenv("SQLITE_PATH", db_path)
    monkeypatch.setenv("CHROMA_PATH", chroma_path)

    # Reload config so the new env vars take effect.
    import app.config as config

    config.get_settings.cache_clear()
    config.settings = config.get_settings()

    # Re-point modules that captured `settings` at import time.
    import app.db.sqlite as sqlite_mod
    importlib.reload(sqlite_mod)

    from app.db.sqlite import init_db
    init_db()

    yield

    try:
        Path(db_path).unlink(missing_ok=True)
    except OSError:
        pass
