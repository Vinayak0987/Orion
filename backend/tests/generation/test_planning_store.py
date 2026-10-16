"""Tests for the planning_reports store (design.md §5, phases.md Phase 1).

Uses a temporary database per test via the same pattern as tests/test_db.py,
so no developer data is touched. Fully offline - no LLM, no agents.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.generation.db import sqlite
from app.generation.planning import store


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch) -> None:
    """Point the module at a throwaway database file."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file)
    )
    sqlite.init_db()
    store.init_planning()


def _report(**overrides) -> dict:
    """A minimal ready report, with test-friendly overrides."""
    base = {
        "raw_prompt": "Ice cream shop in Andheri, Rs 15L budget",
        "intent": {"business_type": "ice_cream_shop"},
        "intent_source": "llm",
        "status": "ready",
        "blockers": [],
        "warnings": ["SERPER_API_KEY missing - market research (F39) will fall back to LLM-only"],
        "routing": {"active_departments": ["strategy"], "skipped_departments": []},
        "agents": [
            {"agent_id": "market_research", "department": "strategy", "max_tokens": 900}
        ],
        "active_departments": ["strategy"],
        "skipped_departments": [],
        "estimated_agent_calls": 1,
        "estimated_max_completion_tokens": 1500,
    }
    base.update(overrides)
    return base


# =============================================================================
# create / get / list roundtrip
# =============================================================================


def test_create_and_get_roundtrip() -> None:
    report = store.create_report(**_report())

    fetched = store.get_report(report["id"])
    assert fetched is not None
    assert fetched["id"] == report["id"]
    assert fetched["raw_prompt"] == "Ice cream shop in Andheri, Rs 15L budget"
    assert fetched["status"] == "ready"
    assert fetched["intent"] == {"business_type": "ice_cream_shop"}
    assert fetched["intent_source"] == "llm"
    assert fetched["agents"] == [
        {"agent_id": "market_research", "department": "strategy", "max_tokens": 900}
    ]
    assert fetched["estimated_agent_calls"] == 1
    assert fetched["estimated_max_completion_tokens"] == 1500
    assert fetched["confirmed_at"] is None
    assert fetched["executed_at"] is None
    assert fetched["executed_session_id"] is None


def test_id_shape_matches_session_ids() -> None:
    report = store.create_report(**_report())
    assert len(report["id"]) == 12
    int(report["id"], 16)  # uuid4().hex[:12] - twelve hex characters


def test_create_rejects_pending_status() -> None:
    """No `pending` row is ever stored (design.md §5)."""
    for illegal in ("pending", "confirmed", "executed", "expired"):
        with pytest.raises(ValueError, match="half-built"):
            store.create_report(**_report(status=illegal))


def test_create_rejects_unknown_field() -> None:
    with pytest.raises(ValueError, match="Unknown planning report field"):
        store.create_report(**_report(nonsense_field="boom"))


def test_create_requires_prompt_and_source() -> None:
    with pytest.raises(ValueError, match="raw_prompt"):
        store.create_report(raw_prompt="", intent_source="llm")
    with pytest.raises(ValueError, match="intent_source"):
        store.create_report(raw_prompt="a real prompt", intent_source="")


def test_get_missing_returns_none() -> None:
    assert store.get_report("does-not-exist") is None


def test_list_newest_first_with_summaries_only() -> None:
    # Use recent, relative timestamps so the newest row is within the 24 h TTL
    # regardless of when the suite runs (absolute dates here silently 'expire'
    # once wall-clock passes the TTL window).
    now = datetime.now(UTC)
    for index in range(3):
        created = (now - timedelta(minutes=(3 - index))).isoformat()
        store.create_report(
            **_report(
                id=f"r{index}",
                created_at=created,
                agents=[{"agent_id": f"a{index}", "max_tokens": 100}],
            )
        )

    rows = store.list_reports(limit=10)
    assert [r["id"] for r in rows] == ["r2", "r1", "r0"]
    assert rows[0]["agent_count"] == 1
    assert rows[0]["status"] == "ready"
    # Summary fields only - never the full payload.
    assert "intent" not in rows[0]
    assert "agents" not in rows[0]
    assert "blockers" not in rows[0]


def test_list_respects_limit_and_offset() -> None:
    now = datetime.now(UTC)
    for index in range(3):
        created = (now - timedelta(minutes=(3 - index))).isoformat()
        store.create_report(**_report(id=f"r{index}", created_at=created))

    assert [r["id"] for r in store.list_reports(limit=2)] == ["r2", "r1"]
    assert [r["id"] for r in store.list_reports(limit=2, offset=2)] == ["r0"]


def test_init_planning_is_idempotent() -> None:
    store.init_planning()  # second call on the same temp database
    store.init_planning()
    report = store.create_report(**_report())
    assert store.get_report(report["id"]) is not None


# =============================================================================
# decode defaults
# =============================================================================


def test_decode_defaults_for_missing_payloads() -> None:
    report = store.create_report(
        raw_prompt="Just a prompt with no payload",
        intent_source="heuristic",
        status="blocked",
    )

    fetched = store.get_report(report["id"])
    assert fetched is not None
    assert fetched["intent"] is None
    assert fetched["routing"] is None
    assert fetched["agents"] == []
    assert fetched["blockers"] == []
    assert fetched["warnings"] == []
    assert fetched["active_departments"] == []
    assert fetched["skipped_departments"] == []
    assert fetched["estimated_agent_calls"] == 0
    assert fetched["estimated_max_completion_tokens"] == 0


# =============================================================================
# confirm - legal-transition guard
# =============================================================================


def test_confirm_ready_report() -> None:
    report = store.create_report(**_report())
    confirmed = store.confirm_report(report["id"], by="vinayak")

    assert confirmed is not None
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_by"] == "vinayak"
    assert confirmed["confirmed_at"] is not None


def test_confirm_defaults_by_operator_when_blank() -> None:
    report = store.create_report(**_report())
    confirmed = store.confirm_report(report["id"], by="")
    assert confirmed["confirmed_by"] == "operator"


def test_confirm_rejects_every_non_ready_status() -> None:
    blocked = store.create_report(**_report(status="blocked"))
    with pytest.raises(store.IllegalTransition, match="cannot be confirmed"):
        store.confirm_report(blocked["id"])

    ready = store.create_report(**_report())
    confirmed = store.confirm_report(ready["id"])
    with pytest.raises(store.IllegalTransition, match="cannot be confirmed"):
        store.confirm_report(confirmed["id"])

    ready_two = store.create_report(**_report())
    confirmed_two = store.confirm_report(ready_two["id"])
    executed = store.mark_executed(confirmed_two["id"], "sess123")
    with pytest.raises(store.IllegalTransition, match="cannot be confirmed"):
        store.confirm_report(executed["id"])


def test_confirm_expired_by_ttl_is_rejected() -> None:
    stale = store.create_report(
        **_report(created_at=(datetime.now(UTC) - timedelta(hours=25)).isoformat())
    )
    with pytest.raises(store.IllegalTransition, match="expired"):
        store.confirm_report(stale["id"])


def test_confirm_unknown_returns_none() -> None:
    assert store.confirm_report("does-not-exist") is None


# =============================================================================
# mark_executed
# =============================================================================


def test_mark_executed_sets_session_and_timestamp() -> None:
    ready = store.create_report(**_report())
    confirmed = store.confirm_report(ready["id"])
    executed = store.mark_executed(confirmed["id"], "sess456")

    assert executed["status"] == "executed"
    assert executed["executed_session_id"] == "sess456"
    assert executed["executed_at"] is not None


def test_mark_executed_rejects_non_confirmed() -> None:
    ready = store.create_report(**_report())
    with pytest.raises(store.IllegalTransition, match="cannot be executed"):
        store.mark_executed(ready["id"], "sess")

    blocked = store.create_report(**_report(status="blocked"))
    with pytest.raises(store.IllegalTransition, match="cannot be executed"):
        store.mark_executed(blocked["id"], "sess")


def test_mark_executed_unknown_returns_none() -> None:
    assert store.mark_executed("does-not-exist", "sess") is None


# =============================================================================
# TTL boundary
# =============================================================================


def test_ttl_boundary_exact_and_just_under() -> None:
    exactly_24h = datetime.now(UTC) - timedelta(hours=24)
    under_24h = datetime.now(UTC) - timedelta(hours=23, minutes=59)

    assert store.is_expired(exactly_24h.isoformat()) is True
    assert store.is_expired(under_24h.isoformat()) is False


def test_expired_report_reads_as_expired_but_row_stays_ready() -> None:
    stale = store.create_report(
        **_report(created_at=(datetime.now(UTC) - timedelta(hours=25)).isoformat())
    )
    fresh = store.create_report(**_report())

    # Derived at read time: the reader sees 'expired'...
    assert store.get_report(stale["id"])["status"] == "expired"
    listed = {row["id"]: row["status"] for row in store.list_reports(limit=10)}
    assert listed[stale["id"]] == "expired"
    assert listed[fresh["id"]] == "ready"
    # ...while the stored row itself still says 'ready' (no reaper ever mutates it).
    with sqlite.connection() as conn:
        raw = conn.execute(
            "SELECT status FROM planning_reports WHERE id = ?", (stale["id"],)
        ).fetchone()
    assert raw["status"] == "ready"
    assert store.get_report(fresh["id"])["status"] == "ready"
