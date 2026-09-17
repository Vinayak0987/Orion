"""Tests for the deterministic operations feasibility scorer (Phase 2). Offline."""

from __future__ import annotations

from app.agents.operations_feasibility import fallback_summary, score_operations
from app.models.departments import (
    OperationsOutput,
    ProcessStep,
    Role,
    ToolRecommendation,
)
from app.models.intent import BusinessIntent, Budget


def _good_ops() -> OperationsOutput:
    """A fully consistent, complete, affordable operations plan -> 100."""
    return OperationsOutput(
        roles=[Role(title="Manager", headcount=1), Role(title="Cashier", headcount=2)],
        total_monthly_payroll_inr=60_000,
        tools=[
            ToolRecommendation(name="Khatabook", purpose="accounting and billing"),
            ToolRecommendation(name="WhatsApp Business", purpose="customer communication"),
            ToolRecommendation(name="Vyapar", purpose="inventory and POS"),
        ],
        total_tool_cost_monthly_inr=0,
        daily_workflow=[
            ProcessStep(order=1, name="Open", owner_role="Manager"),
            ProcessStep(order=2, name="Stock check", owner_role="Cashier"),
            ProcessStep(order=3, name="Serve", owner_role="Cashier"),
            ProcessStep(order=4, name="Close", owner_role="Manager"),
        ],
        quality_checkpoints=["hygiene", "cash reconciliation", "stock audit"],
    )


def _intent(amount: int = 1_500_000) -> BusinessIntent:
    return BusinessIntent(business_type="ice_cream_shop", budget=Budget(amount=amount, specified=True))


def test_good_plan_scores_100() -> None:
    score, warnings = score_operations(_good_ops(), _intent())
    assert score == 100
    assert warnings == []


def test_orphan_owner_role_fails_consistency() -> None:
    ops = _good_ops()
    ops.daily_workflow.append(ProcessStep(order=5, name="Deliver", owner_role="Driver"))  # not a role
    score, warnings = score_operations(ops, _intent())
    assert score == 75  # one of four checks failed
    assert any("not in the staffing plan" in w and "Driver" in w for w in warnings)


def test_over_budget_fails_feasibility() -> None:
    ops = _good_ops()
    ops.total_monthly_payroll_inr = 5_000_000  # way over a 15L budget
    score, warnings = score_operations(ops, _intent(1_500_000))
    assert score == 75
    assert any("looks high" in w for w in warnings)


def test_thin_process_fails_completeness() -> None:
    ops = _good_ops()
    ops.daily_workflow = ops.daily_workflow[:2]  # only 2 steps
    ops.quality_checkpoints = ["hygiene"]  # only 1
    score, warnings = score_operations(ops, _intent())
    assert score == 75
    assert any("thin" in w for w in warnings)


def test_missing_tools_fails_coverage() -> None:
    ops = _good_ops()
    ops.tools = [ToolRecommendation(name="Canva", purpose="design")]  # no essentials
    score, warnings = score_operations(ops, _intent())
    assert score == 75
    assert any("operational essential" in w for w in warnings)


def test_no_budget_does_not_penalise_feasibility() -> None:
    ops = _good_ops()
    ops.total_monthly_payroll_inr = 9_999_999
    score, _ = score_operations(ops, None)  # no intent/budget
    assert score == 100  # feasibility check skipped, not failed


def test_multiple_failures_lower_the_score() -> None:
    ops = _good_ops()
    ops.daily_workflow = [ProcessStep(order=1, name="X", owner_role="Ghost")]  # orphan + thin
    ops.tools = []  # no coverage
    score, warnings = score_operations(ops, _intent())
    assert score == 25  # only feasibility passes
    assert len(warnings) == 3


def test_scoring_is_deterministic() -> None:
    ops, intent = _good_ops(), _intent()
    assert score_operations(ops, intent) == score_operations(ops, intent)


def test_fallback_summary() -> None:
    assert "consistent" in fallback_summary(100, [])
    assert "Main issues" in fallback_summary(50, ["a", "b"])
    assert "could not be assessed" in fallback_summary(None, [])
