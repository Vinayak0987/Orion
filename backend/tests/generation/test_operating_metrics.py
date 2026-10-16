"""Tests for evaluation.operating_metrics — F59–F63.

Each metric is tested with fixture data of known answer. No LLM, no network.
"""

import pytest

# Research / evaluation harness � not the deployed app. Skipped by default;
# run with:  pytest -m research
pytestmark = pytest.mark.research

from evaluation.operating_metrics import (
    ALL_OPERATING_METRICS,
    CONFLICT_INCIDENT_RATE,
    DETECTION_LATENCY,
    HUMAN_DECISION_LOAD,
    LOWER_IS_BETTER_OPERATING,
    OBJECTIVE_STALENESS,
    PROXY_ANCHOR_DIVERGENCE,
    MetricResult,
    _spearman_rank_correlation,
    conflict_incident_rate,
    detection_latency,
    human_decision_load,
    objective_staleness,
    proxy_anchor_divergence,
    score_all,
)
from app.generation.operating.ablation import AblationArm, ArmRunResult


# ------------------------------------------------------------ Spearman helper --


class TestSpearmanRankCorrelation:
    def test_perfect_positive(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [10.0, 20.0, 30.0, 40.0, 50.0]
        rho = _spearman_rank_correlation(x, y)
        assert rho is not None
        assert abs(rho - 1.0) < 0.001

    def test_perfect_negative(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [50.0, 40.0, 30.0, 20.0, 10.0]
        rho = _spearman_rank_correlation(x, y)
        assert rho is not None
        assert abs(rho - (-1.0)) < 0.001

    def test_no_correlation(self):
        # Orthogonal sequence
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [3.0, 1.0, 4.0, 5.0, 2.0]
        rho = _spearman_rank_correlation(x, y)
        assert rho is not None
        assert -1.0 <= rho <= 1.0

    def test_too_few_values(self):
        assert _spearman_rank_correlation([1.0, 2.0], [3.0, 4.0]) is None

    def test_length_mismatch(self):
        assert _spearman_rank_correlation([1.0, 2.0, 3.0], [1.0, 2.0]) is None

    def test_tied_ranks(self):
        x = [1.0, 1.0, 3.0, 4.0, 5.0]
        y = [2.0, 2.0, 4.0, 5.0, 6.0]
        rho = _spearman_rank_correlation(x, y)
        assert rho is not None
        assert rho > 0.8  # strong positive with ties


# ------------------------------------------------------------ F59 divergence --


class TestProxyAnchorDivergence:
    def test_healthy_system_low_divergence(self):
        """When proxy and anchor move together, divergence is low (negative)."""
        snapshots = [
            {"customers_acquired": float(i * 10), "net_margin_pct": float(i * 2)}
            for i in range(8)
        ]
        result = proxy_anchor_divergence(snapshots)
        assert result.applicable
        assert result.score is not None
        # Positive correlation → negative divergence score
        assert result.score < 0

    def test_gaming_system_high_divergence(self):
        """When proxy goes up but anchor goes down, divergence is high."""
        snapshots = [
            {"customers_acquired": float(i * 10),
             "net_margin_pct": float(50.0 - i * 5)}
            for i in range(8)
        ]
        result = proxy_anchor_divergence(snapshots)
        assert result.applicable
        assert result.score is not None
        # Negative correlation → positive divergence score
        assert result.score > 0

    def test_insufficient_snapshots(self):
        snapshots = [{"customers_acquired": 10.0, "net_margin_pct": 30.0}]
        result = proxy_anchor_divergence(snapshots, window=4)
        assert not result.applicable

    def test_none_values_skipped(self):
        snapshots = [
            {"customers_acquired": None, "net_margin_pct": 30.0},
            {"customers_acquired": 10.0, "net_margin_pct": None},
            {"customers_acquired": 20.0, "net_margin_pct": 25.0},
        ]
        result = proxy_anchor_divergence(snapshots, window=3)
        assert not result.applicable  # not enough after filtering

    def test_custom_keys(self):
        snapshots = [
            {"cac": float(i * 5), "churn_pct": float(i * 3)}
            for i in range(6)
        ]
        result = proxy_anchor_divergence(
            snapshots, proxy_key="cac", anchor_key="churn_pct", window=3
        )
        assert result.applicable


# ------------------------------------------------------------ F60 latency -----


class TestDetectionLatency:
    def _make_result(self, arm: AblationArm, findings=None, days=90):
        return ArmRunResult(
            arm=arm, seed=1, days=days,
            findings=findings or [],
            monitor_ticks=12,
        )

    def test_no_monitors_not_applicable(self):
        result = self._make_result(AblationArm.SINGLE_LOOP)
        metric = detection_latency(result)
        assert not metric.applicable

    def test_no_findings_is_marked_censored(self):
        """No detection is a lower bound, not a measured latency."""
        result = self._make_result(AblationArm.MONITORS_ONLY, findings=[])
        metric = detection_latency(result, onset_day=7)
        assert metric.applicable
        assert metric.score == 90 - 7
        assert metric.details["censored"] is True

    def test_latency_uses_the_recorded_day_not_a_cadence_formula(self):
        """The regression this pins: latency must come from the finding's own
        recorded day. Inferring it from the finding's list index returned the same
        value for every seed and arm, with zero variance."""
        findings = [{"loop_id": "goodhart_detector", "findings": 1, "day": 20}]
        result = self._make_result(AblationArm.MONITORS_ONLY, findings=findings)
        metric = detection_latency(result, onset_day=7)
        assert metric.score == 13.0
        assert metric.details["first_finding_day"] == 20
        assert metric.details["censored"] is False

    def test_earliest_citing_finding_wins(self):
        findings = [
            {"loop_id": "goodhart_detector", "findings": 1, "day": 41},
            {"loop_id": "goodhart_detector", "findings": 2, "day": 13},
        ]
        result = self._make_result(AblationArm.FULL_GRAPH, findings=findings)
        metric = detection_latency(result, onset_day=7)
        assert metric.score == 6.0

    def test_only_goodhart_findings_count_as_detection(self):
        """A conflict finding is not a proxy-divergence citation."""
        findings = [{"loop_id": "conflict_detector", "findings": 3, "day": 13}]
        result = self._make_result(AblationArm.MONITORS_ONLY, findings=findings)
        metric = detection_latency(result, onset_day=7)
        assert metric.details["censored"] is True


# ------------------------------------------------------------ F61 conflict ----


class TestConflictIncidentRate:
    def _make_result(self, arm: AblationArm, findings=None, days=90):
        return ArmRunResult(
            arm=arm, seed=1, days=days,
            findings=findings or [],
            monitor_ticks=12,
        )

    def test_no_monitors_zero_rate(self):
        result = self._make_result(AblationArm.SINGLE_LOOP)
        metric = conflict_incident_rate(result)
        assert metric.score == 0.0

    def test_no_conflicts_zero_rate(self):
        findings = [{"loop_id": "goodhart_detector", "findings": 1}]
        result = self._make_result(AblationArm.MONITORS_ONLY, findings=findings)
        metric = conflict_incident_rate(result)
        assert metric.score == 0.0

    def test_conflicts_produce_positive_rate(self):
        findings = [
            {"loop_id": "conflict_detector", "findings": 2},
            {"loop_id": "conflict_detector", "findings": 1},
        ]
        result = self._make_result(AblationArm.MONITORS_ONLY, findings=findings, days=30)
        metric = conflict_incident_rate(result)
        assert metric.score is not None
        assert metric.score > 0
        assert metric.score == round(3 / 30, 4)


# ------------------------------------------------------------ F62 staleness ---


class TestObjectiveStaleness:
    def _make_result(self, arm: AblationArm, findings=None, days=90,
                     monitor_ticks=12, review_runs=0):
        return ArmRunResult(
            arm=arm, seed=1, days=days,
            findings=findings or [],
            monitor_ticks=monitor_ticks,
            objective_review_runs=review_runs,
        )

    def test_no_monitors_is_not_scored(self):
        """Unobserved is not the same as zero or one; refuse to impute."""
        result = self._make_result(AblationArm.SINGLE_LOOP)
        metric = objective_staleness(result)
        assert not metric.applicable
        assert metric.score is None

    def test_no_review_period_is_not_scored(self):
        result = self._make_result(AblationArm.MONITORS_ONLY, review_runs=0)
        metric = objective_staleness(result)
        assert not metric.applicable

    def test_no_stale_objectives_is_zero(self):
        findings = [{"loop_id": "objective_review", "findings": 0}]
        result = self._make_result(AblationArm.MONITORS_ONLY, findings=findings,
                                   review_runs=8)
        metric = objective_staleness(result)
        assert metric.applicable
        assert metric.score == 0.0

    def test_divides_by_recorded_review_runs(self):
        findings = [
            {"loop_id": "objective_review", "findings": 1},
            {"loop_id": "objective_review", "findings": 1},
        ]
        result = self._make_result(AblationArm.FULL_GRAPH, findings=findings,
                                   monitor_ticks=999, review_runs=8)
        metric = objective_staleness(result)
        # 2 stale out of 8 recorded review runs, NOT monitor_ticks // 4
        assert metric.score == 0.25
        assert metric.details["review_periods"] == 8


# ------------------------------------------------------------ F63 human load --


class TestHumanDecisionLoad:
    def _make_result(self, arm: AblationArm, queued=0, blocked=0, days=90):
        return ArmRunResult(
            arm=arm, seed=1, days=days,
            queued_for_review=queued,
            blocked_actions=blocked,
        )

    def test_no_governance_zero_load(self):
        result = self._make_result(AblationArm.SINGLE_LOOP)
        metric = human_decision_load(result)
        assert metric.score == 0.0

    def test_governance_with_no_blocks_zero_load(self):
        result = self._make_result(AblationArm.FULL_GRAPH, queued=0, blocked=0)
        metric = human_decision_load(result)
        assert metric.score == 0.0

    def test_governance_with_blocks(self):
        result = self._make_result(AblationArm.FULL_GRAPH, queued=10, blocked=5, days=30)
        metric = human_decision_load(result)
        assert metric.score == round(15 / 30, 4)

    def test_details_present(self):
        result = self._make_result(AblationArm.FULL_GRAPH, queued=6, blocked=3, days=90)
        metric = human_decision_load(result)
        assert metric.details["queued_for_review"] == 6
        assert metric.details["blocked_actions"] == 3
        assert metric.details["total_human_decisions"] == 9


# ------------------------------------------------------------ score_all -------


class TestScoreAll:
    def test_returns_five_results(self):
        result = ArmRunResult(
            arm=AblationArm.FULL_GRAPH, seed=1, days=30,
            findings=[{"loop_id": "goodhart_detector", "findings": 1}],
            monitor_ticks=4,
            blocked_actions=2,
            queued_for_review=3,
            daily_snapshots=[
                {"customers_acquired": float(i * 5), "net_margin_pct": float(30 - i)}
                for i in range(8)
            ],
        )
        metrics = score_all(result)
        assert len(metrics) == 5
        assert all(isinstance(m, MetricResult) for m in metrics)

    def test_all_metric_names_in_registry(self):
        assert len(ALL_OPERATING_METRICS) == 5
        assert PROXY_ANCHOR_DIVERGENCE in ALL_OPERATING_METRICS
        assert DETECTION_LATENCY in ALL_OPERATING_METRICS
        assert CONFLICT_INCIDENT_RATE in ALL_OPERATING_METRICS
        assert OBJECTIVE_STALENESS in ALL_OPERATING_METRICS
        assert HUMAN_DECISION_LOAD in ALL_OPERATING_METRICS

    def test_lower_is_better_set(self):
        # Human decision load is NOT in lower-is-better
        assert HUMAN_DECISION_LOAD not in LOWER_IS_BETTER_OPERATING
        assert PROXY_ANCHOR_DIVERGENCE in LOWER_IS_BETTER_OPERATING
