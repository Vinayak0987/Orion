"""Paired significance testing for the evaluation sweep (WORK_REMAINING §2.3).

Arms are paired by `prompt_id`: every arm runs the same prompt set, so a
between-arm comparison is a paired design and an unpaired test would discard
that structure and lose power.

Two tests are reported for each metric:

* **Wilcoxon signed-rank** — the primary test. It assumes no particular
  distribution, which matters here because the multi-agent arm's financial
  accuracy is strongly right-skewed (PAPER.md §6.3 records observations of
  290.9, 129.1, 239.2, 96.8 and 38.4 on one prompt).
* **Paired t-test** — reported alongside for reference only, since a reader
  will expect it. It assumes approximately normal differences, which the
  variance finding gives us reason to doubt.

Effect sizes accompany both, because a p-value alone says nothing about
magnitude at these sample sizes.

Underpowered results are labelled rather than dressed up: a comparison with
fewer than `MIN_PAIRS_FOR_POWER` pairs reports its statistics but is marked
UNDERPOWERED and its p-value must not be read as evidence either way.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field

from evaluation.metrics import ALL_METRICS, LOWER_IS_BETTER

#: Below this many pairs a p-value is not interpretable and is labelled as such.
MIN_PAIRS_FOR_POWER = 10

#: Reported as unavailable rather than crashing, matching the optional-backend
#: pattern used for PDF export.
SCIPY_HINT = (
    "scipy is not installed. Add it with: pip install scipy==1.14.1 "
    "(already listed in backend/requirements.txt)."
)


def scipy_available() -> bool:
    try:
        import scipy.stats  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class PairedComparison:
    """One metric, one pair of arms."""

    metric: str
    arm_a: str
    arm_b: str
    n_pairs: int
    mean_a: float | None = None
    mean_b: float | None = None
    mean_diff: float | None = None
    # Wilcoxon signed-rank
    wilcoxon_stat: float | None = None
    wilcoxon_p: float | None = None
    rank_biserial: float | None = None
    # Paired t-test
    t_stat: float | None = None
    t_p: float | None = None
    cohens_d: float | None = None
    # Bookkeeping
    zero_diffs: int = 0
    skipped_reason: str | None = None
    t_undefined_reason: str | None = None
    prompt_ids: list[str] = field(default_factory=list)

    @property
    def testable(self) -> bool:
        return self.skipped_reason is None

    @property
    def underpowered(self) -> bool:
        return self.n_pairs < MIN_PAIRS_FOR_POWER

    @property
    def favours(self) -> str | None:
        """Which arm the observed direction favours, ignoring significance."""
        if self.mean_diff is None:
            return None
        if self.mean_diff == 0:
            return "neither"
        lower_better = self.metric in LOWER_IS_BETTER
        a_better = (self.mean_diff < 0) if lower_better else (self.mean_diff > 0)
        return self.arm_a if a_better else self.arm_b


def paired_scores(
    rows: list[dict],
    metric: str,
    arm_a: str,
    arm_b: str,
) -> tuple[list[str], list[float], list[float]]:
    """Extract prompt-aligned score pairs for one metric.

    A prompt contributes a pair only when *both* arms produced a score for that
    metric. Metrics deliberately refuse to impute (see evaluation/metrics.py), so
    unscored measurements are absent rather than zero, and pairing on presence is
    the correct behaviour.
    """
    by_arm: dict[str, dict[str, float]] = {arm_a: {}, arm_b: {}}
    for row in rows:
        if row["metric"] != metric:
            continue
        arm = row["approach"]
        if arm not in by_arm:
            continue
        if row["score"] is None:
            continue
        by_arm[arm][row["prompt_id"]] = float(row["score"])

    shared = sorted(set(by_arm[arm_a]) & set(by_arm[arm_b]))
    return (
        shared,
        [by_arm[arm_a][pid] for pid in shared],
        [by_arm[arm_b][pid] for pid in shared],
    )


def _average_ranks(values: list[float]) -> list[float]:
    """Ranks with ties averaged, 1-based."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = shared_rank
        i = j + 1
    return ranks


def _rank_biserial(diffs: list[float]) -> float | None:
    """Rank-biserial correlation, the effect size for Wilcoxon signed-rank.

    (W+ - W-) / (W+ + W-), computed from the ranks of |diff| over non-zero
    differences. Ranges -1..+1; sign follows the sign of the differences.
    """
    nonzero = [d for d in diffs if d != 0]
    if not nonzero:
        return None
    ranks = _average_ranks([abs(d) for d in nonzero])
    w_plus = sum(r for d, r in zip(nonzero, ranks) if d > 0)
    w_minus = sum(r for d, r in zip(nonzero, ranks) if d < 0)
    total = w_plus + w_minus
    if total == 0:
        return None
    return (w_plus - w_minus) / total


def _cohens_d_paired(diffs: list[float]) -> float | None:
    """Cohen's d for a paired design: mean(diff) / sd(diff)."""
    if len(diffs) < 2:
        return None
    sd = statistics.stdev(diffs)
    if sd == 0:
        return None
    return statistics.fmean(diffs) / sd


def compare(
    metric: str,
    arm_a: str,
    arm_b: str,
    prompt_ids: list[str],
    a_scores: list[float],
    b_scores: list[float],
) -> PairedComparison:
    """Run both paired tests on one metric. Never raises on degenerate input."""
    n = len(a_scores)
    result = PairedComparison(
        metric=metric, arm_a=arm_a, arm_b=arm_b, n_pairs=n, prompt_ids=list(prompt_ids)
    )
    if n == 0:
        result.skipped_reason = "no prompts scored in both arms"
        return result

    result.mean_a = round(statistics.fmean(a_scores), 2)
    result.mean_b = round(statistics.fmean(b_scores), 2)
    diffs = [a - b for a, b in zip(a_scores, b_scores)]
    result.mean_diff = round(statistics.fmean(diffs), 2)
    result.zero_diffs = sum(1 for d in diffs if d == 0)

    if n < 2:
        result.skipped_reason = "fewer than 2 pairs; no test is defined"
        return result
    if all(d == 0 for d in diffs):
        result.skipped_reason = "all paired differences are zero; arms are identical"
        return result
    if not scipy_available():
        result.skipped_reason = SCIPY_HINT
        return result

    from scipy import stats

    result.cohens_d = _cohens_d_paired(diffs)
    if result.cohens_d is not None:
        result.cohens_d = round(result.cohens_d, 3)
    result.rank_biserial = _rank_biserial(diffs)
    if result.rank_biserial is not None:
        result.rank_biserial = round(result.rank_biserial, 3)

    try:
        w = stats.wilcoxon(a_scores, b_scores, zero_method="wilcox")
        result.wilcoxon_stat = round(float(w.statistic), 3)
        result.wilcoxon_p = float(w.pvalue)
    except ValueError as exc:  # e.g. every difference is zero after filtering
        result.skipped_reason = f"Wilcoxon not computable: {exc}"
        return result

    # The paired t-test divides by the standard deviation of the differences.
    # When every difference is identical that denominator is zero, and scipy
    # returns inf with a precision-loss warning. Reporting "t = inf" would be
    # meaningless, so the t-test is recorded as undefined while Wilcoxon — which
    # is well defined here — still stands.
    if statistics.stdev(diffs) == 0:
        result.t_undefined_reason = (
            "all paired differences are identical, so the standard deviation of "
            "the differences is zero and t is undefined"
        )
    else:
        t = stats.ttest_rel(a_scores, b_scores)
        result.t_stat = round(float(t.statistic), 3)
        result.t_p = float(t.pvalue)
    return result


def compare_all(
    rows: list[dict],
    arm_a: str = "multi_agent",
    arm_b: str = "baseline",
    metrics: tuple[str, ...] | None = None,
) -> list[PairedComparison]:
    """Compare two arms across every metric."""
    return [
        compare(metric, arm_a, arm_b, *paired_scores(rows, metric, arm_a, arm_b))
        for metric in (metrics or ALL_METRICS)
    ]


# ----------------------------------------------------------------- rendering --


def _fmt_p(p: float | None) -> str:
    if p is None:
        return "—"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def _interpret_d(d: float | None) -> str:
    if d is None:
        return "—"
    a = abs(d)
    size = "negligible" if a < 0.2 else "small" if a < 0.5 else "medium" if a < 0.8 else "large"
    return f"{d:+.3f} ({size})"


def render_markdown(
    comparisons: list[PairedComparison],
    metric_label: dict[str, str],
) -> list[str]:
    """Markdown section for the generated report."""
    from evaluation.metrics import LOWER_IS_BETTER as _LB  # local, keeps import graph flat

    lines: list[str] = [
        "## Statistical significance — paired tests",
        "",
    ]
    if not scipy_available():
        lines += [f"**Not computed.** {SCIPY_HINT}", ""]
        return lines

    testable = [c for c in comparisons if c.testable]
    if not testable:
        lines += [
            "No metric had enough paired observations to test. Run both arms over "
            "the same prompt set first.",
            "",
        ]
        for c in comparisons:
            lines.append(f"- `{c.metric}`: {c.skipped_reason}")
        lines.append("")
        return lines

    arm_a = testable[0].arm_a
    arm_b = testable[0].arm_b
    lines += [
        f"Arms are paired by prompt, comparing **{arm_a}** against **{arm_b}**. Each "
        "test uses only the prompts that produced a score in both arms, so the pair "
        "count differs between metrics and is stated per row.",
        "",
        "Wilcoxon signed-rank is the primary test; the paired t-test is shown for "
        "reference and assumes approximately normal differences, which the variance "
        "finding gives reason to doubt.",
        "",
        "| Metric | Pairs | Mean A | Mean B | Wilcoxon W | p | Rank-biserial | "
        "t | p | Cohen's d | Power |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in comparisons:
        label = metric_label.get(c.metric, c.metric)
        if not c.testable:
            lines.append(
                f"| {label} | {c.n_pairs} | — | — | — | — | — | — | — | — | "
                f"not tested |"
            )
            continue
        power = "UNDERPOWERED" if c.underpowered else "ok"
        t_cell = "undefined" if c.t_undefined_reason else str(c.t_stat)
        t_p_cell = "—" if c.t_undefined_reason else _fmt_p(c.t_p)
        lines.append(
            f"| {label} | {c.n_pairs} | {c.mean_a} | {c.mean_b} | "
            f"{c.wilcoxon_stat} | {_fmt_p(c.wilcoxon_p)} | "
            f"{'—' if c.rank_biserial is None else f'{c.rank_biserial:+.3f}'} | "
            f"{t_cell} | {t_p_cell} | {_interpret_d(c.cohens_d)} | {power} |"
        )
    lines.append("")

    undefined_t = [c for c in comparisons if c.t_undefined_reason]
    if undefined_t:
        lines += ["Where the t-test is undefined:", ""]
        for c in undefined_t:
            lines.append(
                f"- `{c.metric}`: {c.t_undefined_reason}. Wilcoxon is unaffected "
                "and is reported above."
            )
        lines.append("")

    under = [c for c in testable if c.underpowered]
    if under:
        lines += [
            f"> **{len(under)} of {len(testable)} comparisons have fewer than "
            f"{MIN_PAIRS_FOR_POWER} pairs.** Their statistics are printed for "
            "completeness, but a p-value at this sample size is not evidence either "
            "way — neither of an effect nor of its absence. Do not quote them.",
            "",
        ]

    skipped = [c for c in comparisons if not c.testable]
    if skipped:
        lines += ["Not tested:", ""]
        for c in skipped:
            lines.append(f"- `{c.metric}`: {c.skipped_reason}")
        lines.append("")

    lines += ["### Reading these results", ""]
    for c in comparisons:
        if not c.testable:
            continue
        label = metric_label.get(c.metric, c.metric)
        direction = "lower is better" if c.metric in _LB else "higher is better"
        verdict = f"observed direction favours **{c.favours}**"
        if c.underpowered:
            note = (
                f"with only {c.n_pairs} pairs this is a direction, not a finding"
            )
        elif c.wilcoxon_p is not None and c.wilcoxon_p < 0.05:
            note = (
                f"Wilcoxon p={_fmt_p(c.wilcoxon_p)}, so the difference is unlikely "
                "under the null"
            )
        else:
            note = (
                f"Wilcoxon p={_fmt_p(c.wilcoxon_p)}, so the difference is not "
                "distinguishable from noise at this sample size"
            )
        lines.append(f"- **{label}** ({direction}): {verdict} — {note}.")
    lines.append("")
    return lines


def write_json(comparisons: list[PairedComparison], path) -> None:
    """Machine-readable export so figures and the paper cannot drift from this."""
    payload = [
        {
            "metric": c.metric,
            "arm_a": c.arm_a,
            "arm_b": c.arm_b,
            "n_pairs": c.n_pairs,
            "mean_a": c.mean_a,
            "mean_b": c.mean_b,
            "mean_diff": c.mean_diff,
            "wilcoxon_stat": c.wilcoxon_stat,
            "wilcoxon_p": c.wilcoxon_p,
            "rank_biserial": c.rank_biserial,
            "t_stat": c.t_stat,
            "t_p": c.t_p,
            "cohens_d": c.cohens_d,
            "zero_diffs": c.zero_diffs,
            "underpowered": c.underpowered if c.testable else None,
            "skipped_reason": c.skipped_reason,
            "t_undefined_reason": c.t_undefined_reason,
            "prompt_ids": c.prompt_ids,
        }
        for c in comparisons
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
