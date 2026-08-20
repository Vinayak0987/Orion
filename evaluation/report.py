"""Aggregate a sweep into the paper's results tables and a CSV export.

    python -m evaluation.report --label paper-run-1

Produces:
    results/<label>-metrics.csv      one row per (prompt, arm, metric)
    results/<label>-summary.csv      one row per (arm, metric) with mean and n
    results/<label>-report.md        the tables, ready to paste into the paper

Reporting rules that keep the conclusions honest:

* n is reported for every mean. Metrics skip prompts where they do not apply, so
  two arms can legitimately have different sample sizes and the reader must be
  able to see that.
* MAPE is flagged as lower-is-better, so a smaller number is not misread.
* While any benchmark in use is unsourced, F54 is printed with a PROVISIONAL
  banner rather than as a finished result.
* A metric with n < 3 is marked as insufficient rather than presented as a
  finding.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

from app.agents.benchmarks import load_benchmarks_csv
from app.db import sqlite
from evaluation import significance
from evaluation.metrics import (
    ALL_METRICS,
    COMPETITOR_COVERAGE,
    CONSISTENCY,
    FINANCIAL_ACCURACY,
    LOWER_IS_BETTER,
    PLAN_COMPLETENESS,
    ROUTING_EFFICIENCY,
    benchmark_caveat,
)

RESULTS_DIR = Path(__file__).parent / "results"
BENCHMARKS_FILE = Path(__file__).parent / "benchmarks.csv"

MIN_SAMPLE = 3

METRIC_LABEL = {
    FINANCIAL_ACCURACY: "Financial Accuracy (MAPE %, lower is better)",
    COMPETITOR_COVERAGE: "Competitor Coverage Rate (%)",
    PLAN_COMPLETENESS: "Plan Completeness (%)",
    CONSISTENCY: "Consistency Score (%)",
    ROUTING_EFFICIENCY: "Routing Token Saving (%)",
}

ARM_LABEL = {
    "multi_agent": "Multi-agent (dynamic routing)",
    "baseline": "Single-LLM baseline",
    "all_departments": "Multi-agent (all departments)",
    "no_grounding": "Multi-agent (no grounding)",
}


def _stats(scores: list[float]) -> dict:
    if not scores:
        return {"n": 0, "mean": None, "median": None, "stdev": None, "min": None, "max": None}
    return {
        "n": len(scores),
        "mean": round(statistics.fmean(scores), 2),
        "median": round(statistics.median(scores), 2),
        "stdev": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0.0,
        "min": round(min(scores), 2),
        "max": round(max(scores), 2),
    }


def collect(run_label: str) -> tuple[list[dict], dict[tuple[str, str], dict]]:
    rows = sqlite.fetch_metrics(run_label)
    grouped: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        if row["score"] is None:
            continue
        grouped.setdefault((row["approach"], row["metric"]), []).append(float(row["score"]))
    return rows, {key: _stats(scores) for key, scores in grouped.items()}


def write_metrics_csv(rows: list[dict], path: Path) -> None:
    """One row per measurement. This is the raw data behind every table."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["prompt_id", "arm", "metric", "score", "applicable", "reason", "sector", "scale", "prompt"]
        )
        for row in rows:
            details = json.loads(row["details_json"]) if row["details_json"] else {}
            writer.writerow(
                [
                    row["prompt_id"],
                    row["approach"],
                    row["metric"],
                    "" if row["score"] is None else row["score"],
                    details.get("applicable", ""),
                    details.get("reason", ""),
                    details.get("sector", ""),
                    details.get("scale", ""),
                    row["prompt_text"],
                ]
            )


def write_summary_csv(summary: dict[tuple[str, str], dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["arm", "metric", "n", "mean", "median", "stdev", "min", "max"])
        for (arm, metric), stats in sorted(summary.items()):
            writer.writerow(
                [arm, metric, stats["n"], stats["mean"], stats["median"], stats["stdev"], stats["min"], stats["max"]]
            )


def _cell(stats: dict | None) -> str:
    if not stats or stats["n"] == 0:
        return "—"
    marker = "" if stats["n"] >= MIN_SAMPLE else " ⚠"
    return f"{stats['mean']} (n={stats['n']}, sd={stats['stdev']}){marker}"


def _direction_note(metric: str) -> str:
    return "lower is better" if metric in LOWER_IS_BETTER else "higher is better"


def build_markdown(run_label: str, rows: list[dict], summary: dict[tuple[str, str], dict]) -> str:
    arms = sorted({row["approach"] for row in rows})
    prompt_count = len({row["prompt_id"] for row in rows})

    lines: list[str] = [
        f"# MABGP evaluation report — `{run_label}`",
        "",
        f"Prompts scored: **{prompt_count}** · arms: **{', '.join(arms)}** · "
        f"measurements: **{len(rows)}**",
        "",
    ]

    caveat = benchmark_caveat()
    if caveat:
        lines += [f"> **{caveat}**", ""]

    if any(stats["n"] < MIN_SAMPLE for stats in summary.values() if stats["n"] > 0):
        lines += [
            f"> ⚠ marks a mean computed from fewer than {MIN_SAMPLE} observations. "
            "Treat those as smoke-test output, not findings.",
            "",
        ]

    # --- RQ1 -------------------------------------------------------------
    lines += [
        "## RQ1 — Does the multi-agent pipeline beat a single-LLM baseline?",
        "",
        "| Metric | Direction | " + " | ".join(ARM_LABEL.get(a, a) for a in arms) + " |",
        "|---|---|" + "---|" * len(arms),
    ]
    for metric in ALL_METRICS:
        cells = " | ".join(_cell(summary.get((arm, metric))) for arm in arms)
        lines.append(f"| {METRIC_LABEL[metric]} | {_direction_note(metric)} | {cells} |")
    lines.append("")

    multi = {m: summary.get(("multi_agent", m)) for m in ALL_METRICS}
    base = {m: summary.get(("baseline", m)) for m in ALL_METRICS}
    if any(base.values()):
        lines += ["### Multi-agent vs baseline, per metric", ""]
        for metric in ALL_METRICS:
            left, right = multi.get(metric), base.get(metric)
            if not left or not right or left["n"] == 0 or right["n"] == 0:
                lines.append(f"- **{METRIC_LABEL[metric]}**: not comparable (missing data in one arm).")
                continue
            delta = round(left["mean"] - right["mean"], 2)
            better = (delta < 0) if metric in LOWER_IS_BETTER else (delta > 0)
            verdict = "multi-agent better" if better else "baseline better or equal"
            lines.append(
                f"- **{METRIC_LABEL[metric]}**: multi-agent {left['mean']} "
                f"vs baseline {right['mean']} (Δ {delta:+}) — {verdict}."
            )
        lines.append("")

    # --- RQ2 -------------------------------------------------------------
    lines += ["## RQ2 — Does dynamic routing improve efficiency without losing quality?", ""]
    routing_rows = [
        json.loads(row["details_json"])
        for row in rows
        if row["metric"] == ROUTING_EFFICIENCY and row["details_json"]
    ]
    scored = [r for r in routing_rows if r.get("applicable")]
    if not scored:
        lines += [
            "Not measured. Run both `multi_agent` and `all_departments` arms over the "
            "same prompts to populate this section.",
            "",
        ]
    else:
        skipping = [r for r in scored if r.get("routing_actually_skipped")]
        token_savings = [r["token_saving_pct"] for r in scored if r.get("token_saving_pct") is not None]
        time_savings = [r["time_saving_pct"] for r in scored if r.get("time_saving_pct") is not None]
        deltas = [r["quality_delta_pp"] for r in scored if r.get("quality_delta_pp") is not None]

        lines += [
            f"Prompt pairs: **{len(scored)}**, of which **{len(skipping)}** actually "
            "skipped a department (the rest are physical businesses where dynamic and "
            "control routing coincide, so a zero saving is the correct result).",
            "",
            "| Measure | Mean | n |",
            "|---|---|---|",
            f"| Token saving (%) | {round(statistics.fmean(token_savings), 2) if token_savings else '—'} | {len(token_savings)} |",
            f"| Time saving (%) | {round(statistics.fmean(time_savings), 2) if time_savings else '—'} | {len(time_savings)} |",
            f"| Completeness delta (pp) | {round(statistics.fmean(deltas), 2) if deltas else '—'} | {len(deltas)} |",
            "",
        ]
        if skipping:
            skip_tokens = [r["token_saving_pct"] for r in skipping if r.get("token_saving_pct") is not None]
            if skip_tokens:
                lines += [
                    f"Restricted to the {len(skipping)} prompts where routing actually "
                    f"skipped Operations, the mean token saving is "
                    f"**{round(statistics.fmean(skip_tokens), 2)}%**. This is the figure "
                    "to quote for RQ2; the all-prompt mean is diluted by prompts where "
                    "no skip was possible.",
                    "",
                ]
        if deltas:
            mean_delta = statistics.fmean(deltas)
            lines.append(
                f"Quality delta is {mean_delta:+.2f} pp. RQ2 is supported when the saving "
                "is positive and this delta is approximately zero or positive."
            )
            lines.append("")

    # --- RQ3 -------------------------------------------------------------
    lines += ["## RQ3 — Does real-world grounding improve accuracy over text-only?", ""]
    grounded = summary.get(("multi_agent", COMPETITOR_COVERAGE))
    ungrounded = summary.get(("no_grounding", COMPETITOR_COVERAGE))
    coverage_rows = [
        json.loads(row["details_json"])
        for row in rows
        if row["metric"] == COMPETITOR_COVERAGE and row["details_json"]
    ]
    with_truth = [r for r in coverage_rows if r.get("applicable")]

    if not with_truth:
        lines += [
            "**Not measurable yet.** Competitor Coverage needs hand-verified ground "
            "truth. Fill `ground_truth_competitors` in `evaluation/prompts.json` with "
            "the real businesses near each location, then re-run the report.",
            "",
            "Source breakdown observed so far (shows which arm the runs belong to):",
            "",
        ]
        sources: dict[str, int] = {}
        for row in coverage_rows:
            for source in row.get("sources") or []:
                sources[source] = sources.get(source, 0) + 1
        for source, count in sorted(sources.items()):
            lines.append(f"- `{source}`: {count} plan(s)")
        lines.append("")
    else:
        lines += [
            "| Arm | Coverage (%) | n |",
            "|---|---|---|",
            f"| Grounded (Places/OSM) | {_cell(grounded)} | {grounded['n'] if grounded else 0} |",
            f"| Text-only | {_cell(ungrounded)} | {ungrounded['n'] if ungrounded else 0} |",
            "",
        ]

    fin_grounded = summary.get(("multi_agent", FINANCIAL_ACCURACY))
    fin_ungrounded = summary.get(("no_grounding", FINANCIAL_ACCURACY))
    if fin_grounded and fin_ungrounded and fin_ungrounded["n"]:
        lines += [
            "Financial accuracy under the two grounding conditions "
            "(MAPE, lower is better):",
            "",
            f"- grounded: {_cell(fin_grounded)}",
            f"- text-only: {_cell(fin_ungrounded)}",
            "",
        ]

    # --- statistical significance ----------------------------------------
    if "multi_agent" in arms and "baseline" in arms:
        comparisons = significance.compare_all(rows, "multi_agent", "baseline")
        lines += significance.render_markdown(comparisons, METRIC_LABEL)

    # --- appendix --------------------------------------------------------
    lines += [
        "## Sample sizes",
        "",
        "| Arm | Metric | n | mean | median | sd | min | max |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for (arm, metric), stats in sorted(summary.items()):
        lines.append(
            f"| {arm} | {metric} | {stats['n']} | {stats['mean']} | {stats['median']} "
            f"| {stats['stdev']} | {stats['min']} | {stats['max']} |"
        )
    lines += [
        "",
        "## Unscored measurements",
        "",
        "Metrics record `applicable=false` with a reason rather than imputing a zero. "
        "Counts by reason:",
        "",
    ]
    reasons: dict[str, int] = {}
    for row in rows:
        if row["score"] is not None or not row["details_json"]:
            continue
        reason = json.loads(row["details_json"]).get("reason") or "unspecified"
        reasons[reason] = reasons.get(reason, 0) + 1
    if reasons:
        for reason, count in sorted(reasons.items(), key=lambda item: -item[1]):
            lines.append(f"- {count}× {reason}")
    else:
        lines.append("- none: every metric was applicable on every run")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate a MABGP evaluation sweep.")
    parser.add_argument("--label", required=True, help="run label used by the harness")
    args = parser.parse_args()

    sqlite.init_db()
    load_benchmarks_csv(BENCHMARKS_FILE)

    rows, summary = collect(args.label)
    if not rows:
        print(f"No results found for run label '{args.label}'.")
        print("Run the sweep first: python -m evaluation.harness --label <label>")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_csv = RESULTS_DIR / f"{args.label}-metrics.csv"
    summary_csv = RESULTS_DIR / f"{args.label}-summary.csv"
    report_md = RESULTS_DIR / f"{args.label}-report.md"

    write_metrics_csv(rows, metrics_csv)
    write_summary_csv(summary, summary_csv)
    report_md.write_text(build_markdown(args.label, rows, summary), encoding="utf-8")

    arms = {row["approach"] for row in rows}
    sig_json = None
    if "multi_agent" in arms and "baseline" in arms:
        sig_json = RESULTS_DIR / f"{args.label}-significance.json"
        significance.write_json(
            significance.compare_all(rows, "multi_agent", "baseline"), sig_json
        )

    print(f"measurements   {len(rows)}")
    print(f"raw CSV        {metrics_csv}")
    print(f"summary CSV    {summary_csv}")
    print(f"report         {report_md}")
    if sig_json:
        print(f"significance   {sig_json}")


if __name__ == "__main__":
    main()
