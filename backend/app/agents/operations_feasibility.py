"""Deterministic operations feasibility scorer (F37a support).

Pure Python, no LLM, no I/O: given a completed OperationsOutput and the run's
intent, it checks the operations plan for internal consistency and realism and
returns a 0-100 score plus human-readable warnings. Same discipline as
`strategy_scoring.py` and the finance totals: the score is COMPUTED here, never
asserted by the model, so it is deterministic and unit-testable.

Four equally-weighted checks:
  1. Consistency  - every process-step owner_role exists in the staffing roles.
  2. Feasibility  - monthly payroll + tool cost fit the stated budget.
  3. Completeness - enough workflow steps and quality checkpoints.
  4. Tech coverage- the stack covers the operational essentials.

A check that cannot be judged (e.g. no budget stated) passes rather than
penalising the plan for information it was never given.
"""

from __future__ import annotations

from app.models.departments import OperationsOutput
from app.models.intent import BusinessIntent

# Operational essentials a viable small business should have some tooling for.
_ESSENTIAL_TOOL_KEYWORDS = ("billing", "pos", "account", "communicat", "inventory", "messag")
_MIN_ESSENTIALS_COVERED = 3
_MIN_WORKFLOW_STEPS = 4
_MIN_CHECKPOINTS = 3
# Monthly payroll + tools should not exceed this fraction of (budget / 12).
_MONTHLY_BUDGET_FRACTION = 0.6


def _consistency_ok(ops: OperationsOutput) -> tuple[bool, str | None]:
    role_titles = {r.title.strip().lower() for r in ops.roles if r.title.strip()}
    if not role_titles or not ops.daily_workflow:
        return True, None  # nothing to cross-check yet
    orphans = sorted(
        {
            s.owner_role.strip()
            for s in ops.daily_workflow
            if s.owner_role.strip() and s.owner_role.strip().lower() not in role_titles
        }
    )
    if orphans:
        return False, (
            f"{len(orphans)} workflow step(s) owned by role(s) not in the staffing "
            f"plan: {', '.join(orphans)[:120]}"
        )
    return True, None


def _feasibility_ok(ops: OperationsOutput, intent: BusinessIntent | None) -> tuple[bool, str | None]:
    monthly = (ops.total_monthly_payroll_inr or 0) + (ops.total_tool_cost_monthly_inr or 0)
    if intent is None or not intent.budget.specified or intent.budget.amount <= 0:
        return True, None  # cannot judge without a budget
    affordable = intent.budget.amount * _MONTHLY_BUDGET_FRACTION / 12
    if monthly == 0 or monthly <= affordable:
        return True, None
    return False, (
        f"monthly operating cost (Rs {monthly:,}) looks high for a "
        f"{intent.budget.display} budget - verify staffing/tooling scale"
    )


def _completeness_ok(ops: OperationsOutput) -> tuple[bool, str | None]:
    if (
        len(ops.daily_workflow) >= _MIN_WORKFLOW_STEPS
        and len(ops.quality_checkpoints) >= _MIN_CHECKPOINTS
    ):
        return True, None
    return False, (
        f"process detail is thin ({len(ops.daily_workflow)} workflow steps, "
        f"{len(ops.quality_checkpoints)} checkpoints) - operations may be underspecified"
    )


def _tech_coverage_ok(ops: OperationsOutput) -> tuple[bool, str | None]:
    haystack = " ".join(f"{t.name} {t.purpose}".lower() for t in ops.tools)
    covered = sum(1 for kw in _ESSENTIAL_TOOL_KEYWORDS if kw in haystack)
    if covered >= _MIN_ESSENTIALS_COVERED:
        return True, None
    return False, (
        f"tech stack covers only {covered} operational essential(s) "
        f"(billing/POS, accounting, communication, inventory)"
    )


def score_operations(
    ops: OperationsOutput, intent: BusinessIntent | None
) -> tuple[int, list[str]]:
    """Return (score_0_100, warnings). Deterministic; four equal checks."""
    checks = [
        _consistency_ok(ops),
        _feasibility_ok(ops, intent),
        _completeness_ok(ops),
        _tech_coverage_ok(ops),
    ]
    passed = sum(1 for ok, _ in checks if ok)
    warnings = [msg for ok, msg in checks if not ok and msg]
    score = round(passed / len(checks) * 100)
    return score, warnings


def fallback_summary(score: int | None, warnings: list[str]) -> str:
    """Deterministic summary used when the LLM synthesis pass is unavailable."""
    if score is None:
        return "Operations feasibility could not be assessed."
    if not warnings:
        return f"Operations plan is internally consistent (feasibility score {score}/100)."
    return (
        f"Operations feasibility score {score}/100. Main issues: "
        + "; ".join(warnings[:3])
        + "."
    )
