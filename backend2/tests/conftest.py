"""Shared test fixtures. Every test runs against a fresh temp database."""

from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    """Point the app at a throwaway MongoDB (mongomock) for the duration of each test."""
    # Use mongomock for offline testing
    import mongomock
    import app.auth.store as auth_store
    import app.config as config

    # Create a fresh mongomock client for each test
    mock_client = mongomock.MongoClient()
    auth_store.configure(mock_client, "test_orion")

    # Set env var to indicate MongoDB is available
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017/test")
    monkeypatch.setenv("MONGO_DB_NAME", "test_orion")

    # Reload config so the new env vars take effect.
    config.get_settings.cache_clear()
    config.settings = config.get_settings()

    yield

    # Cleanup - clear all collections in mongomock
    db = mock_client["test_orion"]
    for collection_name in db.list_collection_names():
        db.drop_collection(collection_name)
    auth_store.reset_for_tests()
