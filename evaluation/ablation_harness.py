"""Ablation harness — runs the operating-layer experiment (RQ4–RQ7).

    python -m evaluation.ablation_harness --seeds 5 --days 90 --label ablation-v1

Runs all four arms on paired seeds, collects F59–F63, and outputs results
compatible with evaluation/significance.py and evaluation/report.py.

Each arm gets an independent database and environment instance seeded with the
same value.  Differences in outcome are attributable to control topology.

Output files:
  evaluation/results/<label>-ablation-metrics.csv   per-seed per-metric scores
  evaluation/results/<label>-ablation-summary.csv   arm-level aggregates
  evaluation/results/<label>-ablation-sweep.json    full run metadata

No LLM calls. No network. Fully offline and deterministic.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

# These imports require PYTHONPATH to include both backend/ and the repo root
from app.db import sqlite as sq
from app.operating import init_all
from app.operating.ablation import (
    ARM_CONFIGS,
    AblationArm,
    ArmRunResult,
    run_arm,
    run_paired,
)
from evaluation.operating_metrics import (
    ALL_OPERATING_METRICS,
    MetricResult,
    score_all,
)


EVALUATION_DIR = Path(__file__).parent
RESULTS_DIR = EVALUATION_DIR / "results"


@dataclass
class SweepConfig:
    """Configuration for one ablation sweep."""
    label: str
    seeds: list[int]
    days: int = 90
    arms: list[AblationArm] = field(default_factory=lambda: list(AblationArm))
    onset_day: int = 7  # when proxy gaming begins (known from env params)


@dataclass
class SeedResult:
    """All arm results for one seed."""
    seed: int
    arm_results: dict[str, ArmRunResult] = field(default_factory=dict)
    metrics: dict[str, list[MetricResult]] = field(default_factory=dict)
    duration_s: float = 0.0


def run_sweep(config: SweepConfig) -> list[SeedResult]:
    """Run the full ablation sweep.

    Each seed gets its own database.  Arms within a seed share nothing except
    the seed value (which determines the environment's stochastic sequence).
    """
    results: list[SeedResult] = []

    for seed in config.seeds:
        started = time.perf_counter()
        seed_result = SeedResult(seed=seed)

        for arm in config.arms:
            # Each arm gets its own isolated database
            db_file = Path(tempfile.mkdtemp()) / f"ablation-{arm}-seed{seed}.db"
            sq.settings.__class__.sqlite_file = property(lambda _s, f=db_file: f)
            init_all()

            arm_result = run_arm(arm, seed=seed, days=config.days)
            seed_result.arm_results[str(arm)] = arm_result

            # Score all operating metrics
            arm_metrics = score_all(arm_result, onset_day=config.onset_day)
            seed_result.metrics[str(arm)] = arm_metrics

        seed_result.duration_s = time.perf_counter() - started
        results.append(seed_result)

    return results


def write_metrics_csv(config: SweepConfig, results: list[SeedResult]) -> Path:
    """Write per-seed per-arm per-metric CSV compatible with significance.py."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{config.label}-ablation-metrics.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "seed", "arm", "metric", "score", "applicable", "reason",
        ])
        for sr in results:
            for arm_name, metrics in sr.metrics.items():
                for m in metrics:
                    writer.writerow([
                        sr.seed, arm_name, m.metric,
                        m.score if m.score is not None else "",
                        m.applicable, m.reason,
                    ])
    return path


def write_summary_csv(config: SweepConfig, results: list[SeedResult]) -> Path:
    """Write arm-level aggregate summary."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{config.label}-ablation-summary.csv"

    # Aggregate per arm per metric
    from collections import defaultdict
    scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for sr in results:
        for arm_name, metrics in sr.metrics.items():
            for m in metrics:
                if m.score is not None:
                    scores[arm_name][m.metric].append(m.score)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["arm", "metric", "n", "mean", "sd", "min", "max"])
        for arm_name in sorted(scores):
            for metric_name in ALL_OPERATING_METRICS:
                values = scores[arm_name].get(metric_name, [])
                if values:
                    n = len(values)
                    mean = sum(values) / n
                    sd = (sum((v - mean) ** 2 for v in values) / max(n - 1, 1)) ** 0.5
                    writer.writerow([
                        arm_name, metric_name, n,
                        f"{mean:.4f}", f"{sd:.4f}",
                        f"{min(values):.4f}", f"{max(values):.4f}",
                    ])
                else:
                    writer.writerow([arm_name, metric_name, 0, "", "", "", ""])
    return path


def write_sweep_json(config: SweepConfig, results: list[SeedResult]) -> Path:
    """Write full sweep metadata for reproducibility."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{config.label}-ablation-sweep.json"

    payload = {
        "label": config.label,
        "timestamp": datetime.now(UTC).isoformat(),
        "config": {
            "seeds": config.seeds,
            "days": config.days,
            "arms": [str(a) for a in config.arms],
            "onset_day": config.onset_day,
        },
        "summary": {
            "total_seeds": len(results),
            "total_arm_runs": sum(len(sr.arm_results) for sr in results),
            "total_duration_s": round(sum(sr.duration_s for sr in results), 1),
        },
        "per_seed": [
            {
                "seed": sr.seed,
                "duration_s": round(sr.duration_s, 1),
                "arms": {
                    arm_name: ar.as_dict()
                    for arm_name, ar in sr.arm_results.items()
                },
            }
            for sr in results
        ],
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def run_and_save(config: SweepConfig) -> tuple[list[SeedResult], dict[str, Path]]:
    """Run the sweep and write all output files."""
    results = run_sweep(config)
    files = {
        "metrics": write_metrics_csv(config, results),
        "summary": write_summary_csv(config, results),
        "sweep": write_sweep_json(config, results),
    }
    return results, files


# ------------------------------------------------------------------ CLI --------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Run the operating-layer ablation experiment (RQ4–RQ7)")
    ap.add_argument("--seeds", type=int, default=5,
                    help="Number of paired seeds to run (default: 5)")
    ap.add_argument("--days", type=int, default=90,
                    help="Simulated days per arm (default: 90)")
    ap.add_argument("--label", type=str, default="ablation-v1",
                    help="Run label for output files")
    ap.add_argument("--arms", nargs="*", default=None,
                    help="Specific arms to run (default: all four)")
    ap.add_argument("--onset-day", type=int, default=7,
                    help="Day when proxy gaming begins (for F60)")
    args = ap.parse_args(argv)

    arms = (
        [AblationArm(a) for a in args.arms]
        if args.arms else list(AblationArm)
    )
    seeds = list(range(1, args.seeds + 1))

    config = SweepConfig(
        label=args.label,
        seeds=seeds,
        days=args.days,
        arms=arms,
        onset_day=args.onset_day,
    )

    print(f"Ablation sweep: {len(seeds)} seeds × {len(arms)} arms × {args.days} days")
    print(f"Arms: {[str(a) for a in arms]}")
    print(f"Label: {args.label}")
    print()

    started = time.perf_counter()
    results, files = run_and_save(config)
    total_s = time.perf_counter() - started

    print(f"\nCompleted in {total_s:.1f}s")
    print(f"  Metrics CSV:  {files['metrics']}")
    print(f"  Summary CSV:  {files['summary']}")
    print(f"  Sweep JSON:   {files['sweep']}")
    print()

    # Print a quick summary table
    print(f"{'Arm':<16} {'Divergence':<12} {'Latency':<10} {'Conflicts':<12} "
          f"{'Staleness':<12} {'Load':<8}")
    print("-" * 72)
    for arm_name in [str(a) for a in arms]:
        arm_scores: dict[str, list[float]] = {}
        for sr in results:
            for m in sr.metrics.get(arm_name, []):
                if m.score is not None:
                    arm_scores.setdefault(m.metric, []).append(m.score)

        def mean_or_na(metric: str) -> str:
            vals = arm_scores.get(metric, [])
            return f"{sum(vals)/len(vals):.3f}" if vals else "N/A"

        print(f"{arm_name:<16} "
              f"{mean_or_na('proxy_anchor_divergence'):<12} "
              f"{mean_or_na('detection_latency_days'):<10} "
              f"{mean_or_na('conflict_incident_rate'):<12} "
              f"{mean_or_na('objective_staleness'):<12} "
              f"{mean_or_na('human_decision_load'):<8}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
