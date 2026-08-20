"""Evaluation harness - runs the experimental arms and records every metric.

Four arms, mapping onto the three research questions:

    multi_agent        21 agents, dynamic routing, grounding on     RQ1 treatment
    baseline           one LLM call                                 RQ1 control
    all_departments    21 agents, routing forced off                RQ2 control
    no_grounding       21 agents, external APIs off                 RQ3 control

Usage:

    python -m evaluation.harness --arms multi_agent baseline --limit 5
    python -m evaluation.harness --all --label paper-run-1

Design constraints that matter for the results being trustworthy:

* Arms run sequentially per prompt, not per arm, so a provider outage affects all
  arms of that prompt equally rather than ruining one arm entirely.
* Results are written to SQLite after every prompt, so an interrupted sweep keeps
  what it already measured.
* Free-tier failures are recorded as failures, not retried indefinitely. A sweep
  that silently retried until it succeeded would understate real-world latency.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from app.agents.benchmarks import load_benchmarks_csv
from app.config import settings
from app.core.logging import configure_logging
from app.db import sqlite
from app.llm.chain import llm_client
from app.models.state import SharedBusinessState
from app.orchestrator import orchestrate
from evaluation.baseline import baseline_model_name, generate_baseline
from evaluation.metrics import (
    ROUTING_EFFICIENCY,
    MetricResult,
    routing_efficiency,
    score_state,
)

log = structlog.get_logger(__name__)

EVALUATION_DIR = Path(__file__).parent
PROMPTS_FILE = EVALUATION_DIR / "prompts.json"
BENCHMARKS_FILE = EVALUATION_DIR / "benchmarks.csv"
RESULTS_DIR = EVALUATION_DIR / "results"

ARM_MULTI_AGENT = "multi_agent"
ARM_BASELINE = "baseline"
ARM_ALL_DEPARTMENTS = "all_departments"
ARM_NO_GROUNDING = "no_grounding"

ALL_ARMS = (ARM_MULTI_AGENT, ARM_BASELINE, ARM_ALL_DEPARTMENTS, ARM_NO_GROUNDING)

ARM_PURPOSE = {
    ARM_MULTI_AGENT: "RQ1/RQ2/RQ3 treatment: full pipeline",
    ARM_BASELINE: "RQ1 control: single LLM call",
    ARM_ALL_DEPARTMENTS: "RQ2 control: dynamic routing disabled",
    ARM_NO_GROUNDING: "RQ3 control: external grounding disabled",
}


@dataclass(slots=True)
class PromptSpec:
    id: str
    prompt: str
    sector: str = ""
    scale: str = ""
    expect_operations: bool | None = None


@dataclass(slots=True)
class ArmOutcome:
    arm: str
    prompt_id: str
    state: SharedBusinessState | None
    duration_s: float
    error: str | None = None
    metrics: list[MetricResult] = field(default_factory=list)


def load_prompts(path: Path = PROMPTS_FILE) -> tuple[list[PromptSpec], dict[str, list[str]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    prompts = [
        PromptSpec(
            id=item["id"],
            prompt=item["prompt"],
            sector=item.get("sector", ""),
            scale=item.get("scale", ""),
            expect_operations=item.get("expect_operations"),
        )
        for item in payload["prompts"]
    ]
    truth = {
        key: value
        for key, value in (payload.get("ground_truth_competitors") or {}).items()
        if not key.startswith("_") and isinstance(value, list)
    }
    return prompts, truth


async def run_arm(arm: str, spec: PromptSpec, iteration: int = 1) -> ArmOutcome:
    """Execute one arm for one prompt. Never raises."""
    started = time.perf_counter()
    # Distinct session id per repeat so stored sessions do not overwrite.
    session_id = f"{arm}-{spec.id}" if iteration == 1 else f"{arm}-{spec.id}-r{iteration}"

    # RQ3 control: turn grounding off for the duration of this arm only.
    restore: tuple[bool, bool, bool] | None = None
    if arm == ARM_NO_GROUNDING:
        restore = (
            settings.enable_places_api,
            settings.enable_overpass,
            settings.enable_serper_api,
        )
        settings.enable_places_api = False
        settings.enable_overpass = False
        settings.enable_serper_api = False

    try:
        if arm == ARM_BASELINE:
            state = await generate_baseline(spec.prompt, session_id=session_id)
        else:
            state = await orchestrate(
                spec.prompt,
                session_id=session_id,
                force_all_departments=(arm == ARM_ALL_DEPARTMENTS),
                persist=True,
            )
        elapsed = time.perf_counter() - started
        return ArmOutcome(arm, spec.id, state, elapsed)

    except Exception as exc:  # noqa: BLE001 - a failed arm is a data point
        elapsed = time.perf_counter() - started
        log.warning("harness.arm_failed", arm=arm, prompt=spec.id, error=str(exc)[:250])
        return ArmOutcome(arm, spec.id, None, elapsed, error=str(exc)[:400])

    finally:
        if restore is not None:
            (
                settings.enable_places_api,
                settings.enable_overpass,
                settings.enable_serper_api,
            ) = restore


def record(
    run_label: str, spec: PromptSpec, outcome: ArmOutcome, iteration: int = 1
) -> None:
    """Persist an arm's metrics to SQLite (F60)."""
    for result in outcome.metrics:
        sqlite.record_metric(
            run_label=run_label,
            prompt_id=spec.id,
            prompt_text=spec.prompt,
            approach=outcome.arm,
            metric=result.metric,
            score=result.score if result.recorded else None,
            details={
                "applicable": result.applicable,
                "reason": result.reason,
                "sector": spec.sector,
                "scale": spec.scale,
                "duration_s": round(outcome.duration_s, 2),
                "iteration": iteration,
                "error": outcome.error,
                **result.details,
            },
        )


async def run_sweep(
    *,
    arms: list[str],
    run_label: str,
    limit: int | None = None,
    prompt_ids: list[str] | None = None,
    repeat: int = 1,
) -> dict:
    """Run the requested arms over the prompt set and record all metrics.

    `repeat` re-runs every prompt N times. Metrics are recorded once per run, so
    repeated observations of the same (prompt, arm) pair measure run-to-run
    variance rather than overwriting each other. This is what quantifies the
    variance-compounding effect the paper reports: a decomposed estimation chain
    is expected to be noisier than a single-step one, and noise is only visible
    across repeats of an identical input.
    """
    configure_logging()
    sqlite.init_db()
    load_benchmarks_csv(BENCHMARKS_FILE)

    prompts, ground_truth = load_prompts()
    if prompt_ids:
        wanted = set(prompt_ids)
        prompts = [spec for spec in prompts if spec.id in wanted]
    if limit is not None:
        prompts = prompts[:limit]

    log.info(
        "harness.starting",
        label=run_label,
        arms=arms,
        prompts=len(prompts),
        repeat=repeat,
        baseline_model=baseline_model_name(),
        cache=settings.enable_chroma_cache,
    )

    completed = 0
    failures: list[str] = []
    routing_pairs = 0

    for iteration in range(1, repeat + 1):
        for index, spec in enumerate(prompts, start=1):
            outcomes: dict[str, ArmOutcome] = {}

            for arm in arms:
                outcome = await run_arm(arm, spec, iteration=iteration)
                if outcome.state is not None:
                    outcome.metrics = score_state(outcome.state, ground_truth.get(spec.id))
                record(run_label, spec, outcome, iteration=iteration)
                outcomes[arm] = outcome

                if outcome.error:
                    failures.append(f"{spec.id}/{arm}: {outcome.error[:80]}")
                else:
                    completed += 1

                status = "failed" if outcome.error else outcome.state["metadata"].status.value
                log.info(
                    "harness.arm_done",
                    run=f"{iteration}/{repeat}",
                    prompt=f"{index}/{len(prompts)}",
                    id=spec.id,
                    arm=arm,
                    status=status,
                    seconds=round(outcome.duration_s, 1),
                    scores={
                        result.metric: result.score
                        for result in outcome.metrics
                        if result.recorded
                    },
                )

            # F58 needs both routing arms for the same prompt.
            dynamic = outcomes.get(ARM_MULTI_AGENT)
            control = outcomes.get(ARM_ALL_DEPARTMENTS)
            if dynamic and control and dynamic.state and control.state:
                efficiency = routing_efficiency(dynamic.state, control.state)
                sqlite.record_metric(
                    run_label=run_label,
                    prompt_id=spec.id,
                    prompt_text=spec.prompt,
                    approach=ARM_MULTI_AGENT,
                    metric=ROUTING_EFFICIENCY,
                    score=efficiency.score if efficiency.recorded else None,
                    details={
                        "applicable": efficiency.applicable,
                        "reason": efficiency.reason,
                        "expected_operations": spec.expect_operations,
                        "iteration": iteration,
                        **efficiency.details,
                    },
                )
                routing_pairs += 1

    summary = {
        "run_label": run_label,
        "arms": arms,
        "prompts": len(prompts),
        "repeat": repeat,
        "arm_runs_completed": completed,
        "arm_runs_failed": len(failures),
        "routing_pairs": routing_pairs,
        "failures": failures[:20],
    }
    log.info("harness.finished", **{k: v for k, v in summary.items() if k != "failures"})
    await llm_client.aclose()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MABGP evaluation sweep.")
    parser.add_argument(
        "--arms",
        nargs="+",
        choices=ALL_ARMS,
        default=[ARM_MULTI_AGENT, ARM_BASELINE],
        help="experimental arms to run",
    )
    parser.add_argument("--all", action="store_true", help="run every arm")
    parser.add_argument("--label", default=None, help="run label; defaults to a timestamp")
    parser.add_argument("--limit", type=int, default=None, help="first N prompts only")
    parser.add_argument("--prompts", nargs="+", default=None, help="specific prompt ids")
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="re-run every prompt N times, to measure run-to-run variance",
    )
    args = parser.parse_args()

    arms = list(ALL_ARMS) if args.all else args.arms
    label = args.label or f"run-{time.strftime('%Y%m%d-%H%M%S')}"

    summary = asyncio.run(
        run_sweep(
            arms=arms,
            run_label=label,
            limit=args.limit,
            prompt_ids=args.prompts,
            repeat=max(1, args.repeat),
        )
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{label}-sweep.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nSweep summary written to {path}")
    print(f"Build the report with: python -m evaluation.report --label {label}")


if __name__ == "__main__":
    main()
