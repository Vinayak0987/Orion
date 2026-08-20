"""Tests for reflection.

The property that matters: the verdict is decided by anchor movement, not by what
the department says about itself.
"""

from __future__ import annotations

import pytest

from app.operating import ledger, memory as M
from app.operating import reflection as R
from app.operating.anchors import AnchorSet
from app.operating.ledger import EntryKind, LedgerEntry
from app.operating.memory import MemoryType
from app.operating.reflection import Verdict


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    from app.db import sqlite as sqlite_module

    db_file = tmp_path / "reflection-test.db"
    monkeypatch.setattr(
        sqlite_module.settings.__class__, "sqlite_file",
        property(lambda _self: db_file),
    )
    ledger.init_ledger()
    M.init_memory()
    yield


def add(kind, *, amount=0, quantity=0, department="finance"):
    kwargs = dict(company_id="c1", kind=kind, department=department, actor="a")
    if amount:
        kwargs["amount_minor"] = amount
    if quantity:
        kwargs["quantity"] = quantity
    ledger.append(LedgerEntry(**kwargs))


def snap() -> AnchorSet:
    return AnchorSet.compute("c1")


# ===================== GROUNDING ==============================================


def test_declining_margin_produces_a_negative_verdict():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snap()
    add(EntryKind.COGS, amount=600_00)
    after = snap()

    reflection = R.reflect("c1", "marketing", before, after)
    assert reflection.verdict is Verdict.DECLINED
    assert reflection.adverse


def test_a_departments_optimism_does_not_change_the_verdict():
    """The central constraint."""
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snap()
    add(EntryKind.COGS, amount=600_00)
    after = snap()

    reflection = R.reflect(
        "c1", "marketing", before, after,
        claimed="an outstanding month; footfall at record highs",
        claimed_verdict=Verdict.IMPROVED,
    )
    assert reflection.verdict is Verdict.DECLINED
    assert reflection.contradicted is True
    assert "outstanding" in reflection.claimed  # recorded, but carries no weight


def test_an_agreeing_claim_is_not_marked_contradicted():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=600_00)
    before = snap()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=100_00)
    after = snap()

    reflection = R.reflect("c1", "finance", before, after,
                           claimed_verdict=Verdict.IMPROVED)
    assert reflection.verdict is Verdict.IMPROVED
    assert reflection.contradicted is False


def test_improving_period_produces_a_positive_verdict():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=600_00)
    before = snap()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=100_00)
    after = snap()
    assert R.reflect("c1", "finance", before, after).verdict is Verdict.IMPROVED


def test_no_computable_anchors_yields_unknown_not_a_guess():
    before = snap()
    after = snap()
    assert R.reflect("c1", "marketing", before, after).verdict is Verdict.UNKNOWN


def test_immaterial_movement_is_flat():
    """Margin is unchanged across the period, so there is nothing to learn.

    Scoped to the margin anchor: revenue also doubled, which is a real and
    favourable movement, and a whole-company reflection should say so.
    """
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=500_00)
    before = snap()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=500_00)
    after = snap()
    reflection = R.reflect("c1", "finance", before, after,
                           anchors=("gross_margin_pct",))
    assert reflection.movements[0].material is False
    assert reflection.verdict is Verdict.FLAT


def test_revenue_growth_at_constant_margin_is_still_an_improvement():
    """The unscoped view of the same period."""
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=500_00)
    before = snap()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=500_00)
    after = snap()
    assert R.reflect("c1", "finance", before, after).verdict is Verdict.IMPROVED


# ===================== DIRECTION ==============================================


def test_lower_is_better_anchors_are_interpreted_correctly():
    """Rising churn is a decline, even though the number went up."""
    for _ in range(10):
        add(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="sales")
    add(EntryKind.CUSTOMER_CHURNED, quantity=1, department="sales")
    before = snap()
    for _ in range(5):
        add(EntryKind.CUSTOMER_CHURNED, quantity=1, department="sales")
    after = snap()

    reflection = R.reflect("c1", "sales", before, after,
                           anchors=("churn_pct",))
    movement = reflection.movements[0]
    assert movement.anchor == "churn_pct"
    assert movement.delta > 0
    assert movement.favourable is False
    assert reflection.verdict is Verdict.DECLINED


def test_falling_cac_is_favourable():
    add(EntryKind.MARKETING_SPEND, amount=1_000_00, department="marketing")
    for _ in range(2):
        add(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="sales")
    before = snap()
    for _ in range(8):
        add(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="sales")
    after = snap()

    reflection = R.reflect("c1", "marketing", before, after, anchors=("cac",))
    assert reflection.movements[0].delta < 0
    assert reflection.movements[0].favourable is True


def test_lower_is_better_set_is_explicit():
    assert "churn_pct" in R.LOWER_IS_BETTER
    assert "cac" in R.LOWER_IS_BETTER
    assert "net_margin_pct" not in R.LOWER_IS_BETTER


# ===================== LESSONS ================================================


def test_lessons_name_the_measured_movement():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    add(EntryKind.OPEX, amount=100_00)
    before = snap()
    add(EntryKind.COGS, amount=800_00)
    after = snap()

    reflection = R.reflect("c1", "finance", before, after)
    assert reflection.lessons
    for lesson in reflection.lessons:
        assert "(" in lesson and ")" in lesson  # carries the delta


def test_no_lessons_are_derived_from_a_good_period():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=600_00)
    before = snap()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=100_00)
    after = snap()
    assert R.reflect("c1", "finance", before, after).lessons == ()


def test_only_anchors_with_a_template_produce_a_lesson():
    """No generic advice; a lesson must name a specific problem."""
    add(EntryKind.REVENUE, amount=1_000_00)
    before = snap()
    add(EntryKind.CAPEX, amount=500_00)
    after = snap()
    reflection = R.reflect("c1", "finance", before, after, anchors=("capex",))
    assert reflection.lessons == ()


# ===================== PERSISTENCE ============================================


def test_lessons_are_written_to_the_departments_reflective_memory():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snap()
    add(EntryKind.COGS, amount=800_00)
    after = snap()

    reflection = R.reflect("c1", "marketing", before, after)
    written = R.persist(reflection)
    assert written

    stored = M.stats("c1")["marketing"]
    assert stored[str(MemoryType.REFLECTIVE)] >= 1


def test_a_contradiction_is_itself_recorded_as_a_lesson():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snap()
    add(EntryKind.COGS, amount=800_00)
    after = snap()

    reflection = R.reflect("c1", "marketing", before, after,
                           claimed_verdict=Verdict.IMPROVED)
    R.persist(reflection)
    hits = M.retrieve("c1", "marketing", "own assessment measured outcome")
    assert hits


def test_reflection_memory_is_department_scoped():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snap()
    add(EntryKind.COGS, amount=800_00)
    after = snap()
    R.persist(R.reflect("c1", "marketing", before, after))
    assert "finance" not in M.stats("c1")


def test_a_good_period_writes_nothing():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=600_00)
    before = snap()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=100_00)
    after = snap()
    assert R.persist(R.reflect("c1", "finance", before, after)) == []


# ===================== RENDERING ==============================================


def test_text_marks_a_contradiction_plainly():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snap()
    add(EntryKind.COGS, amount=800_00)
    after = snap()
    text = R.reflect("c1", "marketing", before, after,
                     claimed_verdict=Verdict.IMPROVED).as_text()
    assert "DECLINED" in text
    assert "measurement stands" in text


def test_text_lists_material_movements_only():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snap()
    add(EntryKind.COGS, amount=800_00)
    after = snap()
    text = R.reflect("c1", "finance", before, after).as_text()
    assert "worsened" in text


# ===================== SCHEDULER ADAPTER ======================================


def test_handler_reflects_and_reports_a_summary():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snap()
    add(EntryKind.COGS, amount=800_00)

    handler = R.make_handler(
        before_provider=lambda c, n: before,
        after_provider=lambda c, n: AnchorSet.compute(c),
        department="marketing",
    )
    from datetime import UTC, datetime

    result = handler("c1", datetime(2026, 8, 1, tzinfo=UTC))
    assert result["verdict"] == str(Verdict.DECLINED)
    assert result["lessons"] >= 1
    assert result["memories_written"] >= 1


def test_handler_passes_a_claim_through_without_letting_it_decide():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snap()
    add(EntryKind.COGS, amount=800_00)

    handler = R.make_handler(
        before_provider=lambda c, n: before,
        after_provider=lambda c, n: AnchorSet.compute(c),
        department="marketing",
        claim_provider=lambda c, n: ("record footfall", Verdict.IMPROVED),
    )
    from datetime import UTC, datetime

    result = handler("c1", datetime(2026, 8, 1, tzinfo=UTC))
    assert result["verdict"] == str(Verdict.DECLINED)
    assert result["contradicted"] is True
