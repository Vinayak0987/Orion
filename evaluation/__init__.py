"""F53-F58 - evaluation and benchmarking harness.

    python -m evaluation.harness --all --label paper-run-1
    python -m evaluation.report --label paper-run-1
"""

from evaluation.baseline import baseline_model_name, generate_baseline
from evaluation.metrics import (
    ALL_METRICS,
    COMPETITOR_COVERAGE,
    CONSISTENCY,
    FINANCIAL_ACCURACY,
    PLAN_COMPLETENESS,
    ROUTING_EFFICIENCY,
    MetricResult,
    benchmark_caveat,
    competitor_coverage,
    consistency,
    financial_accuracy,
    plan_completeness,
    routing_efficiency,
    score_state,
)

__all__ = [
    "ALL_METRICS",
    "COMPETITOR_COVERAGE",
    "CONSISTENCY",
    "FINANCIAL_ACCURACY",
    "PLAN_COMPLETENESS",
    "ROUTING_EFFICIENCY",
    "MetricResult",
    "baseline_model_name",
    "benchmark_caveat",
    "competitor_coverage",
    "consistency",
    "financial_accuracy",
    "generate_baseline",
    "plan_completeness",
    "routing_efficiency",
    "score_state",
]
