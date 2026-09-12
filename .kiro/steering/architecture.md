# Architecture — Orion (mabgp)

> Kiro steering document. This describes the system as verified in code on
> 10 September 2026. When this file and the code disagree, the code wins —
> fix the file.

**Orion** (codebase identifier `mabgp`) is an AI Business Operating System with
two layers. The **generation layer** turns one sentence into a founding business
plan using 21 specialised agents across 5 departments, coordinated by a routing
orchestrator over an enforced append-only state object. The **operating layer**
runs that finished plan onward as a living company on department cadences. A
third, strictly additive stratum — the **Planning Report flow** — is being added
in front of the generation layer (see `design.md` and `phases.md`).

## 1. Verified baseline

| Point | Value |
|---|---|
| Tests | 989 passing, fully offline; a socket guard fails any outbound connection |
| Stack | Python 3.13 in `.venv` at repo root; LangGraph; FastAPI; stdlib sqlite3; ChromaDB |
| LLM | Groq → Gemini → Ollama fallback chain, free tiers only; every call through `app.llm.llm_client` |
| Frontend | React 18 + Vite; `react` + `react-dom` only; hash routing; inline-SVG charts |
| Repo | Windows/PowerShell; it IS a git repo (`main`, tracks `origin/main`) — stale notes claiming "no git repo" are wrong |

Verify before building:

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
cd C:\Users\Vinayak\Desktop\kiro\backend
..\.venv\Scripts\python.exe -m pytest -q     # expect 989 passed
```

## 2. Module map

| Path (repo-relative) | Role |
|---|---|
| `backend/app/main.py` | FastAPI app: `/health`, `/intent`, `/generate`, `/ws/generate`, `/sessions*`, output routes |
| `backend/app/config.py` | all settings (F63); nothing else reads `os.environ`; `warnings()` feeds `/health` |
| `backend/app/intent/` | F1–F5: prompt validation; hybrid classifier (LLM semantics + deterministic budget/location/routing flags) |
| `backend/app/models/` | `intent.py` BusinessIntent; `departments.py` output schemas (FROZEN fields); `state.py` SharedBusinessState + `apply_department_patch` |
| `backend/app/agents/` | `base.py` Agent/AgentSpec; five department modules with stage tuples; `registry.py`; `subgraph.py` |
| `backend/app/orchestrator/` | `routing.py` (F10), `graph.py` (F11 DAG + `describe_graph`), `runner.py` (`orchestrate`), `progress.py` (F12), `completeness.py` (F16) |
| `backend/app/llm/` | `base.py` FreeTierTracker + ModelTier; `chain.py` fallback + JSON repair; three providers |
| `backend/app/apis/` | Places (Google/OpenStreetMap via `select_provider`), Serper, Chroma cache, freshness |
| `backend/app/output/` | section catalogue, HTML/PDF render, BusinessPackage |
| `backend/app/db/sqlite.py` | `sessions` + `evaluation_results` tables; the only home of that SQL |
| `backend/app/operating/` | ledger, anchors, constitution, governance, loops, monitors, scheduler, memory, reflection, departments, monitoring, ablation; own `/operating` router |
| `frontend/src/` | `api.js` single backend client; `App.jsx` hash router; `components/`, `operating/`, `views/` |

## 3. Generation execution flow

```
prompt
  └► validate_prompt (F1)                10–500 chars, else PromptValidationError
     └► classify_intent (F2)             ONE LLM call, STRUCTURED tier;
        │                                keyword-heuristic fallback (confidence 0.35)
        └► resolve_departments (F10)     RoutingDecision{active, skipped, reason, dynamic}
           └► build_graph (F11)          department DAG; stage-2 fan-out; operations join
              └► astream + timeout (F12) department sub-graphs run staged agents
                 └► _finalize (F16)      completeness + contradictions → RunStatus
                    └► _persist_final   sessions row (F59)
```

`POST /intent` stops after F10 and returns `describe_graph(decision)` —
ephemeral, department-level only, never persisted. That is the gap the
Planning Report flow closes.


## 4. The 21-agent topology (verified from the stage tuples)

Orchestrator-level stages (`routing.py`): Stage 1 `strategy` → Stage 2
`finance ∥ branding ∥ marketing` → Stage 3 `operations` (a join — it waits for
all of Stage 2). Digital businesses omit Stage 3 entirely. Agents within one
department stage share a superstep and run concurrently; later stages read
earlier stages' output.

| # | `agent_id` | Feature | Department | Dept stage | Runs |
|---|---|---|---|---|---|
| 1 | `market_research` | F20 | strategy | 1 | parallel |
| 2 | `competitive_analysis` | F19 | strategy | 1 | parallel |
| 3 | `location_intelligence` | F21 | strategy | 1 | parallel |
| 4 | `business_planning` | F17 | strategy | 2 | parallel |
| 5 | `risk_analysis` | F18 | strategy | 2 | parallel |
| 6 | `revenue_model` | F22 | finance | 1 | parallel |
| 7 | `cost_structure` | F23 | finance | 1 | parallel |
| 8 | `funding_strategy` | F24 | finance | 2 | parallel |
| 9 | `pl_forecast` | F25 | finance | 2 | parallel |
| 10 | `brand_naming` | F26 | branding | 1 | sequential (alone) |
| 11 | `brand_identity` | F27 | branding | 2 | parallel |
| 12 | `brand_voice` | F28 | branding | 2 | parallel |
| 13 | `visual_design` | F29 | branding | 2 | parallel |
| 14 | `digital_plan` | F30 | marketing | 1 | sequential (alone) |
| 15 | `buyer_persona` | F31 | marketing | 1 | sequential (alone) |
| 16 | `campaign_plan` | F32 | marketing | 2 | parallel |
| 17 | `seo_content` | F33 | marketing | 2 | parallel |
| 18 | `supply_chain` | F34 | operations | 1 | parallel |
| 19 | `staffing_plan` | F35 | operations | 1 | parallel |
| 20 | `tech_stack` | F36 | operations | 1 | parallel |
| 21 | `process_flow` | F37 | operations | 2 | sequential (alone) |

Branding and Marketing run their naming/persona agent alone in stage 1 because
every stage-2 agent in those departments references its output. Operations'
`process_flow` runs last because it assigns roles that `staffing_plan`
produced. Tier, temperature and `max_tokens` per agent live on `AgentSpec` in
each department module — the Planning Report reads them there and never
re-derives topology anywhere else. `registry.describe_all_departments()` is
the canonical serialized form of this table.

## 5. State contract and telemetry

`SharedBusinessState` (a LangGraph `TypedDict`) holds: `session_id`,
`raw_prompt`, `intent` (single-writer), five department sections keyed by
department name with a `merge_section` reducer, append-only telemetry lists
(`agent_traces`, `api_traces`, `errors` via `operator.add`), and `metadata`
(single-writer). Department sub-graphs are invoked with a derived state so
telemetry lists start empty and are never double-counted.

`apply_department_patch(state, department, patch)` is the only sanctioned
department write: it rejects keys naming another department's section and
unknown fields (`StateContractViolation`); patch values merge over current
section values. `AgentTrace` records `agent_id`, `department`, `status`
(`completed | failed | skipped`), provider, model, token counts, latency and
error — it is the F46/F58 measurement substrate. Run verdicts
(`RunMetadata.status`) are `pending | running | completed | partial | failed |
timeout`; the run is driven with `astream(stream_mode="values")` so the last
full snapshot survives a timeout, making partial results real (F52).

## 6. Operating layer (summary)

`app/operating/` runs the finished plan onward: an append-only `ledger` (the
only writable substrate), `anchors` computed from the ledger and stored
nowhere (the project's central invariant), a `constitution` enforced in the
call path, a `governance` gate chain, `loops`/`scheduler` driving ten
schedulable loops, four `monitors`, typed `memory`, `reflection`, and the
`ablation` harness. Honest status: control mechanisms are built and tested and
the system runs unattended, but planners are rule-based and the ablation's
n=10 result is a null — RQ4–RQ7 are unanswered. Nothing in the Planning
Report flow may touch this layer.

## 7. API surface and frontend (verified)

Generation-layer endpoints: `GET /health`, `POST /intent`, `POST /generate`,
`WS /ws/generate`, `GET /sections`, `GET/DELETE /sessions…`, package, section,
HTML and PDF report routes. Operating layer: 12 routes under
`/operating` via its own router — the pattern the planning router will copy.
The frontend (`frontend/src/`) is `api.js` (the single backend client),
`App.jsx` (hash routes `#/generate`, `#/business`, `#/work`, `#/activity`,
`#/loops`), `components/`, `operating/` (13 components), `views/` (4), and one
hook. CORS is localhost-only; the app has no authentication by design.

## 8. Where the Planning flow sits

A new, strictly additive package `backend/app/planning/` sits in front of the
generation layer: it READS `classify_intent`, `resolve_departments`,
`describe_all_departments`, `llm_client.health()` and `settings`; it WRITES
only its own `planning_reports` table and, at confirm time, flips its own
status column. It does not modify routing, agents, the DAG, the operating
layer, or the existing endpoints beyond an optional `planning_report_id`
field on the WebSocket run request. Ownership rule: topology truth stays in
`registry.py`; readiness truth stays in `llm_client.health()` + the database
ping; the planning package composes them and owns only the report lifecycle.
The inspect-and-confirm pattern itself is proven at scale in the
MIT-licensed AgentOS planner (verified 10 September 2026); Orion
reimplements the pattern in FastAPI — pattern reuse, no code ported.

## 9. Rules that bind every change

From `AGENTS.md` (authoritative when fresher than this file): locked stack;
free tiers only; every LLM call via `app.llm.llm_client`; every
generation-layer state write via `apply_department_patch`; department field
names FROZEN (add optional fields, never rename); the suite stays fully
offline with a regression test per change; runnable code only, pinned
versions; frontend depends on `react`/`react-dom` only (inline-SVG charts);
anchors are computed, never reported. Verify with pytest; trust the test
output over any document.

