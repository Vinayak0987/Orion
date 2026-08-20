"""Tests for the operating-layer API routes (/operating/*).

Offline, no LLM, no network. Seeds the ledger with a few entries and exercises
every endpoint.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.db import sqlite
from app.main import app
from app.operating import init_all
from app.operating import governance as G, ledger, memory as M
from app.operating.constitution import ActionKind, ProposedAction
from app.operating.ledger import EntryKind, LedgerEntry
from app.operating.memory import Memory, MemoryType

COMPANY = "test-company"


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    db_file = tmp_path / "op-api.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file))
    sqlite.init_db()
    init_all()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded(client):
    """Seed the company with a few ledger entries and a pending decision."""
    for kind, amt in ((EntryKind.CASH_IN, 10_00_000_00),
                      (EntryKind.REVENUE, 5_00_000_00),
                      (EntryKind.COGS, 2_00_000_00),
                      (EntryKind.MARKETING_SPEND, 50_000_00),
                      (EntryKind.CUSTOMER_ACQUIRED, 0)):
        if kind == EntryKind.CUSTOMER_ACQUIRED:
            ledger.append(LedgerEntry(
                company_id=COMPANY, kind=kind, department="marketing",
                actor="test", quantity=20,
                occurred_at=datetime(2026, 1, 1, tzinfo=UTC).isoformat()))
        else:
            ledger.append(LedgerEntry(
                company_id=COMPANY, kind=kind, department="finance",
                actor="test", amount_minor=amt,
                occurred_at=datetime(2026, 1, 1, tzinfo=UTC).isoformat()))
    # Create a pending decision
    action = ProposedAction(
        kind=ActionKind.SPEND, department="marketing", actor="planner",
        company_id=COMPANY, amount_minor=8_000_00,
        description="large campaign")
    from app.operating.governance import Policy
    G.submit("test-decision-1", action, policy=Policy(review_above_minor=1_000_00))
    # Write a memory
    M.write(Memory(company_id=COMPANY, department="marketing",
                   memory_type=MemoryType.EPISODIC,
                   content="ran a campaign last week", confidence=0.6))
    return COMPANY


# ------------------------------------------------------------------ anchors ----


def test_get_anchors(client, seeded):
    r = client.get("/operating/anchors", params={"company_id": seeded})
    assert r.status_code == 200
    body = r.json()
    assert body["company_id"] == seeded
    assert "revenue" in body["anchors"]
    assert body["anchors"]["revenue"]["value"] is not None
    assert body["anchors"]["revenue"]["unit"] == "INR"


def test_get_anchors_empty_company(client):
    r = client.get("/operating/anchors", params={"company_id": "no-such"})
    assert r.status_code == 200
    body = r.json()
    assert body["entry_count"] == 0


def test_get_anchor_history(client, seeded):
    r = client.get("/operating/anchors/history",
                   params={"company_id": seeded, "points": 5})
    assert r.status_code == 200
    body = r.json()
    assert "series" in body
    assert body["points"] >= 1


# ------------------------------------------------------------------ findings ---


def test_get_findings_empty(client, seeded):
    r = client.get("/operating/findings", params={"company_id": seeded})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------- decisions ----


def test_get_decisions(client, seeded):
    r = client.get("/operating/decisions", params={"company_id": seeded})
    assert r.status_code == 200
    decisions = r.json()
    assert len(decisions) >= 1


def test_get_decisions_by_state(client, seeded):
    r = client.get("/operating/decisions",
                   params={"company_id": seeded, "state": "pending_review"})
    assert r.status_code == 200
    pending = r.json()
    assert len(pending) >= 1
    assert all(d["state"] == "pending_review" for d in pending)


def test_approve_decision(client, seeded):
    r = client.post("/operating/decisions/test-decision-1/approve",
                    json={"by": "vinayak"})
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "approved"
    assert body["decided_by"] == "vinayak"


def test_approve_without_name_is_422(client, seeded):
    r = client.post("/operating/decisions/test-decision-1/approve",
                    json={"by": ""})
    assert r.status_code == 422


def test_reject_decision(client, seeded):
    r = client.post("/operating/decisions/test-decision-1/reject",
                    json={"by": "vinayak", "reason": "too expensive"})
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "rejected"


def test_return_decision(client, seeded):
    r = client.post("/operating/decisions/test-decision-1/return",
                    json={"by": "vinayak", "reason": "needs revision"})
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "returned"


def test_approve_nonexistent_decision_is_404(client, seeded):
    r = client.post("/operating/decisions/no-such/approve",
                    json={"by": "vinayak"})
    assert r.status_code == 404


# -------------------------------------------------------------------- audit ----


def test_get_audit(client, seeded):
    r = client.get("/operating/audit/test-decision-1")
    assert r.status_code == 200
    trail = r.json()
    assert len(trail) >= 1
    assert trail[0]["decision_id"] == "test-decision-1"


def test_get_audit_nonexistent(client, seeded):
    r = client.get("/operating/audit/no-such")
    assert r.status_code == 404


# -------------------------------------------------------------- constitution ---


def test_get_constitution(client):
    r = client.get("/operating/constitution")
    assert r.status_code == 200
    rules = r.json()
    assert len(rules) == 7
    assert all("id" in rule for rule in rules)


# -------------------------------------------------------------------- loops ----


def test_get_loops(client):
    r = client.get("/operating/loops")
    assert r.status_code == 200
    body = r.json()
    assert "loops" in body
    assert body["valid"] is True
    assert "unterminated_cycles" in body


# ----------------------------------------------------------------- schedule ----


def test_get_schedule(client, seeded):
    r = client.get("/operating/schedule", params={"company_id": seeded})
    assert r.status_code == 200
    status = r.json()
    assert isinstance(status, list)
    assert len(status) > 0
    assert "loop_id" in status[0]


# -------------------------------------------------------------------- runs -----


def test_get_runs(client, seeded):
    r = client.get("/operating/runs", params={"company_id": seeded})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ------------------------------------------------------------------ ledger -----


def test_get_ledger(client, seeded):
    r = client.get("/operating/ledger", params={"company_id": seeded})
    assert r.status_code == 200
    entries = r.json()
    assert len(entries) >= 5
    # Newest first
    assert entries[0]["seq"] > entries[-1]["seq"]
    # Monetary entries have amount_minor
    revenue_entries = [e for e in entries if e["kind"] == "revenue"]
    assert revenue_entries[0]["amount_minor"] == 5_00_000_00


# ------------------------------------------------------------------ memory -----


def test_get_memory(client, seeded):
    r = client.get("/operating/memory",
                   params={"company_id": seeded, "department": "marketing"})
    assert r.status_code == 200
    body = r.json()
    assert body["department"] == "marketing"
    assert "counts" in body
    assert "entries" in body


# -------------------------------------------------------------- departments ----


def test_get_departments(client):
    r = client.get("/operating/departments")
    assert r.status_code == 200
    depts = r.json()
    assert len(depts) == 5
    names = {d["name"] for d in depts}
    assert names == {"strategy", "finance", "branding", "marketing", "operations"}
    assert all("proxy_metric" in d for d in depts)
    assert all("serves_anchor" in d for d in depts)


# -------------------------------------------------------------------- tick -----


def test_manual_tick(client, seeded):
    r = client.post("/operating/tick", json={"company_id": seeded})
    assert r.status_code == 200
    runs = r.json()
    assert isinstance(runs, list)
