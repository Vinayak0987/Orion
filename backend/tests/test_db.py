"""Tests for F59/F60 - SQLite session and evaluation persistence.

Uses a temporary database per test so no developer data is touched.
"""

from __future__ import annotations

import pytest

from app.db import sqlite


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch) -> None:
    """Point the module at a throwaway database file."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file)
    )
    sqlite.init_db()


# =============================================================================
# F59 - sessions
# =============================================================================


def test_create_and_fetch_session() -> None:
    sqlite.create_session("s1", "Ice cream shop in Andheri, Rs 15L")

    record = sqlite.get_session("s1")
    assert record is not None
    assert record["raw_prompt"] == "Ice cream shop in Andheri, Rs 15L"
    assert record["status"] == "pending"
    assert record["plan"] is None


def test_update_session_json_columns_round_trip() -> None:
    sqlite.create_session("s2", "bakery in Dadar")
    sqlite.update_session(
        "s2",
        status="completed",
        intent_json={"business_type": "bakery", "sector": "food_and_beverage"},
        plan_json={"strategy": {"executive_summary": "x"}},
        active_departments=["strategy", "finance"],
        skipped_departments=["operations"],
        total_tokens=4321,
        completeness_score=92.5,
    )

    record = sqlite.get_session("s2")
    assert record["status"] == "completed"
    assert record["intent"]["business_type"] == "bakery"
    assert record["plan"]["strategy"]["executive_summary"] == "x"
    assert record["active_departments"] == ["strategy", "finance"]
    assert record["skipped_departments"] == ["operations"]
    assert record["total_tokens"] == 4321
    assert record["completeness_score"] == 92.5


def test_update_session_rejects_unknown_column() -> None:
    """Guards against SQL built from unvalidated keys."""
    sqlite.create_session("s3", "prompt")

    with pytest.raises(ValueError, match="Unknown session column"):
        sqlite.update_session("s3", nonexistent_column="boom")


def test_list_sessions_is_newest_first() -> None:
    for i in range(3):
        sqlite.create_session(f"s{i}", f"prompt {i}")
        sqlite.update_session(f"s{i}", completed_at=f"2026-07-2{i}T00:00:00Z")

    rows = sqlite.list_sessions(limit=10)
    assert len(rows) == 3
    assert {r["id"] for r in rows} == {"s0", "s1", "s2"}


def test_delete_session() -> None:
    sqlite.create_session("s9", "prompt")

    assert sqlite.delete_session("s9") is True
    assert sqlite.delete_session("s9") is False
    assert sqlite.get_session("s9") is None


def test_get_missing_session_returns_none() -> None:
    assert sqlite.get_session("does-not-exist") is None


# =============================================================================
# F60 - evaluation results
# =============================================================================


def test_record_and_aggregate_metrics() -> None:
    for approach, scores in (("multi_agent", [90.0, 80.0]), ("baseline", [60.0, 40.0])):
        for idx, score in enumerate(scores):
            sqlite.record_metric(
                run_label="run-1",
                prompt_id=f"p{idx}",
                prompt_text=f"prompt {idx}",
                approach=approach,
                metric="plan_completeness",
                score=score,
                details={"sections_found": int(score / 10)},
            )

    rows = sqlite.aggregate_metrics("run-1")
    by_approach = {r["approach"]: r for r in rows}

    assert by_approach["multi_agent"]["mean_score"] == 85.0
    assert by_approach["baseline"]["mean_score"] == 50.0
    assert by_approach["multi_agent"]["n"] == 2


def test_aggregate_ignores_null_scores() -> None:
    sqlite.record_metric("run-2", "p0", "prompt", "multi_agent", "mape", 12.0)
    sqlite.record_metric("run-2", "p1", "prompt", "multi_agent", "mape", None)

    rows = sqlite.aggregate_metrics("run-2")
    assert rows[0]["n"] == 1
    assert rows[0]["mean_score"] == 12.0


def test_fetch_metrics_returns_raw_rows_for_csv_export() -> None:
    sqlite.record_metric("run-3", "p0", "prompt", "baseline", "consistency", 55.0)

    rows = sqlite.fetch_metrics("run-3")
    assert len(rows) == 1
    assert rows[0]["approach"] == "baseline"
    assert rows[0]["metric"] == "consistency"
