# Orion (mabgp) — Agent Planner Subsystem: Architecture & Development Plan

> **Implementation status (2026-09-12):** Steps 1–7 built and verified. The full
> offline suite is **1083 passing** (was 989; +94 planner tests), zero failures,
> socket guard intact. Shipped modules under `backend/app/planning/`:
> `plan_models.py`, `compile.py`, `plan_store.py`, `policy.py`, `executor.py`,
> `plan_api.py`; `init_planning()` now also creates the plan tables and
> `plan_api.router` is wired into `main.py`. Tests:
> `test_plan_models.py` (5), `test_plan_compile.py` (11), `test_plan_store.py` (10),
> `test_plan_policy.py` (7), `test_plan_executor.py` (5), `test_plan_api.py` (9).
> Remaining/optional: per-node incremental checkpointing during a run, bounded
> repair (`repair.py`), mid-run HITL (`waiting_for_input`), and the `#/plan`
> frontend.
>
> Implementation-oriented design, grounded in Orion's actual codebase and in code read
> from three reference repositories (MiroFish, AgentOS, AgentArea) plus current
> agent-planning research. This is **not** a generic explanation of AI planning —
> every recommendation cites a real file, class, or function and states whether it is
> reused, adapted, or rejected.
>
> Verified against: `backend/app/planning/{store,service,api}.py`,
> `backend/app/agents/registry.py`, `backend/app/orchestrator/{routing,graph,runner}.py`,
> `backend/app/llm/`, `backend/app/operating/`, `.kiro/steering/*` on 2026-09-11.

---

## 0. TL;DR — the one-paragraph answer

Orion already has the **front half** of a planner: `app/planning/` builds a persisted,
agent-granular, inspect-and-confirm *report* (`prompt → intent → routing → 21-agent
roster → readiness/blockers → confirm`). It does **not** yet have the **back half**: a
planner that (a) turns a confirmed report into an explicit **dependency DAG of typed
tasks**, (b) **executes** that DAG with per-node telemetry, budget enforcement, and
bounded validate-and-repair, (c) survives a crash via a **JSON checkpoint on the task
row**, and (d) can pause for **human approval** without a workflow engine. The three
repos converge on the same answer for a system of Orion's size: **model the plan as a
self-derived document + a task DAG (AgentOS's `enrich()` + research's DAG consensus);
run it with an in-process loop, not Temporal (AgentArea's `DirectTaskManager`); enforce
one fail-closed typed policy (AgentArea's `EffectivePolicy`); persist a checkpoint per
step in SQLite (AgentArea's `ContinueAsNewState`, minus Temporal); reuse Orion's own
`describe_all_departments()` as the plan source of truth (never re-derive topology).**
Reject everything built for multi-tenancy, distribution, payments, sandboxing, and
cross-vendor protocols — none of it applies to a single-node, offline, free-tier
research tool.

---

## 1. What Orion actually has today (verified, not assumed)

| Component | File | What it does | Gap for a full planner |
|---|---|---|---|
| Planning **report** store | `app/planning/store.py` | `planning_reports` table; status machine `ready→confirmed→executed`, `blocked` terminal, `expired` lazy-derived; `IllegalTransition` guard; no `pending` row ever stored | It stores a *report*, not a *plan of tasks*. No task rows, no dependencies, no execution state. |
| Report **builder** | `app/planning/service.py` | `build_report()` composes `classify_intent` → `resolve_departments` → `build_agent_roster` (flattened `DEPARTMENT_STAGES`) → `build_inferences` (provenance) → readiness `_blockers` → token estimate. **Reads** topology, never re-derives. | No decomposition beyond the fixed 21-agent roster; no replanning; no per-node execution; no budget enforcement at run time. |
| API | `app/planning/api.py` | `POST /planning/reports`, `GET …`, `POST …/confirm` — thin, all logic in service/store | No run endpoint owned by planning; run linkage is a `planning_report_id` on `/ws/generate` (phases.md Phase 5). |
| Topology source of truth | `app/agents/registry.py` `DEPARTMENT_STAGES`, `describe_all_departments()` | Canonical 21-agent / 5-department / staged tuples | **This is already Orion's HTN decomposition library** — see §4. |
| Execution engine | `app/orchestrator/{routing,graph,runner}.py` | `resolve_departments` → `build_graph` (LangGraph `StateGraph`, stage-2 fan-out) → `orchestrate` (`astream`) | This *is* the DAG executor. The planner should **plan onto it**, not replace it. |
| LLM | `app/llm/llm_client` | Groq→Gemini→Ollama chain, `health()`, JSON repair | Reused verbatim. No new LLM path. |
| Invariant | `app/operating/` | Anchors computed, never stored | The planner must **compute** its plan from topology, never let an LLM assert it — mirrors the anchor rule. |

**Key realisation:** Orion's generation layer is already a **plan-and-execute workflow**
in the Anthropic sense. `resolve_departments` is the *planner* (decides which of 21
agents run), `build_graph` is the *DAG compiler*, `orchestrate` is the *executor*. The
"Agent Planner Subsystem" is therefore **not a greenfield engine** — it is the layer
that makes that implicit plan **explicit, inspectable, replannable, budget-bounded, and
resumable**, reusing the executor that already exists.

---

## 2. The comparison matrix (grounded in code read from each repo)

Legend: ✅ strong/production-grade · ◑ partial/implicit · ❌ absent · 🔁 present but reject for Orion.

| Capability | MiroFish | AgentOS | AgentArea | **Recommended for Orion** |
|---|---|---|---|---|
| **Task decomposition** | ◑ LLM outline (`report_agent.plan_outline`), sub-query fan-out (`zep_tools._generate_sub_queries`), batched config gen | ◑ template-driven fixed sections (`buildRecommendedPlanner*`) | ◑ emergent from ReAct + `completion` tool (no explicit planner) | **Deterministic HTN from `DEPARTMENT_STAGES`** (Orion already has the decomposition library); LLM only refines *content*, never *topology* |
| **Planning (plan artifact)** | ◑ `ReportOutline` dataclass | ✅ `WorkspacePlan` self-derived document | ◑ `ExecutionPlanResult` (vestigial) | **`ExecutionPlan` document derived by `enrich()`** (AgentOS pattern) built from the confirmed report |
| **Replanning** | ❌ | ◑ re-`enrich` each turn (spec, not execution) | ◑ ReAct re-decides next action | **Bounded replan node**: on node failure, one LLM repair attempt, hard cap (research consensus #5); else mark node `failed`, continue independents |
| **DAG execution** | ❌ (linear hardcoded pipeline) | ❌ (delegates to OpenClaw) | ◑ Temporal workflow (deterministic) | **Reuse Orion's existing LangGraph `build_graph`** — already a staged DAG with fan-out; add a thin topological planner over it |
| **Parallel execution** | ◑ threads per platform | ◑ `Promise.all` advisors (read-only) | ✅ activities | **Reuse LangGraph stage-2 fan-out**; parallel for read-only, sequential for writes (AgentOS rule) |
| **Sequential/staged** | ✅ pipeline | ✅ deploy pipeline | ✅ workflow loop | **Reuse existing 3-stage order** (strategy→parallel→operations) |
| **ReAct loop** | ✅ `_generate_section_react` (bounded budget=5) | ◑ turn-level plan→reflect | ✅ `DirectTaskManager._execute` / `Agent._execute_agent_loop` | **Adopt bounded ReAct** *inside a single node* only (max_tool_calls cap), not at top level — keep the DAG deterministic |
| **Plan validation** | ◑ schema validate/normalize (`ontology_generator`) | ✅ `collectPlanBlockers`/`Warnings` + `readinessScore≥90` | ✅ `runtime_contract()` fail-closed | **Two-tier blockers vs warnings + numeric score** (AgentOS) — Orion **already has `_blockers`/`warnings`**; extend to per-node plan validation |
| **Plan repair** | ◑ truncated-JSON repair, rule fallback | ✅ patch-merge + re-enrich | ◑ retry activity | **Evaluator-optimizer with hard cap** (research); patch-based refinement (AgentOS #6) |
| **Execution monitoring** | ✅ tail JSONL as event stream (`_read_action_log`) | ✅ operation-progress tracker → NDJSON | ✅ `EventManager` + `task_events` | **Per-node telemetry → `task_events` + NDJSON over existing `/ws/generate`** (Orion already streams; extend event schema) |
| **HITL / approval** | ❌ | ✅ inspect-and-confirm + capability gate | ✅ `PendingEscalation` + `waiting_for_input` signal | **Pre-run: Orion's existing confirm. Mid-run: `PendingEscalation` row + `waiting_for_input` status + resume endpoint** (AgentArea, engine-free) — optional phase |
| **Governance / limits** | ◑ config constants (`MAX_TOOL_CALLS`) | ◑ size profiles (agent/workflow caps) | ✅ typed `EffectivePolicy`, resolved-once, fail-closed | **Adopt `ExecutionLimitsPolicy`+`TokenPolicy`+`BudgetPolicy` as ONE frozen dataclass**, single scope, missing dim = reject |
| **Budget/cost-aware** | ◑ per-section tool budget | ◑ size caps | ✅ `BudgetTracker`, `CostBudgetGuard` warn@80/deny@100, Decimal money | **Inline budget check after each LLM call** (`DirectTaskManager` pattern); count metered tools only; free-tier so budget = token/call caps, not $ |
| **Tool-aware** | ✅ tool registry + tolerant parser | ◑ typed patch (no free tools) | ✅ `BaseTool`+`ToolExecutor`+`filter_disclosed_tools` | **`BaseTool` registry + `filter_disclosed_tools`**; Orion's agents mostly ground via Serper/Places — model those as tools |
| **Dependency-aware** | ❌ (ID references only) | ❌ | ◑ implicit | **Explicit `depends_on` edges** in the plan (research consensus #3, #20) — the biggest genuine addition Orion needs |
| **Durable / crash recovery** | ◑ file state + reload `_load_*` | ◑ JSON plan on disk | ✅ `ContinueAsNewState` checkpoint | **JSON `state` column on the task/run row, written per node** (AgentArea idea, SQLite instead of Temporal) |
| **Long-running** | ✅ subprocess lifecycle + cleanup | ◑ 120s agent timeout | ✅ continue-as-new, 24h | **Not needed** at 60–90s runtime; keep timeout + checkpoint. Add `scheduled_at`-on-task only if scheduled runs are wanted |
| **Delegation / sub-agents** | ◑ interview dispatch | ◑ `allowEphemeralSubagents` (advisory) | ✅ delegation-as-subtask + budget inheritance | **Not needed v1**; if ever, use delegation-as-child-task (AgentArea), not A2A |
| **Events / audit** | ◑ JSONL logs | ◑ progress snapshots | ✅ append-only `audit_events` + `task_events`, same-txn | **`task_events` written in the SAME SQLite txn as the state update** (replaces Redis/outbox); reuse for RQ telemetry |
| **State model** | 🔁 scattered classvars + files | ✅ single self-derived doc | ✅ typed `AgentExecutionState` | **Single `ExecutionPlan` Pydantic doc + `enrich()`**; volatile handles rebuilt from SQLite |
| **Multi-tenancy / auth** | ❌ | ✅ product permissions | 🔁 OpenFGA/Keto ReBAC | 🔁 **Reject** — single-user localhost tool (Orion's existing posture) |
| **Durable engine (Temporal)** | ❌ | ❌ | 🔁 Temporal + worker | 🔁 **Reject** — SQLite checkpoint gives single-node crash safety |
| **Message broker** | 🔁 FS-polling IPC | ❌ | 🔁 Redis + Go event-service + outbox | 🔁 **Reject** — same-txn SQLite event insert |
| **Sandboxing** | ◑ subprocess groups | ◑ agent policy | 🔁 kata/gVisor/warmpool (Go) | 🔁 **Reject** — Orion runs no model-generated code |
| **Payments / wallet** | ❌ | ❌ | 🔁 x402/mpp | 🔁 **Reject** — free tiers only |
| **MCP tool hosting** | ❌ | ◑ tool catalog | 🔁 Go mcp-manager | 🔁 **Reject the manager**; if tools needed, in-process only |

---

## 3. What each repo taught us (the decisive lessons)

**MiroFish → the executor-side resilience toolkit.** No formal planner, but battle-tested
patterns Orion should lift for *node execution*: bounded ReAct with a per-node tool
budget (`report_agent._generate_section_react`, `MAX_TOOL_CALLS=5`), the
decompose→fan-out→dedup→synthesize idiom (`zep_tools._generate_sub_queries`), stepwise
generation with **per-node rule fallback** (`simulation_config_generator`), resilient
`chat_json` (fence/`<think>` strip, truncated-JSON repair), `retry_with_backoff` /
`call_batch_with_retry` (partial success), and the "tail an append-only log as an event
stream" monitoring pattern (`simulation_runner._read_action_log`). **Reject** its
`Project.status` linear-enum pipeline (the exact anti-pattern a planner replaces) and its
flat `Task` (no deps/subtasks). Orion already avoids most of this — but its LLM error
handling (`chat.py` JSON repair) is the same lineage and should be the model for node
output parsing.

**AgentOS → the plan-as-document discipline.** Its "planner" is a workspace *compiler*,
not an action engine, but the discipline is gold and **Orion already reimplements half of
it** (the `inferences` provenance in `service.build_inferences` *is* AgentOS's
`PlannerInference{confidence,status,rationale,sourceLabels}`). Adopt for the execution
plan: (1) a single self-derived document with an idempotent `enrich()` reducer — derived
fields (blockers, score, status, stage) are **never** set by hand; (2) two-tier
validation (`collectPlanBlockers` hard vs `collectPlanWarnings` soft) + a numeric
readiness gate; (3) patch-based LLM refinement (LLM returns a typed JSON diff, code merges
by id and re-enriches) instead of free-form regeneration; (4) graceful degradation to a
deterministic fallback on every LLM path; (5) the operation-progress template→tracker→
NDJSON pattern (Orion streams over `/ws/generate` already). **Reject** its regex bilingual
NLU, its monolithic 100 KB files (split into `models/enrich/validation/agents/progress`),
its "spawn 6 real agents to think" runtime, and — critically — do **not** copy its absence
of a DAG as a model for real execution.

**AgentArea → the engine-free runtime.** The single most important file for Orion is
`libs/tasks/direct_task_manager.py` (`DirectTaskManager`): it proves the **entire agent
loop, budget enforcement, and persistence work in-process with no workflow engine**. Lift:
the `Task` model + `update_status()` auto-timestamps + a *subset* of statuses
(`pending, running, waiting_for_input, blocked, completed, failed, cancelled`); the typed
**`EffectivePolicy`** with fail-closed `runtime_contract()` (resolved once, never loosened,
missing dimension = reject) — the top idea to steal; the gate pipeline simplified to
warn@80/deny@100; `decide_tool_action()` + `filter_disclosed_tools()`; **HITL via a
`PendingEscalation` row + `waiting_for_input` status + a resume endpoint**; the
`GoalProgressEvaluator` (deterministic "are we done?" with no LLM call); **crash recovery
via a serialized checkpoint (`ContinueAsNewState`) written to the task row per turn** —
in SQLite, not Temporal; append-only `task_events` written in the **same transaction** as
the state update (this replaces the entire Redis+Go+outbox stack); the
`WorkflowExecutor`/`TaskExecutorInterface` protocol so an in-process engine can later be
swapped for a queue without touching callers. **Reject** Temporal, the Go event-service,
OpenFGA/Keto, multi-tenancy, wallet/payments, the mcp-manager sandboxes, webhook/LLM
triggers, progressive tool disclosure, and A2A — all solve problems a single-node offline
tool does not have.

**Research → the guardrails on ambition.** The consensus is unambiguous and it validates
keeping Orion small: prefer **workflows over autonomous agents** for well-defined tasks
(Anthropic, *Building Effective Agents*); **separate planning from execution**
(plan-and-execute — plan once, execute cheap, replan on failure); model tasks as an
**explicit dependency DAG** with topological order and deterministic parallel aggregation;
make state durable via **checkpoints**; use **validate/repair (evaluator-optimizer) loops
with hard iteration caps**; **gate with guardrails + HITL interrupts**; **enforce budgets**
and right-size models; constrain the planner to **registered, mockable tools**; instrument
**per-node telemetry**; and above all **design for determinism/offline testing** (pin
models, gate side effects behind mockable tools, no wall-clock/random in state, snapshot
plans as golden fixtures). Classification that matters for Orion: plan-and-execute, DAG,
task-decomposition, replanning, plan-validation, execution-monitoring, HITL, budget/tool/
dependency-aware, durable = **PRODUCTION-PROVEN → adopt**. Reflexion, ToT, GoT, classical
HTN search, CAMEL = **RESEARCH → borrow ideas only** (Orion's HTN is a *fixed* library, not
a search). Event-driven runtimes (AutoGen) and A2A = **EXPERIMENTAL → skip**. LangGraph
(which Orion already uses) provides `StateGraph` + checkpoints + `interrupt()` — the exact
primitives this design leans on.

---

## 4. The insight that shapes everything: Orion's HTN library already exists

Classical HTN planning needs a *domain control library* — hand-authored decompositions of
high-level tasks into ordered subtasks. **Orion already has this**, and it is the project's
central invariant that it stays authoritative:

```
"generate business plan"                          (root task)
  └─ resolve_departments(intent)                   (method selection: which subtasks apply)
       ├─ strategy      → {market_research, competitive_analysis, location_intelligence}   stage 1
       │                  {business_planning, risk_analysis}                               stage 2
       ├─ finance       → {revenue_model, cost_structure} · {funding_strategy, pl_forecast}
       ├─ branding      → {brand_naming} · {brand_identity, brand_voice, visual_design}
       ├─ marketing     → {digital_plan, buyer_persona} · {campaign_plan, seo_content}
       └─ operations    → {supply_chain, staffing_plan, tech_stack} · {process_flow}   (skipped if digital)
```

`DEPARTMENT_STAGES` (registry.py) **is** the ordered decomposition; `resolve_departments`
**is** method selection (physical → 21 tasks, digital → 17); the intra-stage tuples
**are** the parallel/sequential ordering; the stage-2 fan-out and operations-join in
`build_graph` **are** the dependency edges. This is why the design.md steering doc already
insists "topology truth stays in `registry.py`; the planning package composes it and never
re-derives it," and why the anchor invariant applies: **the plan must be computed from the
topology, exactly as anchors are computed from the ledger — an LLM may refine content but
must never assert the plan structure.**

Consequence for the design: Orion does **not** need an LLM to "decompose the task." It
needs a component that **projects the existing HTN library into an explicit, typed,
dependency-aware `ExecutionPlan`**, then executes it on the LangGraph engine that already
exists, with the resilience/governance/monitoring layers the three repos proved out.

---

## 5. Target architecture — the Planner Subsystem

Additive to `app/planning/`, strictly layered, no operating-layer change, no frozen-field
rename, offline-testable. Split into small modules (AgentOS lesson: never one 100 KB file).

```
backend/app/planning/
  store.py            # EXISTS — planning_reports (report lifecycle)
  service.py          # EXISTS — build_report (report builder)
  api.py              # EXISTS — /planning/reports routes
  __init__.py         # EXISTS — init_planning()
  # ---- NEW: the planner subsystem ----
  plan_models.py      # ExecutionPlan, PlanNode, PlanEdge, NodeStatus (Pydantic)
  policy.py           # ExecutionPolicy (frozen) + runtime_contract() fail-closed   [AgentArea]
  compile.py          # compile_plan(report) -> ExecutionPlan  (HTN projection, deterministic) [Orion registry]
  enrich.py           # enrich(plan) -> ExecutionPlan  (idempotent reducer)          [AgentOS]
  validate.py         # blockers/warnings/readiness + topological/cycle check        [AgentOS + research]
  executor.py         # PlanExecutor protocol + LangGraphExecutor (wraps orchestrate) [AgentArea seam]
  monitor.py          # per-node telemetry -> plan_events (same-txn)                  [AgentArea+MiroFish]
  checkpoint.py       # serialize/restore plan state on the row (crash recovery)      [AgentArea]
  repair.py           # bounded evaluator-optimizer node repair (hard cap)            [research+MiroFish]
  plan_store.py       # execution_plans + plan_events tables (SQLite)
  plan_api.py         # /planning/plans routes (compile, get, run, resume)
```

### 5.1 Data model (`plan_models.py`) — the explicit DAG the codebase lacks

```python
class NodeStatus(str, Enum):            # subset of AgentArea's status set
    PENDING = "pending"; READY = "ready"; RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"     # HITL park (optional phase)
    COMPLETED = "completed"; FAILED = "failed"
    SKIPPED = "skipped"; BLOCKED = "blocked"

class PlanNode(BaseModel):
    id: str                              # == agent_id (market_research, …)
    department: str
    stage: int                           # from DEPARTMENT_STAGES
    execution: Literal["parallel","sequential"]
    tier: str; max_tokens: int           # copied from AgentSpec — NOT re-derived
    grounding: str | None                # serper / places / None (service._grounding_for)
    depends_on: list[str] = []           # EXPLICIT edges — the genuine new capability
    status: NodeStatus = NodeStatus.PENDING
    attempts: int = 0
    tokens_used: int = 0
    error: str | None = None

class ExecutionPlan(BaseModel):          # single self-derived document — AgentOS
    id: str
    report_id: str                       # links to a CONFIRMED planning_report
    prompt: str
    nodes: list[PlanNode]
    # derived — NEVER set by hand, always recomputed by enrich():
    stages: list[list[str]] = []         # topological levels
    blockers: list[str] = []
    warnings: list[str] = []
    readiness_score: int = 0
    status: Literal["draft","ready","running","paused","completed","partial","failed"] = "draft"
    # budget accounting:
    estimated_max_tokens: int = 0
    tokens_used: int = 0
    created_at: str; updated_at: str
```

`depends_on` is derived deterministically from `DEPARTMENT_STAGES` (a stage-N node depends
on all stage-<N nodes in its department; operations depends on all of stage 2 per
`build_graph`). It is stored explicitly so the DAG is inspectable, testable, and — later —
editable.

### 5.2 `compile.py` — HTN projection (the core, deterministic, no LLM)

```python
def compile_plan(report: dict) -> ExecutionPlan:
    """Project a CONFIRMED planning_report into an explicit ExecutionPlan.
    Deterministic: reuses report['agents'] (already a flattened DEPARTMENT_STAGES
    view from service.build_agent_roster). No LLM call. No topology re-derivation."""
    nodes = [_node_from_roster_entry(a) for a in report["agents"]]
    _wire_dependencies(nodes)          # stage-based edges + operations-join
    plan = ExecutionPlan(report_id=report["id"], prompt=report["prompt"], nodes=nodes, …)
    return enrich(plan)                # compute stages, blockers, score, status
```

This mirrors the anchor invariant: the plan is *computed*, never asserted. It reuses the
exact roster `service.build_agent_roster()` already produces, so there is one topology
source and zero duplication.

### 5.3 `policy.py` — one frozen, fail-closed limits object (AgentArea's best idea)

```python
@dataclass(frozen=True)
class ExecutionPolicy:
    max_model_turns: int          # per node ReAct cap (MiroFish MAX_TOOL_CALLS lineage)
    max_tool_calls_total: int
    max_tokens: int               # run token budget (free-tier proxy for $)
    max_repair_rounds: int        # hard cap on evaluator-optimizer (research #5)
    node_timeout_s: float
    def runtime_contract(self) -> "ExecutionPolicy":
        missing = [f for f in fields(self) if getattr(self, f.name) is None]
        if missing: raise PolicyError(f"missing limits: {missing}")  # FAIL CLOSED
        return self
```

Single scope (no workspace/agent/user merge — Orion has one user). Resolved once from
`settings`, immutable, never loosened. Offline-appropriate defaults, not AgentArea's
`$50/20M tokens`: e.g. `max_model_turns=3, max_tool_calls_total=50, max_tokens=200_000,
max_repair_rounds=1, node_timeout_s=30`. Missing dimension = reject (no silent fallback —
the same discipline as `_blockers` today).

### 5.4 `executor.py` — reuse the engine, don't build one

```python
class PlanExecutor(Protocol):                       # AgentArea's TaskExecutorInterface seam
    async def run(self, plan: ExecutionPlan, policy: ExecutionPolicy,
                  on_event: Callable[[PlanEvent], None]) -> ExecutionPlan: ...

class LangGraphExecutor:
    """Wraps the EXISTING app.orchestrator.runner.orchestrate — Orion already
    executes the staged DAG via astream. The planner adds: per-node status
    transitions, inline budget checks after each LLM call (DirectTaskManager
    pattern), checkpoint write per node, bounded repair on node failure."""
```

The planner does **not** re-implement graph execution. It drives the existing
`orchestrate()` (which already does stage fan-out and partial-result survival via
`astream(stream_mode="values")`), intercepting node boundaries to enforce policy, emit
events, and checkpoint. This is the plan-and-execute separation the research demands, with
Orion's proven executor as the "execute" half.

### 5.5 `enrich.py` / `validate.py` — AgentOS reducer + two-tier gate

`enrich(plan)` (idempotent) recomputes `stages` (topological levels via Kahn's algorithm),
detects cycles (a blocker), recomputes `blockers` (dangling `depends_on`, no ready node,
policy contract failure) and `warnings` (a node with no grounding that the report flagged,
force-all, etc.), the `readiness_score`, and `status`. Called after every mutation. This is
`enrichWorkspacePlan` transposed to Python, and it reuses the *shape* of Orion's existing
`_blockers`/`warnings` in `service.py`.

### 5.6 `checkpoint.py` — crash recovery without Temporal

After each node completes, serialize `{node statuses, tokens_used, attempts,
partial results}` to a `state_json` column on the `execution_plans` row, in the **same
SQLite transaction** as the `plan_events` insert. On restart, `SELECT` unfinished plans and
resume from the first non-`completed` node. This is `ContinueAsNewState` with SQLite as the
durable store — single-node crash safety, zero external infra (AgentArea's whole
Temporal+Redis stack collapses to one JSON column + WAL).

### 5.7 `monitor.py` / `plan_store.py` — events as audit + RQ telemetry

`plan_events` (append-only: `id, plan_id, node_id, event_type, data_json, created_at`),
written in the same txn as state changes (MiroFish's log-as-event-stream + AgentArea's
same-txn insert, minus the broker). Doubles as reproducible telemetry for the paper's RQs —
consistent with `AgentTrace` and the operating-layer `ledger` philosophy.

### 5.8 HITL mid-run (optional, later phase) — engine-free

If a node ever needs approval (not required for v1 generation, but the seam should exist):
write a `waiting_for_input` status + a pending row, stop the loop, return a resumable plan;
a `POST /planning/plans/{id}/resume` endpoint re-invokes the executor from the checkpoint.
This is AgentArea's `PendingEscalation`/signal pattern without Temporal signals. Orion's
*pre-run* approval already exists (the confirm step) — mid-run HITL is additive.

---

## 6. Phased development plan (dependency-ordered, each phase offline-testable)

Follows the house rules in `phases.md`: a regression test per change, full suite stays
offline (socket guard), no new dependencies, no frozen-field rename, English copy, nothing
costs money. Baseline: **989 tests passing**. Each phase ends with the phase tests + full
suite green.

| Phase | Deliverable | Key files | New tests | Reuses / Adopts |
|---|---|---|---|---|
| **P0** | Baseline verified; confirm `app/planning/` report flow is green | — | — | Orion existing |
| **P1** | `plan_models.py` + `compile.py`: deterministic HTN projection of a confirmed report → `ExecutionPlan` with explicit `depends_on` | plan_models, compile | roster→nodes, dependency wiring (21 vs 17), cycle-free, digital-skips-operations | Orion `registry`/`build_agent_roster`; AgentOS document; research DAG |
| **P2** | `enrich.py` + `validate.py`: idempotent reducer, topological `stages`, blockers/warnings/score, cycle detection | enrich, validate | enrich idempotency, Kahn levels, dangling-edge blocker, cycle blocker, score arithmetic | AgentOS `enrich`/`collectPlanBlockers` |
| **P3** | `policy.py`: frozen `ExecutionPolicy` + fail-closed `runtime_contract()`; wired from `settings` | policy | missing-dim rejection, never-loosen, offline defaults | AgentArea `EffectivePolicy` |
| **P4** | `plan_store.py`: `execution_plans` + `plan_events` tables; `init_planning()` extended | plan_store | create/get/list, same-txn event insert, decode defaults | Orion `store.py` house style; AgentArea events |
| **P5** | `executor.py` + `monitor.py`: `LangGraphExecutor` wrapping `orchestrate`, per-node status/events, inline budget check | executor, monitor | node status transitions, budget deny@100%, event emission, **all with a scripted/dead LLM provider (offline)** | AgentArea `DirectTaskManager` loop + gate; MiroFish monitoring |
| **P6** | `checkpoint.py`: state_json per node; resume unfinished plan | checkpoint | checkpoint roundtrip, resume-from-mid-DAG, partial-on-failure | AgentArea `ContinueAsNewState` |
| **P7** | `repair.py`: bounded evaluator-optimizer on node failure (hard cap, deterministic fallback) | repair | repair within cap, cap-exhausted → node failed + continue independents | research evaluator-optimizer; MiroFish rule fallback |
| **P8** | `plan_api.py`: `POST /planning/plans` (compile from confirmed report), `GET`, `POST …/run` (stream events over the existing `/ws/generate` transport), `POST …/resume` | plan_api | 201 shape, 409 unless report confirmed, stream events, resume | Orion `api.py` thin-route rule |
| **P9** | (optional) mid-run HITL: `waiting_for_input` + resume | checkpoint, plan_api | park + resume | AgentArea `PendingEscalation` |
| **P10** | Docs + acceptance: update `architecture.md`/`design.md`/`README`; golden-plan fixtures | docs, tests | golden ExecutionPlan snapshot (determinism) | research determinism rule |

**Acceptance invariants (must hold at P10):**
- Plan is **computed** from `DEPARTMENT_STAGES`, never LLM-asserted (mirrors anchor rule).
- Compile is deterministic: same confirmed report → byte-identical `ExecutionPlan` (golden fixture).
- Physical prompt → 21 nodes; digital → 17 + operations skipped; force-all → 21 + RQ2 warning.
- Policy contract fails closed on any missing limit; budget denies at 100%, warns at 80%.
- A killed process resumes from the SQLite checkpoint with no double-execution.
- Repair is hard-capped; exhausted repair marks the node `failed` and continues independent nodes.
- Full suite offline, socket guard intact, no new dependency, no frozen field renamed, no operating-layer change.

---

## 7. Explicit reject list (so scope never creeps)

Rejected with the repo that tempted it and the reason:

- **Temporal / durable workflow engine** (AgentArea) — SQLite checkpoint gives single-node crash safety; Temporal solves multi-node distribution Orion doesn't have.
- **Redis broker + Go event-service + transactional outbox** (AgentArea) — same-txn SQLite `plan_events` insert replaces it.
- **OpenFGA/Keto ReBAC, multi-tenancy, `workspace_id`** (AgentArea, AgentOS) — single-user localhost tool; one implicit scope.
- **Wallet / payments / x402** (AgentArea) — free tiers only; budget = token/call caps, no money.
- **mcp-manager sandboxes / kata / warmpool** (AgentArea) — Orion executes no model-generated code.
- **Webhook/LLM-condition triggers, Temporal schedules** (AgentArea) — if scheduled runs are ever wanted, `scheduled_at` on the row + APScheduler, not this.
- **A2A protocol, remote agent registration** (AgentArea) — self-contained; use in-process delegation-as-subtask if sub-agents ever needed.
- **Progressive tool disclosure, content-safety filters** (AgentArea) — pay off only with dozens of tools / untrusted multi-tenant input.
- **Regex bilingual NLU, self-provisioned 6-agent runtime, 100 KB monolith files** (AgentOS) — LLM patch refinement + module split instead.
- **`Project.status` linear-enum pipeline, flat `Task`, FS-polling IPC, string if/elif tool dispatch, hand-parsed tool calls, zh-domain coupling** (MiroFish) — the anti-patterns an explicit DAG + registry-driven tools replace.
- **Top-level open-ended ReAct / autonomous agent, ToT/GoT/Reflexion search** (research) — Orion is a *workflow*, not an autonomous agent; bounded ReAct only inside a node.

---

## 8. Why this is the best design for Orion specifically

1. **It reuses, not rebuilds.** Orion's `registry` (HTN library), `orchestrator`
   (DAG executor), `llm_client` (fallback chain), and `planning/service` (report +
   inferences) already implement most primitives the research calls production-proven.
   The subsystem adds only the genuinely missing pieces: explicit dependency edges, a
   self-derived execution-plan document, one fail-closed policy, per-node
   monitoring/checkpoint, and bounded repair.
2. **It honours every Orion invariant.** Plan computed-not-asserted (anchor rule);
   additive (no operating-layer change); offline-testable (executor tested with
   scripted/dead providers); locked stack (LangGraph + stdlib sqlite3, no new deps);
   frozen fields untouched; regression test per phase.
3. **It matches Orion's scale.** Every "overkill" column in the matrix maps to a
   distributed/multi-tenant/paid problem Orion does not have; the design takes the
   *patterns* those systems proved (in-process loop, typed policy, checkpoint, event
   log) and drops the infrastructure.
4. **It is defensible in the paper.** Deterministic compile + golden fixtures +
   append-only `plan_events` make the planner's behaviour reproducible and measurable —
   consistent with the project's empirical-honesty requirement and its existing
   `AgentTrace`/ablation telemetry.

---

### Appendix A — capability → source-file crosswalk (for implementers)

| Adopt this in Orion | Copy the pattern from | Do NOT copy |
|---|---|---|
| In-process node loop + inline budget check | AgentArea `direct_task_manager.py:DirectTaskManager._execute` | the Temporal path |
| Frozen fail-closed policy | AgentArea `governance/domain/policies.py:EffectivePolicy.runtime_contract` | 4-layer scope merge, ReBAC |
| `Task`/status + auto-timestamps | AgentArea `tasks/domain/models.py:AgentTask.update_status` | `workspace_id`, full status set |
| Checkpoint per step | AgentArea `execution/workflows/models.py:ContinueAsNewState` | continue-as-new / Temporal history |
| Same-txn event log | AgentArea `audit/models.py` + `tasks/domain/models.py:TaskEvent` | Redis/Go/outbox |
| Self-derived plan doc + `enrich()` | AgentOS `planner-core.ts:enrichWorkspacePlan` | 100 KB file, fixed domain schema |
| Two-tier blockers/warnings + score | AgentOS `planner-core.ts:collectPlanBlockers/Warnings/calculateReadinessScore` | regex NLU |
| Provenance inferences | AgentOS `PlannerInference` **(Orion already has it in `service.build_inferences`)** | — |
| Patch-based LLM refinement | AgentOS `planner.ts:applyPlannerAgentPatch` | free-form regeneration |
| Progress template→tracker→NDJSON | AgentOS `operation-progress.ts` **(Orion streams via `/ws/generate`)** | second WebSocket |
| Bounded ReAct per node | MiroFish `report_agent.py:_generate_section_react` | linear pipeline, flat Task |
| Resilient JSON / rule fallback | MiroFish `simulation_config_generator.py` **(Orion has it in `llm/chain.py`)** | zh prompts |
| Log-as-event-stream monitoring | MiroFish `simulation_runner.py:_read_action_log` | FS-polling IPC |
| HTN decomposition library | **Orion `agents/registry.py:DEPARTMENT_STAGES`** (already exists) | — |
| DAG executor | **Orion `orchestrator/graph.py:build_graph`** (already exists) | — |
| DAG / topological / dependency-aware / plan-validation / durable | research consensus (LangGraph, Anthropic, Temporal docs) | ToT/GoT/Reflexion search, A2A, event-driven runtime |
