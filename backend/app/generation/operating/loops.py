"""Loop registry and topology validator.

A loop is a first-class object here, not an implicit control flow. Registering
one is checked against two invariants, and a topology that fails either is
refused before it can run.

**I1 — Termination.** Every cycle in the loop graph must contain at least one
node that is a code-computed anchor or a human decision.

    Rationale: a set of components that evaluate one another can converge on
    mutual agreement without converging on accuracy. Agent A approves B, B
    approves C, C approves A — three review steps, extensive documentation, and
    no point at which anything is compared against reality. That is not a graph
    of loops; it is one larger loop with more participants and more confidence.

**I2 — Independence.** A monitor loop may not share an evaluation signal with
the loop it monitors.

    Rationale: an auditor rewarded by the number it audits has no incentive to
    report that the number has been captured.

How I1 is decided
-----------------
Delete every anchor and human node from the graph. Any cycle that survives is,
by construction, a cycle containing no anchor and no human — so I1 holds exactly
when the residual graph is acyclic. The offending cycle is reported, because
"invalid topology" without a path is not actionable.

Neither invariant is claimed to be sufficient. Whether they are also *necessary*
is an open question, and the documents accompanying this work state it as such.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class LoopKind(StrEnum):
    EXECUTION = "execution"   # a department doing work
    MONITOR = "monitor"       # a loop that audits other loops
    LEARNING = "learning"     # reflection, knowledge evolution
    ANCHOR = "anchor"         # a code-computed measurement: terminates a cycle
    HUMAN = "human"           # a human decision: terminates a cycle


#: Node kinds that satisfy I1. Both are outside the agent runtime's authority:
#: an anchor is computed by code, a human decision is made by a person.
TERMINATING_KINDS: frozenset[LoopKind] = frozenset({LoopKind.ANCHOR, LoopKind.HUMAN})


class TopologyViolation(RuntimeError):
    """A loop graph failed an invariant. Carries the offending path."""

    def __init__(self, invariant: str, message: str, path: list[str] | None = None):
        detail = f" path: {' -> '.join(path)}" if path else ""
        super().__init__(f"[{invariant}] {message}{detail}")
        self.invariant = invariant
        self.path = path or []


@dataclass(frozen=True, slots=True)
class Loop:
    """One node in the control graph.

    Attributes:
        id: unique name.
        kind: what sort of node this is; determines whether it can terminate a
            cycle.
        sends_to: ids this loop passes work or signal to. These are the graph's
            directed edges.
        monitors: for a MONITOR, the loop ids it audits.
        evaluation_signal: the quantity this loop's success is judged by. Used by
            I2; two loops sharing a signal are not independent.
        cadence_seconds: how often it runs. None means event-driven.
    """

    id: str
    kind: LoopKind
    sends_to: tuple[str, ...] = ()
    monitors: tuple[str, ...] = ()
    evaluation_signal: str | None = None
    cadence_seconds: int | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("a loop needs an id")
        if self.monitors and self.kind is not LoopKind.MONITOR:
            raise ValueError(
                f"loop '{self.id}' declares monitors but is kind {self.kind}; "
                f"only a MONITOR may audit another loop"
            )
        if self.kind in TERMINATING_KINDS and self.evaluation_signal:
            raise ValueError(
                f"loop '{self.id}' is {self.kind} and must not carry an "
                f"evaluation signal: an anchor or human node is not judged by a "
                f"metric, which is what allows it to terminate a cycle"
            )


@dataclass
class LoopGraph:
    """A registry that refuses invalid topologies.

    Validation runs on `register`, so an invalid graph cannot be constructed
    incrementally and then discovered later at run time.
    """

    loops: dict[str, Loop] = field(default_factory=dict)
    validate_on_register: bool = True

    # ------------------------------------------------------------- registration

    def register(self, loop: Loop) -> Loop:
        if loop.id in self.loops:
            raise ValueError(f"loop '{loop.id}' is already registered")

        candidate = dict(self.loops)
        candidate[loop.id] = loop
        if self.validate_on_register:
            _validate(candidate, allow_dangling=True)
        self.loops[loop.id] = loop
        return loop

    def register_all(self, loops: list[Loop]) -> None:
        """Register a complete topology.

        Edges may point forward to loops not yet added, so per-step validation
        tolerates dangling references; the final check does not.
        """
        previous = self.validate_on_register
        self.validate_on_register = False
        try:
            for loop in loops:
                if loop.id in self.loops:
                    raise ValueError(f"loop '{loop.id}' is already registered")
                self.loops[loop.id] = loop
            self.validate()
        except Exception:
            for loop in loops:
                self.loops.pop(loop.id, None)
            raise
        finally:
            self.validate_on_register = previous

    def validate(self) -> None:
        _validate(self.loops, allow_dangling=False)

    # ------------------------------------------------------------------ queries

    def of_kind(self, kind: LoopKind) -> list[Loop]:
        return [l for l in self.loops.values() if l.kind is kind]

    def edges(self) -> list[tuple[str, str]]:
        return [
            (loop.id, target)
            for loop in self.loops.values()
            for target in loop.sends_to
        ]

    def cycles(self) -> list[list[str]]:
        """Every elementary cycle in the full graph."""
        return _find_cycles({k: v.sends_to for k, v in self.loops.items()})

    def unterminated_cycles(self) -> list[list[str]]:
        """Cycles containing no anchor and no human node — I1 violations."""
        residual = {
            k: tuple(t for t in v.sends_to
                     if self.loops.get(t) is None
                     or self.loops[t].kind not in TERMINATING_KINDS)
            for k, v in self.loops.items()
            if v.kind not in TERMINATING_KINDS
        }
        return _find_cycles(residual)

    def describe(self) -> dict:
        """Topology summary for the interface and for the paper's figure."""
        return {
            "loops": [
                {
                    "id": l.id,
                    "kind": str(l.kind),
                    "sends_to": list(l.sends_to),
                    "monitors": list(l.monitors),
                    "evaluation_signal": l.evaluation_signal,
                    "cadence_seconds": l.cadence_seconds,
                }
                for l in self.loops.values()
            ],
            "cycles": self.cycles(),
            "unterminated_cycles": self.unterminated_cycles(),
            "valid": not self.unterminated_cycles(),
        }


# ------------------------------------------------------------------ validation --


def _validate(loops: dict[str, Loop], *, allow_dangling: bool) -> None:
    if not allow_dangling:
        _check_references(loops)
    _check_independence(loops)
    _check_termination(loops)


def _check_references(loops: dict[str, Loop]) -> None:
    for loop in loops.values():
        for target in loop.sends_to:
            if target not in loops:
                raise TopologyViolation(
                    "REFERENCES",
                    f"loop '{loop.id}' sends to unknown loop '{target}'",
                )
        for target in loop.monitors:
            if target not in loops:
                raise TopologyViolation(
                    "REFERENCES",
                    f"monitor '{loop.id}' audits unknown loop '{target}'",
                )


def _check_independence(loops: dict[str, Loop]) -> None:
    """I2 — a monitor may not share an evaluation signal with its subject."""
    for monitor in loops.values():
        if monitor.kind is not LoopKind.MONITOR:
            continue
        for subject_id in monitor.monitors:
            subject = loops.get(subject_id)
            if subject is None:
                continue  # caught by _check_references when not allowed
            if subject_id == monitor.id:
                raise TopologyViolation(
                    "I2_INDEPENDENCE",
                    f"monitor '{monitor.id}' audits itself",
                )
            if (
                monitor.evaluation_signal is not None
                and monitor.evaluation_signal == subject.evaluation_signal
            ):
                raise TopologyViolation(
                    "I2_INDEPENDENCE",
                    f"monitor '{monitor.id}' and its subject '{subject_id}' share "
                    f"the evaluation signal '{monitor.evaluation_signal}'. An "
                    f"auditor judged by the metric it audits has no incentive to "
                    f"report that the metric has been captured.",
                )


def _check_termination(loops: dict[str, Loop]) -> None:
    """I1 — every cycle must contain an anchor or a human node."""
    residual: dict[str, tuple[str, ...]] = {
        loop_id: tuple(
            t for t in loop.sends_to
            if t in loops and loops[t].kind not in TERMINATING_KINDS
        )
        for loop_id, loop in loops.items()
        if loop.kind not in TERMINATING_KINDS
    }
    cycles = _find_cycles(residual, first_only=True)
    if cycles:
        cycle = cycles[0]
        raise TopologyViolation(
            "I1_TERMINATION",
            "cycle contains no code-computed anchor and no human decision, so "
            "it can converge on agreement without reference to anything "
            "external. Route it through an anchor or a human review step.",
            path=cycle + [cycle[0]],
        )


def _find_cycles(
    adjacency: dict[str, tuple[str, ...]], *, first_only: bool = False
) -> list[list[str]]:
    """Elementary cycles by depth-first search.

    Iterative rather than recursive: a deep topology should not be limited by
    the interpreter's stack.
    """
    found: list[list[str]] = []
    seen_signatures: set[frozenset[str]] = set()

    for start in adjacency:
        stack: list[tuple[str, list[str]]] = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for neighbour in adjacency.get(node, ()):
                if neighbour == start and len(path) >= 1:
                    signature = frozenset(path)
                    if signature not in seen_signatures:
                        seen_signatures.add(signature)
                        found.append(list(path))
                        if first_only:
                            return found
                elif neighbour not in path and neighbour in adjacency:
                    stack.append((neighbour, path + [neighbour]))
    return found


# -------------------------------------------------------------- default graph --


def default_graph() -> LoopGraph:
    """Orion's operating topology.

    Five execution loops for the implemented departments, four monitor loops, one
    anchor node and one human node. Every cycle routes through the anchor or the
    human, which is what I1 requires.
    """
    graph = LoopGraph()
    graph.register_all(
        [
            Loop("anchors", LoopKind.ANCHOR,
                 sends_to=("goodhart_detector", "conflict_detector",
                           "drift_monitor", "objective_review"),
                 description="metrics derived from the append-only ledger"),
            Loop("human_review", LoopKind.HUMAN,
                 sends_to=("strategy", "finance", "branding", "marketing",
                           "operations"),
                 description="ratification, arbitration, subjective judgement"),

            # execution loops: each judged by its own departmental objective
            Loop("strategy", LoopKind.EXECUTION, sends_to=("anchors",),
                 evaluation_signal="strategy_objective", cadence_seconds=86_400),
            Loop("finance", LoopKind.EXECUTION, sends_to=("anchors",),
                 evaluation_signal="finance_objective", cadence_seconds=86_400),
            Loop("branding", LoopKind.EXECUTION, sends_to=("anchors",),
                 evaluation_signal="branding_objective", cadence_seconds=604_800),
            Loop("marketing", LoopKind.EXECUTION, sends_to=("anchors",),
                 evaluation_signal="marketing_objective", cadence_seconds=86_400),
            Loop("operations", LoopKind.EXECUTION, sends_to=("anchors",),
                 evaluation_signal="operations_objective", cadence_seconds=86_400),

            # monitor loops: judged by detection quality, never by what they audit
            Loop("goodhart_detector", LoopKind.MONITOR,
                 sends_to=("human_review",),
                 monitors=("marketing", "finance", "branding", "operations",
                           "strategy"),
                 evaluation_signal="detection_quality", cadence_seconds=86_400,
                 description="claim versus ledger"),
            Loop("conflict_detector", LoopKind.MONITOR,
                 sends_to=("human_review",),
                 monitors=("finance", "marketing", "operations"),
                 evaluation_signal="conflict_detection_quality",
                 cadence_seconds=86_400),
            Loop("drift_monitor", LoopKind.MONITOR,
                 sends_to=("human_review",),
                 monitors=("strategy", "finance"),
                 evaluation_signal="freshness_detection_quality",
                 cadence_seconds=604_800),
            Loop("objective_review", LoopKind.MONITOR,
                 sends_to=("human_review",),
                 monitors=("strategy", "marketing", "finance", "branding",
                           "operations"),
                 evaluation_signal="objective_fitness",
                 cadence_seconds=2_592_000),

            # learning loop: reads anchors, updates playbooks, never scores itself
            Loop("reflection", LoopKind.LEARNING, sends_to=("human_review",),
                 evaluation_signal="lesson_quality", cadence_seconds=604_800),
        ]
    )
    return graph
