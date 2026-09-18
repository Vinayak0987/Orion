# Design — Planning Report flow

> Kiro steering document. Full design of the additive flow:
> **prompt → persisted agent-granular plan → readiness/blocker report →
> confirm → run**. Grounded in the verified codebase; see `architecture.md`.

## 1. The gap today

`POST /intent` classifies a prompt and returns `execution_plan` from
`describe_graph()` (`graph.py:149`) — department stages only, computed fresh on
every call, never persisted. No endpoint enumerates the 21 agents (the topology
exists in code as `describe_all_departments()`, `registry.py:88`, but is not
surfaced or stored), nothing gates on provider/API availability, and nothing
asks the operator to confirm before `/generate` spends the full multi-agent
quota. The operator cannot see "what will run, in what order, on which
providers, with what degraded" before committing.

## 2. Goals

1. Persist an agent-granular execution plan per prompt — all 21 agents for
   physical or force-all runs; 17 active + skipped Operations for digital
   businesses.
2. A readiness verdict — `ready | blocked` — with hard blockers and soft
   warnings, computed from live provider/API/database state.
3. An explicit confirm step that precedes any run.
4. Report → session linkage, so a run is traceable to the plan it executed.
5. Fully offline-testable, additive, no new dependencies.

## 3. Non-goals

- No authentication (localhost research tool — the app's existing posture).
- No change to routing logic — this flow reports routing, it does not alter it.
- No plan editing or negotiation — v1 is inspect-and-confirm only.
- No operating-layer changes, no scheduler hooks.
- No reuse of the report's intent by the run (v1): `orchestrate()` owns
  classification and re-classifies. Cost: one extra STRUCTURED call (~600
  tokens) per run. Accepted; revisit only with a measured reason.

## 4. Operator flow and quota honesty

```
1. Operator submits a prompt on #/plan
2. POST /planning/reports        → report built + persisted (ready | blocked)
3. Operator reviews intent, departments, agents, estimates, blockers
4. POST /planning/reports/{id}/confirm → code-only revalidation → confirmed
5. Run streams over /ws/generate carrying planning_report_id → executed
```

| Step | LLM calls | Notes |
|---|---|---|
| Create report | at most 1 | intent classification only; 0 if all providers are down (keyword heuristic) |
| Confirm | 0 | revalidation reads provider health and pings the database |
| Run | 1 + N agents | N = 17 (digital) or 21 (physical / force-all); the report's intent is not reused |

The UI must state this plainly: building the report costs at most one
classification call; confirming is free; running costs the full pipeline. The
upper bound on completion tokens is `600 + Σ spec.max_tokens` over active
agents. Repair rounds and fallback retries are extra and excluded — every
estimate is a bound, not a prediction, and must be labelled as such.


## 5. Data model — `planning_reports` (new table)

A new table, not a `sessions` column: the report exists BEFORE any session,
and `sessions.plan_json` already means the finished business plan (F59). DDL
follows the `sqlite.py` house style (stdlib sqlite3, WAL, UTC ISO timestamps,
JSON columns, idempotent `CREATE TABLE IF NOT EXISTS`):

```sql
CREATE TABLE IF NOT EXISTS planning_reports (
    id              TEXT PRIMARY KEY,      -- uuid4().hex[:12], same shape as session ids
    raw_prompt      TEXT NOT NULL,
    intent_json     TEXT,                  -- BusinessIntent dump, or null
    intent_source   TEXT NOT NULL,         -- 'llm' | 'heuristic'
    status          TEXT NOT NULL,         -- ready | confirmed | executed | blocked | expired
    blockers_json   TEXT NOT NULL DEFAULT '[]',
    warnings_json   TEXT NOT NULL DEFAULT '[]',
    routing_json    TEXT,                  -- describe_graph(decision) verbatim
    agents_json     TEXT,                  -- agent-granular plan, §6
    active_departments   TEXT,             -- JSON list
    skipped_departments  TEXT,             -- JSON list
    estimated_agent_calls INTEGER NOT NULL DEFAULT 0,
    estimated_max_completion_tokens INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    confirmed_at     TEXT,
    confirmed_by     TEXT,
    executed_at      TEXT,
    executed_session_id  TEXT
);
CREATE INDEX IF NOT EXISTS idx_planning_created ON planning_reports(created_at DESC);
```

Status machine (enforced in the store's confirm/executed helpers, mirroring the
operating layer's `IllegalTransition` discipline):

```
ready --confirm--> confirmed --run completed--> executed
ready --24 h TTL--> expired   (computed lazily; no reaper process)
blocked                      (terminal: fix inputs or environment, then create a new report)
```

No `pending` row is ever stored — creation computes everything and inserts a
final `ready` or `blocked` row, so a report can never be observed half-built.
TTL is a module constant `REPORT_TTL_HOURS = 24` in `app/planning/service.py`
(promote to `Settings` only if operators ever need to tune it); `expired` is
derived from `created_at` at read and confirm time.

## 6. Report payload (API shape)

`intent` is the `BusinessIntent` dump. `routing` is `describe_graph(decision)`
verbatim — the same object `/intent` returns today, so the two surfaces stay
comparable. `agents` is the main new part: the flattened, ordered view of
`describe_all_departments()` filtered to ACTIVE departments, one entry per
agent, values read from that agent's `AgentSpec`:

```json
{
  "id": "9f1c0a2b7d3e",
  "status": "ready",
  "created_at": "2026-09-10T09:00:00+00:00",
  "expires_at": "2026-09-11T09:00:00+00:00",
  "prompt": "Ice cream shop in Andheri, Rs 15L budget",
  "intent": { "business_type": "ice_cream_shop", "...": "..." },
  "intent_source": "llm",
  "inferences": [
    { "label": "business_type", "value": "ice_cream_shop", "confidence": 0.9,
      "status": "inferred", "rationale": "LLM extraction",
      "sourceLabels": ["llm"] },
    { "label": "budget", "value": "Rs 15.0 L", "confidence": null,
      "status": "confirmed",
      "rationale": "parsed deterministically from 'Rs 15L'",
      "sourceLabels": ["budget_parser"] },
    { "label": "location_area", "value": "Andheri", "confidence": null,
      "status": "confirmed", "rationale": "gazetteer match on 'Andheri'",
      "sourceLabels": ["gazetteer"] },
    { "label": "sector", "value": "food_and_beverage", "confidence": null,
      "status": "inferred",
      "rationale": "LLM-suggested; keyword vote agrees ('ice cream')",
      "sourceLabels": ["llm", "keyword_vote"] }
  ],
  "routing": { "stages": ["..."], "active_departments": ["..."],
               "skipped_departments": [], "dynamic_routing": true,
               "routing_reason": "..." },
  "agents": [
    { "agent_id": "market_research", "department": "strategy",
      "feature": "F20", "department_stage": 1, "execution": "parallel",
      "tier": "reasoning", "max_tokens": 900, "grounding": "serper" },
    { "...": "20 more entries in execution order" }
  ],
  "estimates": { "intent_llm_calls": 1, "agent_llm_calls": 21,
                 "max_completion_tokens": 23400 },
  "blockers": [],
  "warnings": ["SERPER_API_KEY missing - market research (F39) will fall back to LLM-only"]
}
```

`estimates.max_completion_tokens` = `600` (the classifier's `max_tokens` cap)
+ Σ `spec.max_tokens` over active agents — an upper bound, labelled as one;
repairs and fallback retries are excluded. `grounding` says which external
source the agent would consult (`serper` for `market_research`,
`places`/`openstreetmap` via `select_provider()` for `competitive_analysis`)
or `null` for the other 19 agents. The 21-entry full-graph report and the
17-entry digital report both come from the same code path — the topology is
never duplicated.

`inferences` adapts the verified AgentOS planner pattern (`memory.md` §3) to
Orion's hybrid extraction: one entry per key intent field — `business_type`,
`budget`, `location_area`, `sector` — each with a `status`:

- `confirmed` — an exact deterministic layer resolved it (`budget_parser`
  regex, `gazetteer` locality match);
- `inferred` — a semantic layer supplied it (`llm` extraction or hint,
  `keyword_vote` / `keyword_fallback` heuristic);
- `needs-confirmation` — the field is unspecified (`unspecified_fields`).

`confidence` is copied from the intent for `business_type` (the only field
that carries one) and is `null` elsewhere. `rationale` and `sourceLabels`
are derived from the stored intent and prompt by re-running the
deterministic parsers (`find_locality`, `classify_sector`) — no extra LLM
call, no new column (§5): the array is recomputed at read time from
`intent_json` + `raw_prompt` + `intent_source`, so it can never disagree
with the stored intent.

## 7. Readiness rules

The system is designed to run with zero API keys (HOW_TO_RUN §0), so missing
external-API keys are degraded-mode warnings, NOT blockers. Hard blockers are
only the two conditions that make a run impossible:

| Verdict | Condition | Source of truth |
|---|---|---|
| **blocked** | every LLM provider unavailable (no Groq key, no Gemini key, Ollama unreachable) | `llm_client.health()` |
| **blocked** | database unreachable (cannot persist the run) | the `/health`-style `SELECT 1` ping |
| warning | Google Places missing → competitor grounding degrades (OSM fallback or LLM-only) | `settings.warnings()` |
| warning | Serper missing → market research falls back to LLM-only | `settings.warnings()` |
| warning | intent came from the keyword heuristic (low confidence) | provider availability snapshot |
| warning | prompt lacks budget / location area / sector (`unspecified_fields`) | `BusinessIntent` |
| warning | `force_all_departments` engaged → 21 agents, not 17 (RQ2 control arm spend) | request flag |

Warnings are surfaced verbatim from `settings.warnings()` plus the derived
ones above — the planning layer never invents its own health facts. The
unspecified-field warnings are derived one-to-one from the `inferences`
entries (§6) whose status is `needs-confirmation`, each contributing
`"prompt lacks {label} - {rationale}"`, so the operator-visible string and
the structured payload can never disagree. A `blocked` report still lists
the full plan (agents, estimates) so the operator can see what is being
gated and why.

## 8. API surface (`app/planning/api.py`, router pattern from `app/operating/api.py`)

| Route | Behaviour |
|---|---|
| `POST /planning/reports` `{prompt, force_all_departments?}` | build + persist; **201** with the full report; **422** on `PromptValidationError` |
| `GET /planning/reports?limit&offset` | list, summary fields only (id, status, prompt, created_at, agent count) |
| `GET /planning/reports/{id}` | full report; 404 unknown |
| `POST /planning/reports/{id}/confirm` `{by?}` | re-check blockers + TTL (no LLM calls); **200** confirmed report; **409** if `blocked`, expired, or already confirmed; 404 unknown |

Run linkage — `/ws/generate` request gains an OPTIONAL `planning_report_id`:
if present, validate exists + `confirmed` + not expired + prompt matches the
report's `raw_prompt`, else emit `{"event": "error", "kind": "planning"}` and
do not run (no quota spent). On a completed run, `mark_executed(id,
session_id)`. Absent field ⇒ today's behaviour, unchanged — backwards
compatible for the evaluation harness, which never sends it. `POST /generate`
stays untouched in v1 (report linkage is WebSocket-only; the HTTP path is
the harness's transport).

## 9. Frontend

New hash route `#/plan` (`App.jsx` `ROUTES` gains `"plan"`), placed first in
the nav. `api.js` gains a `planning` namespace (`createReport`, `reports`,
`report`, `confirm`) alongside `operating`. `PlanView` composes: a prompt
form (reuse `PromptForm`'s field styling), a readiness banner (blocked =
stop + blocker list; ready = proceed), the agent roster grouped by
orchestrator stage with per-agent tier/token badges, the estimate line with
its "upper bound" label, and a Confirm button that calls confirm then hands
off to `#/generate`, which starts `streamGeneration` carrying
`planning_report_id`. Copy is English, honest about cost (§4), and reuses
existing status/callout classes — no new visual language, no new
dependencies.

## 10. Testing strategy

All offline; the socket guard stays supreme. Store tests run against a
tmp-path database (the `test_api.py` `offline_api` fixture pattern). Service
tests script the LLM (`ScriptedProvider`/`DeadProvider` — no agent runners
are involved, so placeholders are unnecessary) and cover: ready/blocked, 21
vs 17 agents (physical vs digital prompt), force-all, estimate arithmetic,
heuristic warning; the four `inferences` entries (confirmed by a parser,
inferred via LLM or keyword vote, `needs-confirmation` when unspecified,
corroborated `sourceLabels`); and the §7 one-to-one mapping between
`needs-confirmation` inferences and unspecified-field warnings. API tests
use `TestClient` over the router. Linkage tests
reuse the `websocket_connect` pattern: confirm → run with placeholder
runners → assert `executed` + `executed_session_id`; and the rejection paths
(unknown id, blocked, expired, mismatched prompt). Every behaviour in §7 and
§8 gets at least one named test.

## 11. Alternatives considered and rejected

- **Reuse `sessions` / `plan_json`** — naming hazard (memory.md §4); planning
  precedes any session.
- **LLM-written narrative plan** — violates the project's own empirical
  principle, *derived figures override asserted ones* (operating layer §0):
  the plan must be computed from `DEPARTMENT_STAGES`, like anchors from the
  ledger.
- **A second WebSocket for planning** — one transport; `/ws/generate` stays
  the single run path (the separate operating-layer event bus is
  WORK_REMAINING §5.4, out of scope).
- **Reusing the report's intent at run time** — deferred (§3); one extra
  classification call is cheap and keeps `orchestrate()` unmodified.
- **Plan editing / negotiation, auth, background TTL reaper** — v1
  non-goals; lazy expiry keeps the system reaper-free like the rest of the
  codebase.

