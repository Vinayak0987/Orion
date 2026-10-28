"""Knowledge documents + episodic memory tests (Plan 07).

All offline. Document ingest uses the keyword fallback (ChromaDB not installed).
The memory round-trip verifies: a stored fact is retrievable, and the executor
retrieve/extract hooks work with a scripted LLM.
"""

from __future__ import annotations

import asyncio
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "chroma"))
    monkeypatch.setattr(settings, "workspace_path", str(tmp_path / "ws"))
    from app.db import init_db

    init_db()
    yield


@pytest.fixture
def client():
    from fastapi import FastAPI

    from app.api.knowledge import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---- Documents --------------------------------------------------------------
def test_upload_persists_document_row_and_chunks(client):
    content = b"Orion is an AI company operating system. Agents run missions with tools and memory. " * 20
    r = client.post("/knowledge/documents",
                    files={"file": ("notes.txt", content, "text/plain")})
    assert r.status_code == 201
    doc_id = r.json()["document_id"]
    # New model: upload stores RAW only — no chunking happens at upload time.
    assert r.json()["chunks"] == 0
    assert r.json()["status"] == "uploaded"

    listing = client.get("/knowledge/documents").json()
    assert listing["count"] == 1
    assert listing["documents"][0]["status"] == "uploaded"
    assert listing["summary"]["documents"] == 1

    detail = client.get(f"/knowledge/documents/{doc_id}").json()
    assert detail["document"]["name"] == "notes.txt"
    # Chunks are produced lazily on first query, not at upload.
    assert detail["document"]["chunks_count"] == 0


def test_search_finds_uploaded_content(client):
    doc_id = client.post("/knowledge/documents",
                files={"file": ("facts.txt", b"The capital of France is Paris. Paris is in Europe.", "text/plain")}).json()["document_id"]
    # New model: upload is store-only. Indexing happens on demand — index it,
    # then global search can retrieve it.
    client.post(f"/knowledge/documents/{doc_id}/index")
    r = client.post("/knowledge/search", json={"query": "capital of France", "limit": 3})
    assert r.status_code == 200
    passages = r.json()["passages"]
    assert passages and any("Paris" in (p.get("text") or "") for p in passages)


def test_delete_document(client):
    doc_id = client.post("/knowledge/documents",
                         files={"file": ("x.txt", b"some removable text here", "text/plain")}).json()["document_id"]
    r = client.delete(f"/knowledge/documents/{doc_id}")
    assert r.status_code == 200 and r.json()["deleted"]
    assert client.get("/knowledge/documents").json()["count"] == 0


def test_empty_file_rejected(client):
    r = client.post("/knowledge/documents", files={"file": ("empty.txt", b"", "text/plain")})
    assert r.status_code == 422


def test_list_documents_tool():
    """Test the list_documents builtin tool returns document metadata."""
    from app.tools.builtins.knowledge import list_documents
    from app.tools.base import ToolContext
    from app.knowledge import documents as _docs

    # Create a test document
    doc_id = _docs.create_document(
        name="test.csv", type="csv", uploaded_by="default-user", size_bytes=100
    )
    _docs.mark_active(doc_id, chunks_count=5)

    # Call the tool
    ctx = ToolContext(user_id="default-user")
    result = list_documents({}, ctx)

    # Should not have error
    assert "error" not in result
    assert "documents" in result
    assert result["count"] == 1
    docs = result["documents"]
    assert len(docs) == 1
    assert docs[0]["document_id"] == doc_id
    assert docs[0]["name"] == "test.csv"
    assert docs[0]["type"] == "csv"
    assert docs[0]["status"] == "active"
    assert docs[0]["chunks_count"] == 5

    # Test type filter
    result_filtered = list_documents({"type": "csv"}, ctx)
    assert "error" not in result_filtered
    assert result_filtered["count"] == 1

    result_filtered = list_documents({"type": "pdf"}, ctx)
    assert "error" not in result_filtered
    assert result_filtered["count"] == 0


def test_eda_workflow_tools_available():
    """Test that the EDA workflow tools (list_documents, query_document, code_interpreter) are all available."""
    from app.tools.builtins.knowledge import list_documents, query_document
    from app.tools.base import ToolContext, load_all

    # Load all tools to verify they're registered
    registry = load_all()

    # Verify all three tools exist and are enabled
    assert "list_documents" in registry
    assert registry["list_documents"].enabled_by_default is True

    assert "query_document" in registry
    assert registry["query_document"].enabled_by_default is True

    assert "code_interpreter" in registry
    assert registry["code_interpreter"].enabled_by_default is True

    # Verify they can be called without error
    ctx = ToolContext(user_id="default-user")

    # list_documents should work even with no documents
    result = list_documents({}, ctx)
    assert "error" not in result
    assert "documents" in result

    # code_interpreter should work with simple code (async safe_run)
    import asyncio
    result = asyncio.run(registry["code_interpreter"].safe_run({"code": "print('test')"}, ctx))
    assert "error" not in result
    assert "test" in result.get("stdout", "")


# ---- Memory store -----------------------------------------------------------
def test_memory_write_and_search():
    from app.knowledge import memory

    eid = memory.write("agent-x", "LinkedIn ads outperformed Google ads 2.3x for enterprise.",
                       mission_id="m1", ttl_days=30)
    assert eid
    hits = memory.search("agent-x", "LinkedIn ads enterprise performance")
    assert hits and "LinkedIn" in hits[0]["content"]


def test_memory_endpoints(client):
    from app.knowledge import memory

    memory.write("agent-y", "Remember fact one.", ttl_days=30)
    r = client.get("/knowledge/memory?agent_id=agent-y")
    assert r.json()["count"] == 1

    r = client.put("/knowledge/memory/settings", json={"default_ttl_days": 45})
    assert r.json()["default_ttl_days"] == 45

    r = client.delete("/knowledge/memory/agent/agent-y?confirm=CLEAR")
    assert r.json()["entries_removed"] == 1


def test_clear_requires_confirm(client):
    r = client.delete("/knowledge/memory/agent/whatever")
    assert r.status_code == 422


# ---- Executor memory hooks (round-trip) ------------------------------------
@pytest.mark.asyncio
async def test_executor_extract_and_retrieve_roundtrip(monkeypatch):
    """A completed task extracts a fact; a later retrieval surfaces it."""
    from app.knowledge import memory
    from app.llm.providers import LLMResult

    agent = {"id": "agent-mem", "memory_enabled": 1, "memory_ttl_days": 30, "department_id": None}

    class ExtractLLM:
        async def call(self, messages, tier="fast", temperature=0.7):
            return LLMResult(text='["The Q4 target is 30% enterprise growth."]',
                             provider="fake", model="x")

    facts = await memory.extract_and_store_memory(agent, "m1", "We decided Q4 target is 30% growth.",
                                                  llm=ExtractLLM())
    assert facts and "30%" in facts[0]

    block = await memory.retrieve_memory(agent, "what is the Q4 growth target")
    assert "30%" in block


@pytest.mark.asyncio
async def test_memory_skipped_when_disabled():
    from app.knowledge import memory

    agent = {"id": "agent-off", "memory_enabled": 0, "memory_ttl_days": 30}
    facts = await memory.extract_and_store_memory(agent, "m1", "something", llm=None)
    assert facts == []
    assert await memory.retrieve_memory(agent, "anything") == ""
