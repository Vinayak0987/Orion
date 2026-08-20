"""F10-F13 - Business Orchestrator.

Routing rules, execution DAG, parallel execution and session lifecycle.
"""

from app.orchestrator.completeness import (
    EXPECTED_FIELDS,
    MIN_SUBSTANTIVE_TEXT_LENGTH,
    SHORT_TEXT_FIELDS,
    TOTAL_EXPECTED_FIELDS,
    CompletenessReport,
    detect_contradictions,
    is_substantive,
    minimum_length_for,
    score_completeness,
)
from app.orchestrator.graph import build_graph, describe_graph
from app.orchestrator.progress import (
    ProgressCallback,
    ProgressEmitter,
    ProgressEvent,
    ProgressEventType,
)
from app.orchestrator.routing import (
    ALL_DEPARTMENTS,
    ALL_STAGES,
    RoutingDecision,
    resolve_departments,
)
from app.orchestrator.runner import (
    export_plan,
    new_session_id,
    orchestrate,
    run_summary,
    total_tokens,
)

__all__ = [
    "ALL_DEPARTMENTS",
    "ALL_STAGES",
    "EXPECTED_FIELDS",
    "MIN_SUBSTANTIVE_TEXT_LENGTH",
    "SHORT_TEXT_FIELDS",
    "TOTAL_EXPECTED_FIELDS",
    "CompletenessReport",
    "ProgressCallback",
    "ProgressEmitter",
    "ProgressEvent",
    "ProgressEventType",
    "RoutingDecision",
    "build_graph",
    "describe_graph",
    "detect_contradictions",
    "export_plan",
    "is_substantive",
    "minimum_length_for",
    "new_session_id",
    "orchestrate",
    "resolve_departments",
    "run_summary",
    "score_completeness",
    "total_tokens",
]
