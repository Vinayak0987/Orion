"""Tests for the governance gate chain.

The important properties are the refusals: an unapproved action cannot execute,
an approval cannot unlock a hard constraint, and the audit trail cannot be
rewritten to hide either.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.db.sqlite import connection
from app.operating import governance as G
from app.operating import ledger
from app.operating.constitution import (
    ActionKind,
    ConstitutionContext,
    ConstitutionViolation,
    ProposedAction,
)
from app.operating.governance import (
    DecisionState,
    IllegalTransition,
    NotApproved,
    Policy,
    Risk,
    Stage,
)


@pytest.fixture(autouse=True)
def gov_db(tmp_path, monkeypatch):
    from app.db import sqlite as sqlite_module

    db_file = tmp_path / "governance-test.db"
    monkeypatch.setattr(
        sqlite_module.settings.__class__, "sqlite_file",
        property(lambda _self: db_file),
    )
    ledger.init_ledger()
    G.init_governance()
    yield


def action(**kwargs) -> ProposedAction:
    defaults = dict(
        kind=ActionKind.SPEND, department="marketing", actor="campaign_plan",
        company_id="c1", amount_minor=1_000_00, description="run a promotion",
    )
    defaults.update(kwargs)
    return ProposedAction(**defaults)


# ------------------------------------------------------------ classification ---


def test_routine_action_is_auto_approved():
    d = G.submit("d1", action(amount_minor=100_00))
    assert d.risk is Risk.ROUTINE
    assert d.state is DecisionState.APPROVED
    assert d.decided_by == "policy:auto"


def test_large_spend_goes_to_review():
    d = G.submit("d1", action(amount_minor=9_000_00))
    assert d.risk is Risk.ELEVATED
    assert d.state is DecisionState.PENDING_REVIEW


def test_subjective_action_goes_to_a_human_by_rule():
    d = G.submit("d1", action(kind=ActionKind.CHANGE_PRICE, amount_minor=0))
    assert d.risk is Risk.SUBJECTIVE
    assert d.state is DecisionState.PENDING_REVIEW
    assert "judgement" in d.reason


def test_irreversible_action_goes_to_review_regardless_of_amount():
    d = G.submit("d1", action(kind=ActionKind.SIGN_CONTRACT, amount_minor=1))
    assert d.risk is Risk.IRREVERSIBLE
    assert d.state is DecisionState.PENDING_REVIEW


def test_policy_can_disable_auto_approval():
    strict = Policy(auto_approve_routine=False)
    d = G.submit("d1", action(amount_minor=1_00), policy=strict)
    assert d.state is DecisionState.PENDING_REVIEW


def test_policy_threshold_is_configurable():
    lenient = Policy(review_above_minor=100_000_00)
    d = G.submit("d1", action(amount_minor=9_000_00), policy=lenient)
    assert d.risk is Risk.ROUTINE


def test_elevated_reason_states_the_amount_in_major_units():
    """Regression: the amount was divided by 100 twice, understating it 100x."""
    d = G.submit("d1", action(amount_minor=2_00_000_00))  # Rs 200,000
    assert "200,000.00" in d.reason
    assert "2,000.00 exceeds" not in d.reason


# -------------------------------------------------------- approval and refusal --


def test_approval_requires_a_named_human():
    d = G.submit("d1", action(amount_minor=9_000_00))
    with pytest.raises(ValueError):
        G.approve(d, by="   ")


def test_approved_decision_executes():
    d = G.submit("d1", action(amount_minor=9_000_00))
    G.approve(d, by="founder")
    G.execute(d, ConstitutionContext(daily_spend_cap_minor=100_000_00,
                                     single_spend_cap_minor=100_000_00))
    assert d.state is DecisionState.EXECUTED


def test_unapproved_decision_cannot_execute():
    d = G.submit("d1", action(amount_minor=9_000_00))
    assert d.state is DecisionState.PENDING_REVIEW
    with pytest.raises(NotApproved):
        G.execute(d)


def test_rejected_decision_cannot_execute():
    d = G.submit("d1", action(amount_minor=9_000_00))
    G.reject(d, by="founder", reason="not now")
    with pytest.raises(NotApproved):
        G.execute(d)


def test_rejection_is_terminal():
    d = G.submit("d1", action(amount_minor=9_000_00))
    G.reject(d, by="founder")
    with pytest.raises(IllegalTransition):
        G.approve(d, by="founder")


def test_returned_decision_can_be_resubmitted():
    d = G.submit("d1", action(amount_minor=9_000_00))
    G.return_for_revision(d, by="founder", reason="reduce the amount")
    assert d.state is DecisionState.RETURNED
    G._transition(d, DecisionState.PROPOSED)
    assert d.state is DecisionState.PROPOSED


def test_executed_decision_cannot_execute_twice():
    d = G.submit("d1", action(amount_minor=100_00))
    G.execute(d)
    with pytest.raises(NotApproved):
        G.execute(d)


# ------------------------------- the Constitution overrides human approval -----


def test_human_approval_does_not_unlock_a_hard_constraint():
    """The point of the two-layer design."""
    d = G.submit("d1", action(kind=ActionKind.DELETE_CUSTOMER_DATA,
                              amount_minor=0))
    G.approve(d, by="founder")
    with pytest.raises(ConstitutionViolation):
        G.execute(d)
    assert d.state is DecisionState.BLOCKED


def test_spend_approved_then_blocked_when_the_budget_moved():
    """Facts change while a decision waits, so the gate re-checks at execution."""
    d = G.submit("d1", action(amount_minor=9_000_00))
    G.approve(d, by="founder")
    tight = ConstitutionContext(daily_spend_cap_minor=10_000_00,
                                spent_today_minor=9_500_00)
    with pytest.raises(ConstitutionViolation):
        G.execute(d, tight)
    assert d.state is DecisionState.BLOCKED


def test_blocked_is_terminal():
    d = G.submit("d1", action(kind=ActionKind.DELETE_CUSTOMER_DATA,
                              amount_minor=0))
    G.approve(d, by="founder")
    with pytest.raises(ConstitutionViolation):
        G.execute(d)
    with pytest.raises(IllegalTransition):
        G.approve(d, by="founder")


# --------------------------------------------------------------- audit trail ---


def test_audit_records_every_stage_of_a_successful_passage():
    d = G.submit("d1", action(amount_minor=100_00))
    G.execute(d)
    stages = [row["stage"] for row in G.audit_for("d1")]
    assert str(Stage.DECISION) in stages
    assert str(Stage.APPROVAL_GATE) in stages
    assert str(Stage.EXECUTION_GATE) in stages
    assert str(Stage.AUDIT) in stages


def test_audit_records_a_halt():
    d = G.submit("d1", action(kind=ActionKind.DELETE_CUSTOMER_DATA,
                              amount_minor=0))
    G.approve(d, by="founder")
    with pytest.raises(ConstitutionViolation):
        G.execute(d)
    trail = G.audit_for("d1")
    blocked = [r for r in trail if r["outcome"] == "blocked"]
    assert len(blocked) == 1
    assert blocked[0]["rule_id"] == "C4_NO_CUSTOMER_DATA_DELETION"


def test_audit_records_who_approved():
    d = G.submit("d1", action(amount_minor=9_000_00))
    G.approve(d, by="vinayak")
    approvals = [r for r in G.audit_for("d1") if r["outcome"] == "approved"]
    assert approvals[0]["actor"] == "vinayak"


def test_audit_records_a_refused_execution_attempt():
    d = G.submit("d1", action(amount_minor=9_000_00))
    with pytest.raises(NotApproved):
        G.execute(d)
    refusals = [r for r in G.audit_for("d1") if r["outcome"] == "refused"]
    assert len(refusals) == 1


def test_audit_trail_rejects_update():
    d = G.submit("d1", action(amount_minor=100_00))
    G.execute(d)
    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        with connection() as conn:
            conn.execute("UPDATE audit_trail SET outcome = 'approved'")
    assert "append-only" in str(excinfo.value)


def test_audit_trail_rejects_delete():
    d = G.submit("d1", action(amount_minor=100_00))
    G.execute(d)
    with pytest.raises(sqlite3.IntegrityError):
        with connection() as conn:
            conn.execute("DELETE FROM audit_trail")
    assert len(G.audit_for("d1")) > 0


def test_audit_is_ordered():
    d = G.submit("d1", action(amount_minor=100_00))
    G.execute(d)
    seqs = [r["seq"] for r in G.audit_for("d1")]
    assert seqs == sorted(seqs)


# ------------------------------------------------------------- review queue ----


def test_review_queue_lists_pending_decisions_worst_risk_first():
    G.submit("d1", action(amount_minor=9_000_00))                       # elevated
    G.submit("d2", action(kind=ActionKind.CHANGE_PRICE, amount_minor=0))  # subjective
    G.submit("d3", action(kind=ActionKind.SIGN_CONTRACT, amount_minor=1))  # irreversible
    queue = G.review_queue("c1")
    assert [row["id"] for row in queue] == ["d3", "d2", "d1"]


def test_auto_approved_decisions_do_not_reach_the_queue():
    G.submit("d1", action(amount_minor=100_00))
    assert G.review_queue("c1") == []


def test_queue_is_company_scoped():
    G.submit("d1", action(amount_minor=9_000_00, company_id="c1"))
    G.submit("d2", action(amount_minor=9_000_00, company_id="c2"))
    assert len(G.review_queue("c1")) == 1
    assert len(G.review_queue("c2")) == 1


def test_approving_removes_from_the_queue():
    d = G.submit("d1", action(amount_minor=9_000_00))
    assert len(G.review_queue("c1")) == 1
    G.approve(d, by="founder")
    assert G.review_queue("c1") == []


# ------------------------------------------------------------- persistence -----


def test_decision_is_persisted_with_its_state():
    d = G.submit("d1", action(amount_minor=9_000_00))
    row = G.get_decision_row("d1")
    assert row["state"] == str(DecisionState.PENDING_REVIEW)
    assert row["department"] == "marketing"
    G.approve(d, by="founder")
    assert G.get_decision_row("d1")["state"] == str(DecisionState.APPROVED)
    assert G.get_decision_row("d1")["decided_by"] == "founder"


def test_load_size_reports_human_decision_load():
    G.submit("d1", action(amount_minor=9_000_00))
    G.submit("d2", action(amount_minor=100_00))
    load = G.load_size()
    assert any("pending_review" in key for key in load)


# ------------------------------------------------------------- transitions -----


def test_illegal_transition_is_refused():
    d = G.submit("d1", action(amount_minor=9_000_00))
    with pytest.raises(IllegalTransition):
        G._transition(d, DecisionState.EXECUTED)  # skipping approval


def test_every_state_has_a_transition_entry():
    for state in DecisionState:
        assert state in G.LEGAL_TRANSITIONS


def test_terminal_states_have_no_successors():
    for terminal in (DecisionState.REJECTED, DecisionState.BLOCKED,
                     DecisionState.EXECUTED):
        assert G.LEGAL_TRANSITIONS[terminal] == frozenset()


def test_chain_description_marks_the_three_halting_stages():
    chain = G.describe_chain()
    halting = [s for s in chain if s["can_halt"] == "yes"]
    assert len(halting) == 3
    assert {s["stage"] for s in halting} == {
        str(Stage.REVIEW_QUEUE), str(Stage.APPROVAL_GATE),
        str(Stage.EXECUTION_GATE),
    }
