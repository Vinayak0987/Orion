"""Tests for ExecutionPolicy (Planner Subsystem, Step 5). Pure, offline."""

from __future__ import annotations

import pytest

from app.generation.planning.policy import ExecutionPolicy, PolicyError, default_policy


def _policy(**overrides) -> ExecutionPolicy:
    base = {"max_tokens": 200_000, "max_repair_rounds": 1, "node_timeout_s": 30.0}
    base.update(overrides)
    return ExecutionPolicy(**base)


def test_valid_policy_passes_contract() -> None:
    p = _policy().runtime_contract()
    assert p.max_tokens == 200_000


def test_contract_fails_closed_on_missing_limit() -> None:
    p = _policy(max_tokens=None)
    with pytest.raises(PolicyError, match="missing limit"):
        p.runtime_contract()


def test_contract_rejects_nonpositive_limits() -> None:
    with pytest.raises(PolicyError, match="must be positive"):
        _policy(max_tokens=0).runtime_contract()
    with pytest.raises(PolicyError, match="must be positive"):
        _policy(node_timeout_s=-1.0).runtime_contract()


def test_policy_is_frozen() -> None:
    p = _policy()
    with pytest.raises(Exception):
        p.max_tokens = 5  # frozen dataclass - assignment must fail


def test_token_budget_deny_at_100_percent() -> None:
    p = _policy(max_tokens=1000)
    assert p.within_token_budget(999) is True
    assert p.within_token_budget(1000) is False
    assert p.within_token_budget(1500) is False


def test_token_warn_threshold_is_80_percent() -> None:
    assert _policy(max_tokens=1000).token_warn_threshold() == 800


def test_default_policy_builds_and_satisfies_contract() -> None:
    p = default_policy()
    assert p.max_tokens > 0
    assert p.max_repair_rounds >= 1
    assert p.node_timeout_s > 0
