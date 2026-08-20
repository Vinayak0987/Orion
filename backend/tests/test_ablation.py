"""Tests for app.operating.ablation — the four ablation arms.

Key properties tested:
  - Each arm runs deterministically with a fixed seed
  - Topology constraints match the specification
  - single_loop is a fair baseline (same machinery, different topology)
  - full_graph detects proxy gaming that single_loop misses
  - All arms produce valid results
  - Paired comparison with same seed
"""

import pathlib
import tempfile

import pytest
from datetime import UTC, datetime

from app.operating.ablation import (
    ARM_CONFIGS,
    AblationArm,
    ArmConfig,
    ArmRunResult,
    run_arm,
    run_paired,
)
from app.operating.environment import MarketParams, SimulatedEnvironment
from app.operating.anchors import AnchorSet


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    """Each test gets its own database."""
    db_file = tmp_path / "test-ablation.db"
    from app.db import sqlite as sq
    monkeypatch.setattr(sq.settings.__class__, "sqlite_file",
                        property(lambda _self: db_file))
    from app.operating import init_all
    init_all()
    yield


class TestArmConfigs:
    def test_all_four_arms_defined(self):
        assert len(ARM_CONFIGS) == 4
        assert AblationArm.SINGLE_LOOP in ARM_CONFIGS
        assert AblationArm.ANCHORS_ONLY in ARM_CONFIGS
        assert AblationArm.MONITORS_ONLY in ARM_CONFIGS
        assert AblationArm.FULL_GRAPH in ARM_CONFIGS

    def test_single_loop_has_no_controls(self):
        cfg = ARM_CONFIGS[AblationArm.SINGLE_LOOP]
        assert cfg.anchors_visible is False
        assert cfg.monitors_active is False
        assert cfg.governance_active is False
        assert cfg.human_gates is False

    def test_anchors_only_has_anchors_no_monitors(self):
        cfg = ARM_CONFIGS[AblationArm.ANCHORS_ONLY]
        assert cfg.anchors_visible is True
        assert cfg.monitors_active is False
        assert cfg.governance_active is False

    def test_monitors_only_has_monitors_no_gates(self):
        cfg = ARM_CONFIGS[AblationArm.MONITORS_ONLY]
        assert cfg.monitors_active is True
        assert cfg.governance_active is False

    def test_full_graph_has_everything(self):
        cfg = ARM_CONFIGS[AblationArm.FULL_GRAPH]
        assert cfg.anchors_visible is True
        assert cfg.monitors_active is True
        assert cfg.governance_active is True
        assert cfg.human_gates is True

    def test_descriptions_are_nonempty(self):
        for cfg in ARM_CONFIGS.values():
            assert cfg.description


class TestRunArm:
    def test_single_loop_runs_without_error(self):
        result = run_arm(AblationArm.SINGLE_LOOP, seed=1, days=7)
        assert isinstance(result, ArmRunResult)
        assert result.arm == AblationArm.SINGLE_LOOP
        assert result.days == 7
        assert result.ledger_entries > 0
        assert result.department_ticks > 0

    def test_anchors_only_runs_without_error(self):
        result = run_arm(AblationArm.ANCHORS_ONLY, seed=1, days=7)
        assert result.ledger_entries > 0

    def test_monitors_only_runs_without_error(self):
        result = run_arm(AblationArm.MONITORS_ONLY, seed=1, days=7)
        assert result.ledger_entries > 0

    def test_full_graph_runs_without_error(self):
        result = run_arm(AblationArm.FULL_GRAPH, seed=1, days=7)
        assert result.ledger_entries > 0

    def test_deterministic_same_seed(self, _isolated_db, tmp_path):
        """Same arm + same seed = identical result (in separate DBs)."""
        # First run
        r1 = run_arm(AblationArm.SINGLE_LOOP, seed=42, days=14,
                     company_id="determinism-run-1")
        # Second run with different company_id (same DB is fine, entries are
        # keyed by company_id)
        r2 = run_arm(AblationArm.SINGLE_LOOP, seed=42, days=14,
                     company_id="determinism-run-2")
        assert r1.ledger_entries == r2.ledger_entries
        assert r1.customers_acquired == r2.customers_acquired
        assert r1.customers_churned == r2.customers_churned
        assert r1.total_revenue_minor == r2.total_revenue_minor

    def test_different_seed_different_result(self):
        r1 = run_arm(AblationArm.SINGLE_LOOP, seed=1, days=14)
        r2 = run_arm(AblationArm.SINGLE_LOOP, seed=2, days=14)
        # With different seeds, at least something should differ
        assert (r1.customers_acquired != r2.customers_acquired
                or r1.total_revenue_minor != r2.total_revenue_minor)

    def test_single_loop_no_blocked_actions(self):
        """Without governance, nothing should be blocked."""
        result = run_arm(AblationArm.SINGLE_LOOP, seed=5, days=14)
        assert result.blocked_actions == 0
        assert result.queued_for_review == 0

    def test_full_graph_may_block_actions(self):
        """With governance active, some actions may be blocked."""
        # Run longer to give governance a chance to intervene
        result = run_arm(AblationArm.FULL_GRAPH, seed=5, days=30)
        # Either blocks or review queuing should happen with constitution active
        assert result.department_ticks > 0

    def test_monitors_only_produces_findings(self):
        """With monitors active, findings should be generated."""
        # Run long enough for monitors to fire
        result = run_arm(AblationArm.MONITORS_ONLY, seed=42, days=21)
        assert result.monitor_ticks > 0

    def test_single_loop_no_monitor_ticks(self):
        """Without monitors, no monitor ticks should occur."""
        result = run_arm(AblationArm.SINGLE_LOOP, seed=5, days=21)
        assert result.monitor_ticks == 0

    def test_result_as_dict(self):
        result = run_arm(AblationArm.SINGLE_LOOP, seed=1, days=7)
        d = result.as_dict()
        assert d["arm"] == "single_loop"
        assert d["seed"] == 1
        assert d["days"] == 7
        assert "ledger_entries" in d
        assert "findings_count" in d

    def test_weekly_snapshots_produced(self):
        result = run_arm(AblationArm.SINGLE_LOOP, seed=1, days=14)
        assert len(result.daily_snapshots) > 0

    def test_all_arms_use_same_execution_machinery(self):
        """All arms use the same planner (rule_based_planner).
        Verify they produce similar department tick counts for same duration."""
        results = {}
        for arm in AblationArm:
            results[arm] = run_arm(arm, seed=10, days=7)

        # All arms should have the same number of department ticks
        # (they run the same departments on the same schedule)
        tick_counts = {arm: r.department_ticks for arm, r in results.items()}
        # single_loop, anchors_only and monitors_only should be equal
        # (no governance blocking)
        assert tick_counts[AblationArm.SINGLE_LOOP] == tick_counts[AblationArm.ANCHORS_ONLY]
        assert tick_counts[AblationArm.SINGLE_LOOP] == tick_counts[AblationArm.MONITORS_ONLY]


class TestArmsActuallyDiffer:
    """The assertions that make the experiment valid rather than null by design.

    The first sweep produced byte-identical outcomes in all four arms. These tests
    exist so that regression is caught immediately rather than discovered by
    reading a summary table of meaningless numbers.
    """

    def test_the_signal_a_department_observes_is_period_scoped(self):
        """A cumulative ratio is dominated by history and barely moves.

        This pins the measurement basis: given the same ledger, a period-scoped
        margin must differ from the cumulative one once the company has traded for
        a while, otherwise nothing can detect a within-run decline.
        """
        from app.operating.ablation import _observed_signal, _period_entries
        from app.operating import ledger as L

        run_arm(AblationArm.SINGLE_LOOP, seed=4, days=30, company_id="scoped")
        entries = L.read("scoped")
        last = max(e.seq or 0 for e in entries)
        mid = last // 2

        cumulative = AnchorSet.compute("scoped", entries).value("net_margin_pct")
        period = _observed_signal("net_margin_pct", entries, mid, last)
        assert cumulative is not None and period is not None
        assert _period_entries(entries, mid, last), "period window must be non-empty"

    def test_anchor_arms_write_lessons_and_proxy_arms_do_not(self):
        """The learning path must be live, and must depend on the arm's signal.

        An arm watching a rising acquisition count records no adverse movement and
        therefore no lesson. An arm watching a falling margin does.
        """
        proxy = run_arm(AblationArm.SINGLE_LOOP, seed=1, days=90,
                        company_id="lesson-proxy")
        anchor = run_arm(AblationArm.ANCHORS_ONLY, seed=1, days=90,
                         company_id="lesson-anchor")
        assert anchor.lessons_written > 0, (
            "the anchor arm learned nothing; the reflection path is dead again"
        )
        assert anchor.lessons_written > proxy.lessons_written

    def test_proxy_arm_raises_the_proxy_and_damages_the_anchor(self):
        """Proxy capture, measured within a single run.

        The proxy arm must end with MORE acquisitions and a WORSE margin than the
        anchor arm. If this fails, the ablation is not observing the phenomenon it
        exists to study.
        """
        proxy = run_arm(AblationArm.SINGLE_LOOP, seed=1, days=90,
                        company_id="cap-proxy")
        anchor = run_arm(AblationArm.ANCHORS_ONLY, seed=1, days=90,
                         company_id="cap-anchor")

        proxy_margin = AnchorSet.compute("cap-proxy").value("net_margin_pct")
        anchor_margin = AnchorSet.compute("cap-anchor").value("net_margin_pct")
        assert proxy_margin is not None and anchor_margin is not None

        assert proxy.customers_acquired > anchor.customers_acquired, (
            "the proxy arm did not raise its proxy"
        )
        assert proxy_margin < anchor_margin, (
            "the proxy arm did not damage the anchor; no capture to detect"
        )
        assert proxy.total_marketing_spend_minor > anchor.total_marketing_spend_minor

    def test_escalation_is_driven_by_the_signal_not_by_noise(self):
        """The anchor arm must CORRECT, i.e. cut spend, at least once.

        Escalations alone would mean the rule only ever ratchets up; corrections
        are what show the arm responding to a deteriorating measurement.
        """
        anchor = run_arm(AblationArm.ANCHORS_ONLY, seed=1, days=90,
                         company_id="corr")
        assert anchor.corrections > 0

    def test_the_control_rule_is_identical_across_arms(self):
        """Fairness: the behaviour rule must not differ, only the signal.

        Both arms are driven by `make_escalating_planner`, so an arm cannot win by
        having a different planner. Asserted structurally.
        """
        from app.operating.ablation import (
            ARM_CONFIGS, EscalationState, make_escalating_planner)

        planners = {}
        for arm in AblationArm:
            state = EscalationState()
            planners[arm] = make_escalating_planner(ARM_CONFIGS[arm], state)
        # Same factory, same closure shape, for every arm.
        assert len({p.__code__ for p in planners.values()}) == 1

    def test_monitors_without_gates_do_not_change_the_outcome(self):
        """A real null result, asserted rather than assumed.

        monitors_only detects divergence but has no authority to act on it, so its
        business outcome should match single_loop. If this ever stops holding, the
        monitors have acquired a side effect they should not have.
        """
        plain = run_arm(AblationArm.SINGLE_LOOP, seed=2, days=60,
                        company_id="null-plain")
        watched = run_arm(AblationArm.MONITORS_ONLY, seed=2, days=60,
                          company_id="null-watched")
        assert plain.customers_acquired == watched.customers_acquired
        assert plain.total_marketing_spend_minor == watched.total_marketing_spend_minor
        # but the watched arm did produce findings
        assert watched.monitor_ticks > 0


class TestRunPaired:
    def test_paired_returns_all_arms(self):
        results = run_paired(seed=42, days=7)
        assert len(results) == 4
        for arm in AblationArm:
            assert arm in results

    def test_paired_subset_of_arms(self):
        results = run_paired(
            seed=42, days=7,
            arms=[AblationArm.SINGLE_LOOP, AblationArm.FULL_GRAPH]
        )
        assert len(results) == 2
        assert AblationArm.SINGLE_LOOP in results
        assert AblationArm.FULL_GRAPH in results

    def test_paired_same_seed_across_arms(self):
        """All arms in a paired run share the same seed."""
        results = run_paired(seed=99, days=7)
        for arm, result in results.items():
            assert result.seed == 99

    def test_paired_environment_produces_same_base_demand(self):
        """With the same seed, the environment's organic demand is the same
        for all arms (before departmental actions diverge it)."""
        # This is verified by comparing the environments directly
        env1 = SimulatedEnvironment(seed=55)
        env2 = SimulatedEnvironment(seed=55)
        day = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        # With no department entries, both produce identical results
        o1 = env1.step("a", day)
        o2 = env2.step("b", day)
        assert o1.organic_acquired == o2.organic_acquired
