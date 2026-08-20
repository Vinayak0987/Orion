"""Tests for departmental memory.

The isolation invariant is the one that matters: a Marketing query must never
surface Legal's or Strategy's entries. The scoped-versus-shared comparison is
also tested, because that difference is what the research proposal claims.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.operating import memory as M
from app.operating.memory import (
    ALL_TYPES,
    CONSOLIDATION_THRESHOLD,
    Memory,
    MemoryScopeViolation,
    MemoryType,
    tokenise,
)

NOW = datetime(2026, 7, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def memory_db(tmp_path, monkeypatch):
    from app.db import sqlite as sqlite_module

    db_file = tmp_path / "memory-test.db"
    monkeypatch.setattr(
        sqlite_module.settings.__class__, "sqlite_file",
        property(lambda _self: db_file),
    )
    M.init_memory()
    yield


def remember(department: str, content: str,
             memory_type: MemoryType = MemoryType.EPISODIC,
             company: str = "c1", created_at: str | None = None,
             confidence: float = 0.5) -> str:
    return M.write(Memory(
        company_id=company, department=department, memory_type=memory_type,
        content=content, created_at=created_at or NOW.isoformat(),
        confidence=confidence,
    ))


# ===================== THE ISOLATION INVARIANT ================================


def test_a_department_query_never_returns_another_departments_memory():
    remember("legal", "trademark objection filed against the brand name")
    remember("strategy", "competitor analysis shows brand name collision risk")
    remember("marketing", "brand name performed well in the diwali campaign")

    hits = M.retrieve("c1", "marketing", "brand name", now=NOW)
    assert hits
    assert {h["department"] for h in hits} == {"marketing"}


def test_isolation_holds_even_when_another_department_is_a_better_match():
    """The better lexical match must still not cross the boundary."""
    remember("legal", "brand name trademark objection brand name brand name")
    remember("marketing", "diwali campaign results")

    hits = M.retrieve("c1", "marketing", "brand name trademark", now=NOW)
    assert all(h["department"] == "marketing" for h in hits)


def test_retrieve_requires_a_department():
    remember("marketing", "campaign results")
    with pytest.raises(MemoryScopeViolation):
        M.retrieve("c1", "", "campaign", now=NOW)
    with pytest.raises(MemoryScopeViolation):
        M.retrieve("c1", "   ", "campaign", now=NOW)


def test_memory_is_company_scoped_as_well_as_department_scoped():
    remember("marketing", "diwali campaign results", company="c1")
    remember("marketing", "diwali campaign results", company="c2")
    hits = M.retrieve("c1", "marketing", "diwali", now=NOW)
    assert len(hits) == 1
    assert hits[0]["company_id"] == "c1"


def test_a_memory_must_be_scoped_on_construction():
    with pytest.raises(ValueError):
        Memory(company_id="c1", department="", memory_type=MemoryType.EPISODIC,
               content="x")
    with pytest.raises(ValueError):
        Memory(company_id="", department="marketing",
               memory_type=MemoryType.EPISODIC, content="x")


# ===================== SCOPED VERSUS SHARED ==================================


def test_shared_retrieval_returns_the_noise_that_scoping_excludes():
    """The control arm: this is what a single shared context would surface."""
    remember("legal", "brand name trademark objection")
    remember("strategy", "brand name collision risk in the competitor set")
    remember("finance", "brand name licensing cost estimate")
    remember("marketing", "brand name tested well with the target persona")

    scoped = M.retrieve("c1", "marketing", "brand name", now=NOW)
    shared = M.retrieve_shared("c1", "brand name", now=NOW)

    assert len(scoped) == 1
    assert len(shared) == 4
    # precision against the intent "what does Marketing know about the name"
    assert all(h["department"] == "marketing" for h in scoped)
    assert len({h["department"] for h in shared}) == 4


def test_scoped_precision_holds_as_other_departments_accumulate_history():
    """Volume in other departments must not degrade this one's retrieval."""
    remember("marketing", "diwali campaign delivered strong footfall")
    for i in range(60):
        remember("legal", f"compliance note {i} about campaign disclosures")
        remember("finance", f"budget line {i} for campaign spend")

    scoped = M.retrieve("c1", "marketing", "campaign", now=NOW, limit=5)
    shared = M.retrieve_shared("c1", "campaign", now=NOW, limit=5)

    assert [h["department"] for h in scoped] == ["marketing"]
    # the shared store is now dominated by other departments
    assert sum(1 for h in shared if h["department"] == "marketing") < len(shared)


# ===================== TYPES =================================================


def test_all_four_types_are_available():
    assert set(ALL_TYPES) == {
        MemoryType.EPISODIC, MemoryType.SEMANTIC,
        MemoryType.PROCEDURAL, MemoryType.REFLECTIVE,
    }


def test_retrieval_can_be_restricted_to_one_type():
    remember("marketing", "ran the diwali campaign in october",
             MemoryType.EPISODIC)
    remember("marketing", "diwali campaigns outperform in october",
             MemoryType.SEMANTIC)
    remember("marketing", "how to run a diwali campaign: brief, book, measure",
             MemoryType.PROCEDURAL)

    method = M.retrieve("c1", "marketing", "diwali campaign",
                        types=[MemoryType.PROCEDURAL], now=NOW)
    assert len(method) == 1
    assert method[0]["memory_type"] == str(MemoryType.PROCEDURAL)


def test_a_planner_can_ask_for_method_without_receiving_anecdotes():
    for i in range(5):
        remember("marketing", f"campaign {i} ran in october with discount offer",
                 MemoryType.EPISODIC)
    remember("marketing", "campaign method: brief, book, measure, review",
             MemoryType.PROCEDURAL)

    method = M.retrieve("c1", "marketing", "campaign method",
                        types=[MemoryType.PROCEDURAL], now=NOW)
    assert all(h["memory_type"] == str(MemoryType.PROCEDURAL) for h in method)


# ===================== CONSOLIDATION =========================================


def test_a_near_duplicate_increments_rather_than_duplicating():
    first = remember("marketing", "diwali campaign delivered strong footfall")
    second = remember("marketing", "diwali campaign delivered strong footfall")
    assert first == second
    assert M.count("c1", "marketing") >= 1


def test_repeated_episode_is_promoted_to_a_semantic_conclusion():
    for _ in range(CONSOLIDATION_THRESHOLD):
        remember("marketing", "discount promotions lift footfall and cut margin")

    semantic = M.retrieve("c1", "marketing", "discount promotions footfall",
                          types=[MemoryType.SEMANTIC], now=NOW)
    assert semantic
    assert "Observed" in semantic[0]["content"]


def test_eleven_repeats_carry_one_conclusion_not_eleven_anecdotes():
    for _ in range(11):
        remember("marketing", "discount promotions lift footfall and cut margin")
    counts = M.stats("c1")["marketing"]
    assert counts[str(MemoryType.EPISODIC)] == 1
    assert counts.get(str(MemoryType.SEMANTIC), 0) == 1


def test_consolidation_does_not_fire_below_the_threshold():
    remember("marketing", "a one-off observation about pricing")
    assert str(MemoryType.SEMANTIC) not in M.stats("c1").get("marketing", {})


def test_distinct_content_is_not_consolidated():
    remember("marketing", "diwali campaign delivered strong footfall")
    remember("marketing", "supplier renegotiation reduced unit cost sharply")
    assert M.count("c1", "marketing") == 2


# ===================== SCORING ===============================================


def test_recent_memory_outranks_an_older_equal_match():
    old = (NOW - timedelta(days=300)).isoformat()
    remember("marketing", "diwali campaign footfall result", created_at=old)
    remember("marketing", "diwali campaign footfall outcome",
             created_at=NOW.isoformat())
    hits = M.retrieve("c1", "marketing", "diwali campaign footfall", now=NOW)
    assert hits[0]["created_at"] == NOW.isoformat()


def test_retrieval_count_is_recorded_and_raises_future_rank():
    remember("marketing", "diwali campaign footfall result alpha")
    remember("marketing", "diwali campaign footfall result beta")
    first = M.retrieve("c1", "marketing", "diwali campaign", now=NOW)
    promoted = first[0]["id"]
    for _ in range(5):
        M.retrieve("c1", "marketing", "diwali campaign", now=NOW)
    again = M.retrieve("c1", "marketing", "diwali campaign", now=NOW)
    assert again[0]["id"] == promoted
    assert again[0]["retrieval_count"] > 0


def test_retrieval_can_be_observed_without_being_recorded():
    remember("marketing", "diwali campaign footfall")
    M.retrieve("c1", "marketing", "diwali", now=NOW, record_retrieval=False)
    hits = M.retrieve("c1", "marketing", "diwali", now=NOW,
                      record_retrieval=False)
    assert hits[0]["retrieval_count"] == 0


def test_an_unrelated_query_returns_nothing_rather_than_a_weak_match():
    remember("marketing", "diwali campaign delivered strong footfall")
    assert M.retrieve("c1", "marketing", "supplier logistics warehouse",
                      now=NOW) == []


def test_limit_is_respected():
    for i in range(10):
        remember("marketing", f"campaign {i} footfall outcome variant {i}")
    assert len(M.retrieve("c1", "marketing", "campaign footfall", limit=3,
                          now=NOW)) == 3


def test_tokenise_drops_stopwords_and_short_tokens():
    assert tokenise("The campaign was a big win in October") == [
        "campaign", "big", "win", "october"
    ]


def test_tokenise_keeps_numbers_regardless_of_length():
    """Regression: numbers were dropped, so distinct amounts looked identical."""
    assert tokenise("budget of 15 lakh for q3 2026") == [
        "budget", "15", "lakh", "q3", "2026"
    ]


def test_different_amounts_are_not_consolidated():
    """The defect this guards: two budgets became one memory."""
    remember("finance", "approved marketing budget of 15 lakh")
    remember("finance", "approved marketing budget of 40 lakh")
    assert M.count("c1", "finance") == 2


def test_different_periods_are_not_consolidated():
    remember("finance", "revenue for q1 came in below forecast")
    remember("finance", "revenue for q3 came in below forecast")
    assert M.count("c1", "finance") == 2


# ===================== HOUSEKEEPING ==========================================


def test_superseded_memory_is_excluded_from_retrieval():
    old = remember("marketing", "target persona is students aged eighteen")
    new = remember("marketing", "target persona is families with children")
    M.supersede(old, new)
    hits = M.retrieve("c1", "marketing", "target persona", now=NOW)
    assert all(h["id"] != old for h in hits)


def test_decay_retires_unretrieved_aged_episodes():
    stale = (NOW - timedelta(days=400)).isoformat()
    remember("marketing", "an episode nobody ever needed again",
             created_at=stale)
    assert M.decay("c1", "marketing", now=NOW) == 1
    assert M.retrieve("c1", "marketing", "episode nobody", now=NOW) == []


def test_decay_spares_memories_that_have_proved_useful():
    stale = (NOW - timedelta(days=400)).isoformat()
    remember("marketing", "an old but frequently consulted lesson",
             created_at=stale)
    M.retrieve("c1", "marketing", "frequently consulted lesson", now=NOW)
    assert M.decay("c1", "marketing", now=NOW) == 0


def test_decay_spares_semantic_conclusions():
    """Consolidated knowledge is the point of consolidating; it must not age out."""
    stale = (NOW - timedelta(days=400)).isoformat()
    remember("marketing", "discount promotions reliably cut margin",
             MemoryType.SEMANTIC, created_at=stale)
    assert M.decay("c1", "marketing", now=NOW) == 0


def test_decay_is_department_scoped():
    stale = (NOW - timedelta(days=400)).isoformat()
    remember("marketing", "marketing episode nobody needed", created_at=stale)
    remember("finance", "finance episode nobody needed", created_at=stale)
    assert M.decay("c1", "marketing", now=NOW) == 1
    assert M.count("c1", "finance") == 1


# ===================== STATS =================================================


def test_stats_report_per_department_counts_by_type():
    remember("marketing", "campaign outcome alpha", MemoryType.EPISODIC)
    remember("marketing", "campaign lesson beta", MemoryType.REFLECTIVE)
    remember("finance", "budget outcome gamma", MemoryType.EPISODIC)
    stats = M.stats("c1")
    assert stats["marketing"][str(MemoryType.EPISODIC)] == 1
    assert stats["marketing"][str(MemoryType.REFLECTIVE)] == 1
    assert stats["finance"][str(MemoryType.EPISODIC)] == 1


def test_each_departments_learning_can_be_measured_separately():
    """The property a shared store cannot provide."""
    for i in range(4):
        remember("marketing", f"marketing lesson {i}", MemoryType.REFLECTIVE)
    remember("finance", "finance lesson", MemoryType.REFLECTIVE)
    stats = M.stats("c1")
    assert stats["marketing"][str(MemoryType.REFLECTIVE)] == 4
    assert stats["finance"][str(MemoryType.REFLECTIVE)] == 1


def test_confidence_is_bounded():
    with pytest.raises(ValueError):
        Memory(company_id="c1", department="marketing",
               memory_type=MemoryType.EPISODIC, content="x", confidence=1.5)


def test_empty_content_is_rejected():
    with pytest.raises(ValueError):
        Memory(company_id="c1", department="marketing",
               memory_type=MemoryType.EPISODIC, content="   ")
