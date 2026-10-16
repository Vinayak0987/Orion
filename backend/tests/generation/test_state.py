"""Tests for F14/F15/F16 - SharedBusinessState and the append-only contract.

Runs offline. No API keys required.
"""

from __future__ import annotations

import pytest

from app.generation.models.intent import Budget, BusinessIntent, Location, Scale, Sector
from app.generation.models.state import (
    Department,
    RunStatus,
    StateContractViolation,
    apply_department_patch,
    new_state,
)


# =============================================================================
# F14 - state schema
# =============================================================================


def test_new_state_initializes_empty_telemetry() -> None:
    state = new_state("sess-1", "Ice cream shop in Andheri, Rs 15L budget")

    assert state["session_id"] == "sess-1"
    assert state["agent_traces"] == []
    assert state["api_traces"] == []
    assert state["errors"] == []
    assert state["metadata"].status is RunStatus.PENDING
    # No department section exists until an agent writes one.
    assert "strategy" not in state


# =============================================================================
# F15 - append-only contract
# =============================================================================


def test_agent_can_write_its_own_department() -> None:
    state = new_state("sess-2", "prompt")
    update = apply_department_patch(
        state, Department.STRATEGY, {"executive_summary": "A premium gelato outlet."}
    )

    assert set(update) == {"strategy"}
    assert update["strategy"].executive_summary == "A premium gelato outlet."


def test_agent_cannot_write_another_department() -> None:
    state = new_state("sess-3", "prompt")

    with pytest.raises(StateContractViolation, match="attempted to write to"):
        apply_department_patch(
            state,
            Department.BRANDING,
            {"recommended_name": "Frostbite", "finance": {"gross_margin_pct": 99.0}},
        )


def test_unknown_field_is_rejected() -> None:
    """Field names are frozen because F54-F57 metrics index into them."""
    state = new_state("sess-4", "prompt")

    with pytest.raises(StateContractViolation, match="Unknown field"):
        apply_department_patch(state, Department.FINANCE, {"projected_profit": 500000})


def test_patch_merges_without_clobbering_prior_fields() -> None:
    state = new_state("sess-5", "prompt")

    first = apply_department_patch(state, Department.FINANCE, {"pricing_strategy": "premium"})
    state["finance"] = first["finance"]

    second = apply_department_patch(state, Department.FINANCE, {"break_even_month": 9})

    assert second["finance"].pricing_strategy == "premium"  # preserved
    assert second["finance"].break_even_month == 9  # added


def test_parallel_department_writes_do_not_collide() -> None:
    """F12 - Finance, Branding and Marketing run concurrently; each returns a
    disjoint partial-state dict, so LangGraph merges them without conflict."""
    state = new_state("sess-6", "prompt")

    updates = [
        apply_department_patch(state, Department.FINANCE, {"break_even_month": 8}),
        apply_department_patch(state, Department.BRANDING, {"recommended_name": "Kulfi Co"}),
        apply_department_patch(state, Department.MARKETING, {"content_frequency": "weekly"}),
    ]

    written_keys = [k for u in updates for k in u]
    assert len(written_keys) == len(set(written_keys)), "parallel writes overlapped"


# =============================================================================
# F4 - budget parsing / scale derivation
# =============================================================================


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (500_000, Scale.MICRO),
        (1_500_000, Scale.SMALL),
        (8_000_000, Scale.MEDIUM),
        (30_000_000, Scale.LARGE),
    ],
)
def test_budget_scale_bands(amount: int, expected: Scale) -> None:
    assert Budget(amount=amount, specified=True).scale is expected


def test_unspecified_budget_has_unspecified_scale() -> None:
    assert Budget().scale is Scale.UNSPECIFIED


def test_budget_display_uses_indian_notation() -> None:
    assert Budget(amount=1_500_000, specified=True).display == "Rs 15.0 L"
    assert Budget(amount=25_000_000, specified=True).display == "Rs 2.50 Cr"


# =============================================================================
# F3 / F5 - intent normalization
# =============================================================================


def test_business_type_is_normalized_to_snake_case() -> None:
    intent = BusinessIntent(business_type="Ice Cream Shop")
    assert intent.business_type == "ice_cream_shop"


def test_intent_derives_scale_from_budget() -> None:
    intent = BusinessIntent(
        business_type="ice_cream_shop",
        budget=Budget(amount=1_500_000, specified=True),
    )
    assert intent.scale is Scale.SMALL


def test_location_query_string_skips_unspecified_parts() -> None:
    assert Location(area="Andheri").query_string == "Andheri, Mumbai, Maharashtra"
    assert Location().query_string == "Mumbai, Maharashtra"


def test_intent_defaults_are_mumbai_and_unspecified_sector() -> None:
    intent = BusinessIntent()
    assert intent.location.city == "Mumbai"
    assert intent.sector is Sector.UNSPECIFIED
