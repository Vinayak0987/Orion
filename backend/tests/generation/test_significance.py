"""Tests for evaluation/significance.py (WORK_REMAINING §2.3).

Fixtures use small hand-checkable datasets so a wrong statistic fails loudly
rather than being confirmed by whatever the implementation happens to produce.

The suite stays offline: scipy is a local numerical library and opens no sockets.
"""

from __future__ import annotations

import json
import statistics

import pytest

# Research / evaluation harness � not the deployed app. Skipped by default;
# run with:  pytest -m research
pytestmark = pytest.mark.research

from evaluation import significance as sig
from evaluation.metrics import (
    CONSISTENCY,
    FINANCIAL_ACCURACY,
    PLAN_COMPLETENESS,
)

pytestmark = pytest.mark.skipif(
    not sig.scipy_available(), reason="scipy not installed"
)


def row(prompt_id: str, arm: str, metric: str, score: float | None) -> dict:
    return {
        "prompt_id": prompt_id,
        "approach": arm,
        "metric": metric,
        "score": score,
        "details_json": None,
        "prompt_text": f"prompt {prompt_id}",
    }


# --------------------------------------------------------------- pairing ------


def test_pairs_only_prompts_scored_in_both_arms():
    rows = [
        row("p01", "multi_agent", FINANCIAL_ACCURACY, 100.0),
        row("p01", "baseline", FINANCIAL_ACCURACY, 50.0),
        # p02 scored only in the treatment arm -> must not produce a pair
        row("p02", "multi_agent", FINANCIAL_ACCURACY, 120.0),
        # p03 present in both but the baseline refused to score -> no pair
        row("p03", "multi_agent", FINANCIAL_ACCURACY, 90.0),
        row("p03", "baseline", FINANCIAL_ACCURACY, None),
        row("p04", "multi_agent", FINANCIAL_ACCURACY, 80.0),
        row("p04", "baseline", FINANCIAL_ACCURACY, 40.0),
    ]
    ids, a, b = sig.paired_scores(rows, FINANCIAL_ACCURACY, "multi_agent", "baseline")
    assert ids == ["p01", "p04"]
    assert a == [100.0, 80.0]
    assert b == [50.0, 40.0]


def test_pairing_ignores_other_arms_and_metrics():
    rows = [
        row("p01", "multi_agent", FINANCIAL_ACCURACY, 10.0),
        row("p01", "baseline", FINANCIAL_ACCURACY, 20.0),
        row("p01", "no_grounding", FINANCIAL_ACCURACY, 999.0),
        row("p01", "multi_agent", CONSISTENCY, 100.0),
    ]
    ids, a, b = sig.paired_scores(rows, FINANCIAL_ACCURACY, "multi_agent", "baseline")
    assert ids == ["p01"]
    assert a == [10.0] and b == [20.0]


# ------------------------------------------------------- known-answer stats ---


def test_rank_biserial_all_positive_differences_is_plus_one():
    # every difference positive -> W- is zero -> r = +1
    assert sig._rank_biserial([1.0, 2.0, 3.0, 4.0]) == pytest.approx(1.0)


def test_rank_biserial_all_negative_differences_is_minus_one():
    assert sig._rank_biserial([-1.0, -2.0, -3.0]) == pytest.approx(-1.0)


def test_rank_biserial_symmetric_differences_is_zero():
    # ranks 1,2 positive and 1,2 negative -> W+ == W- -> r = 0
    assert sig._rank_biserial([1.0, 2.0, -1.0, -2.0]) == pytest.approx(0.0)


def test_rank_biserial_ignores_zero_differences():
    assert sig._rank_biserial([0.0, 0.0, 5.0]) == pytest.approx(1.0)


def test_rank_biserial_none_when_all_zero():
    assert sig._rank_biserial([0.0, 0.0]) is None


def test_average_ranks_handles_ties():
    # values 10,10,20 -> ranks 1.5, 1.5, 3
    assert sig._average_ranks([10.0, 10.0, 20.0]) == [1.5, 1.5, 3.0]


def test_cohens_d_paired_matches_hand_calculation():
    diffs = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    expected = statistics.fmean(diffs) / statistics.stdev(diffs)
    assert sig._cohens_d_paired(diffs) == pytest.approx(expected)


def test_cohens_d_none_when_no_variance_in_differences():
    assert sig._cohens_d_paired([3.0, 3.0, 3.0]) is None


# ------------------------------------------------------------- comparison -----


def _constant_offset_rows(metric: str, n: int, offset: float) -> list[dict]:
    """Treatment is exactly `offset` above baseline on every prompt.

    Every paired difference is identical, which makes the t-test undefined —
    deliberately, so the degenerate branch is exercised.
    """
    out = []
    for i in range(1, n + 1):
        pid = f"p{i:02d}"
        out.append(row(pid, "multi_agent", metric, 50.0 + i + offset))
        out.append(row(pid, "baseline", metric, 50.0 + i))
    return out


def _varying_offset_rows(metric: str, n: int, base_offset: float) -> list[dict]:
    """Treatment is above baseline by a varying amount, so both tests are defined."""
    out = []
    for i in range(1, n + 1):
        pid = f"p{i:02d}"
        jitter = (i % 4) * 1.5  # 0, 1.5, 3.0, 4.5 repeating - never all equal
        out.append(row(pid, "multi_agent", metric, 50.0 + i + base_offset + jitter))
        out.append(row(pid, "baseline", metric, 50.0 + i))
    return out


def test_identical_differences_make_t_undefined_but_wilcoxon_stands():
    rows = _constant_offset_rows(PLAN_COMPLETENESS, 12, offset=8.0)
    c = sig.compare(
        PLAN_COMPLETENESS, "multi_agent", "baseline",
        *sig.paired_scores(rows, PLAN_COMPLETENESS, "multi_agent", "baseline"),
    )
    assert c.testable
    assert c.t_undefined_reason is not None
    assert c.t_stat is None and c.t_p is None
    # Wilcoxon does not depend on the variance of the differences
    assert c.wilcoxon_p is not None and c.wilcoxon_p < 0.05


def test_varying_differences_define_both_tests():
    rows = _varying_offset_rows(PLAN_COMPLETENESS, 12, base_offset=6.0)
    c = sig.compare(
        PLAN_COMPLETENESS, "multi_agent", "baseline",
        *sig.paired_scores(rows, PLAN_COMPLETENESS, "multi_agent", "baseline"),
    )
    assert c.t_undefined_reason is None
    assert c.t_stat is not None and c.t_p is not None
    assert c.cohens_d is not None
    assert c.wilcoxon_p is not None


def test_undefined_t_is_surfaced_in_markdown():
    rows = _constant_offset_rows(PLAN_COMPLETENESS, 12, offset=8.0)
    comparisons = sig.compare_all(rows, metrics=(PLAN_COMPLETENESS,))
    md = "\n".join(sig.render_markdown(comparisons, {PLAN_COMPLETENESS: "Completeness"}))
    assert "undefined" in md
    assert "Wilcoxon is unaffected" in md


def test_no_infinities_reach_the_json_export(tmp_path):
    """Guards the actual defect: t = inf must never be written out."""
    import math

    rows = _constant_offset_rows(PLAN_COMPLETENESS, 12, offset=8.0)
    comparisons = sig.compare_all(rows, metrics=(PLAN_COMPLETENESS,))
    out = tmp_path / "sig.json"
    sig.write_json(comparisons, out)
    text = out.read_text(encoding="utf-8")
    assert "Infinity" not in text and "NaN" not in text
    payload = json.loads(text)
    for entry in payload:
        for key in ("t_stat", "t_p", "wilcoxon_p", "cohens_d"):
            value = entry.get(key)
            if isinstance(value, float):
                assert math.isfinite(value), f"{key} is not finite"


def test_consistent_offset_yields_significant_wilcoxon():
    rows = _constant_offset_rows(PLAN_COMPLETENESS, 12, offset=8.0)
    c = sig.compare(
        PLAN_COMPLETENESS,
        "multi_agent",
        "baseline",
        *sig.paired_scores(rows, PLAN_COMPLETENESS, "multi_agent", "baseline"),
    )
    assert c.testable
    assert c.n_pairs == 12
    assert not c.underpowered
    assert c.mean_diff == pytest.approx(8.0)
    # every difference is positive and identical -> maximal effect size
    assert c.rank_biserial == pytest.approx(1.0)
    assert c.wilcoxon_p < 0.05
    # higher-is-better metric, treatment higher -> favours treatment
    assert c.favours == "multi_agent"


def test_lower_is_better_direction_is_inverted():
    # treatment scores HIGHER MAPE, which is worse
    rows = _constant_offset_rows(FINANCIAL_ACCURACY, 12, offset=30.0)
    c = sig.compare(
        FINANCIAL_ACCURACY,
        "multi_agent",
        "baseline",
        *sig.paired_scores(rows, FINANCIAL_ACCURACY, "multi_agent", "baseline"),
    )
    assert c.mean_diff > 0
    assert c.favours == "baseline"


def test_identical_arms_are_not_tested():
    rows = _constant_offset_rows(PLAN_COMPLETENESS, 6, offset=0.0)
    c = sig.compare(
        PLAN_COMPLETENESS,
        "multi_agent",
        "baseline",
        *sig.paired_scores(rows, PLAN_COMPLETENESS, "multi_agent", "baseline"),
    )
    assert not c.testable
    assert "identical" in c.skipped_reason
    assert c.wilcoxon_p is None


def test_single_pair_is_not_tested():
    rows = _constant_offset_rows(PLAN_COMPLETENESS, 1, offset=5.0)
    c = sig.compare(
        PLAN_COMPLETENESS,
        "multi_agent",
        "baseline",
        *sig.paired_scores(rows, PLAN_COMPLETENESS, "multi_agent", "baseline"),
    )
    assert not c.testable
    assert "fewer than 2" in c.skipped_reason


def test_no_shared_prompts_is_not_tested():
    rows = [
        row("p01", "multi_agent", PLAN_COMPLETENESS, 90.0),
        row("p02", "baseline", PLAN_COMPLETENESS, 80.0),
    ]
    c = sig.compare(
        PLAN_COMPLETENESS,
        "multi_agent",
        "baseline",
        *sig.paired_scores(rows, PLAN_COMPLETENESS, "multi_agent", "baseline"),
    )
    assert not c.testable
    assert c.n_pairs == 0


def test_nine_pairs_flagged_underpowered_and_ten_is_not():
    nine = _constant_offset_rows(PLAN_COMPLETENESS, 9, offset=4.0)
    ten = _constant_offset_rows(PLAN_COMPLETENESS, 10, offset=4.0)
    c9 = sig.compare(
        PLAN_COMPLETENESS, "multi_agent", "baseline",
        *sig.paired_scores(nine, PLAN_COMPLETENESS, "multi_agent", "baseline"),
    )
    c10 = sig.compare(
        PLAN_COMPLETENESS, "multi_agent", "baseline",
        *sig.paired_scores(ten, PLAN_COMPLETENESS, "multi_agent", "baseline"),
    )
    assert c9.underpowered is True
    assert c10.underpowered is False
    assert sig.MIN_PAIRS_FOR_POWER == 10


def test_zero_differences_are_counted():
    rows = [
        row("p01", "multi_agent", PLAN_COMPLETENESS, 90.0),
        row("p01", "baseline", PLAN_COMPLETENESS, 90.0),
        row("p02", "multi_agent", PLAN_COMPLETENESS, 95.0),
        row("p02", "baseline", PLAN_COMPLETENESS, 80.0),
        row("p03", "multi_agent", PLAN_COMPLETENESS, 96.0),
        row("p03", "baseline", PLAN_COMPLETENESS, 82.0),
    ]
    c = sig.compare(
        PLAN_COMPLETENESS, "multi_agent", "baseline",
        *sig.paired_scores(rows, PLAN_COMPLETENESS, "multi_agent", "baseline"),
    )
    assert c.zero_diffs == 1
    assert c.n_pairs == 3


# ------------------------------------------------ real measured observations --


def test_paper_variance_observations_direction_favours_baseline():
    """The five multi-agent and three baseline MAPE values from PAPER.md §6.3.

    Only three prompts can pair, so this must come out UNDERPOWERED — the
    guard that stops the paper's strongest finding being over-claimed.
    """
    multi = [290.9, 129.1, 239.2]
    base = [51.7, 87.5, 50.0]
    rows = []
    for i, (m, b) in enumerate(zip(multi, base), start=1):
        rows.append(row(f"p{i:02d}", "multi_agent", FINANCIAL_ACCURACY, m))
        rows.append(row(f"p{i:02d}", "baseline", FINANCIAL_ACCURACY, b))
    c = sig.compare(
        FINANCIAL_ACCURACY, "multi_agent", "baseline",
        *sig.paired_scores(rows, FINANCIAL_ACCURACY, "multi_agent", "baseline"),
    )
    assert c.testable
    assert c.n_pairs == 3
    assert c.underpowered is True
    assert c.favours == "baseline"
    assert c.rank_biserial == pytest.approx(1.0)  # all diffs positive


# ---------------------------------------------------------------- rendering ---


def test_render_marks_underpowered_comparisons():
    rows = _constant_offset_rows(PLAN_COMPLETENESS, 4, offset=6.0)
    comparisons = sig.compare_all(rows, metrics=(PLAN_COMPLETENESS,))
    md = "\n".join(sig.render_markdown(comparisons, {PLAN_COMPLETENESS: "Completeness"}))
    assert "UNDERPOWERED" in md
    assert "not evidence either way" in md
    assert "Completeness" in md


def test_render_does_not_mark_powered_comparisons():
    rows = _constant_offset_rows(PLAN_COMPLETENESS, 14, offset=6.0)
    comparisons = sig.compare_all(rows, metrics=(PLAN_COMPLETENESS,))
    md = "\n".join(sig.render_markdown(comparisons, {PLAN_COMPLETENESS: "Completeness"}))
    assert "UNDERPOWERED" not in md
    assert "| ok |" in md


def test_render_lists_untestable_metrics_with_reasons():
    rows = [
        row("p01", "multi_agent", PLAN_COMPLETENESS, 90.0),
        row("p01", "baseline", PLAN_COMPLETENESS, 90.0),
    ]
    comparisons = sig.compare_all(rows, metrics=(PLAN_COMPLETENESS,))
    md = "\n".join(sig.render_markdown(comparisons, {}))
    assert "Not tested" in md or "No metric had enough" in md


def test_write_json_round_trips(tmp_path):
    rows = _constant_offset_rows(PLAN_COMPLETENESS, 11, offset=3.0)
    comparisons = sig.compare_all(rows, metrics=(PLAN_COMPLETENESS,))
    out = tmp_path / "sig.json"
    sig.write_json(comparisons, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload) == 1
    entry = payload[0]
    assert entry["metric"] == PLAN_COMPLETENESS
    assert entry["n_pairs"] == 11
    assert entry["underpowered"] is False
    assert entry["prompt_ids"][0] == "p01"


def test_compare_all_covers_every_metric():
    from evaluation.metrics import ALL_METRICS

    comparisons = sig.compare_all([])
    assert [c.metric for c in comparisons] == list(ALL_METRICS)
    assert all(not c.testable for c in comparisons)
