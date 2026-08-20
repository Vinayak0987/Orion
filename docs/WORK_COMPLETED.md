# Work Completed

All 10 phases and all 65 features are implemented. **989 tests pass, fully offline.**

---

## 1. Status at a glance

| Phase | Scope | Features | Status |
|---|---|---|---|
| 1 | Foundation & architecture | F62, F63, F65 | done |
| 2 | Core infrastructure | F6–F9, F14–F16, F59, F60, F64 | done |
| 3 | Intent classification | F1–F5 | done |
| 4 | Business orchestrator | F10–F13, F16 | done |
| 5 | Department agents | F17–F37 | done |
| 6 | External APIs & grounding | F38–F41, F61 | done |
| 7 | Output layer | F42–F46 | done |
| 8 | React frontend | F47–F52 | done |
| 9 | Evaluation & benchmarking | F53–F58 | done |
| 10 | Research paper (draft) | — | done |
| 11 | Operating layer (Orion) | OP1–OP9 | done |
| 12 | Autonomous operation | OP10–OP11 | done |
| 13 | Ablation harness | F59–F63, 4 arms, environment | built, run, null result |

**Generation layer: 65/65 features.** **Operating layer: 11 modules.**
**Ablation harness: 4 arms, 5 metrics, reactive simulated environment — run at
n=10, result not significant.**
**Tests: 989, fully offline.** **Cost: ₹0** — no paid tier anywhere in the code path.

The generation layer produces a company's opening state. The operating layer runs
that state onward: `app.operating.build_scheduler()` wires ten loops and
`run_due(company_id)` advances the business with nothing prompting it.

---

## 2. Technology used

### Backend

| Component | Technology | Version | Why |
|---|---|---|---|
| Language | Python | 3.13.2 (3.11+ required) | `StrEnum`, `datetime.UTC`, `asyncio.timeout` |
| Orchestration | LangGraph | 0.2.62 | exposes the execution graph explicitly, which RQ2 manipulates |
| Graph core | langchain-core | 0.3.29 | LangGraph dependency |
| Web framework | FastAPI | 0.115.6 | async, native WebSocket, OpenAPI for free |
| ASGI server | Uvicorn | 0.34.0 | — |
| Validation | Pydantic | 2.10.4 | every LLM JSON payload is schema-validated |
| Settings | pydantic-settings | 2.7.0 | typed config with a custom env source |
| HTTP client | httpx | 0.27.2 | async, and mockable with respx |
| Logging | structlog | 24.4.0 | structured JSON the harness can parse |
| Retry | tenacity | 9.0.0 | — |
| Database | SQLite | stdlib | zero setup, WAL mode for concurrent read |
| Vector store | ChromaDB | 0.5.23 | local file mode — no server, no Docker |
| Templating | Jinja2 | 3.1.5 | HTML report |
| PDF | xhtml2pdf | 0.2.16 | pure Python, no native deps, works on Windows |
| PDF (Docker) | WeasyPrint | 63.1 | better CSS, needs Pango/Cairo |
| Testing | pytest + pytest-asyncio | 8.3.4 / 0.25.0 | — |
| HTTP mocking | respx | 0.22.0 | tests real client code without network |

### Models

| Tier | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| STRUCTURED | `gemini-3.5-flash-lite` | Groq 8B | Ollama |
| REASONING | `llama-3.3-70b-versatile` (Groq) | Gemini | Ollama |
| FAST | `llama-3.1-8b-instant` (Groq) | Gemini | Ollama |
| F53 baseline | `gemini-3.6-flash` (pinned, single provider) | — | — |
| Local | `llama3.2:3b` via Ollama | — | — |

> Gemini 1.5 Flash, named in the original spec, was **retired** during development
> and 404s for new API keys. Gemini 2.5 Flash is closed to new users. The paper must
> report the models actually used.

### External APIs

| API | Free tier | Used for |
|---|---|---|
| Groq | 14,400 req/day | agent execution |
| Google Gemini | per-minute limited | intent extraction, F53 baseline |
| Serper.dev | 2,500 searches/month | F39 market research |
| Google Places (New) | $200 credit/month, card required | F38 competitors — **not configured** |
| OpenStreetMap (Overpass + Nominatim) | free, no key | F38 fallback — **in use** |

### Frontend

| Component | Technology | Version |
|---|---|---|
| Framework | React | 18.3.1 |
| DOM | react-dom | 18.3.1 |
| Build | Vite | 5.4.11 |
| Plugin | @vitejs/plugin-react | 4.3.4 |
| Styling | hand-written CSS | 205 lines |

**Runtime dependencies are `react` and `react-dom` only.** No UI framework, no CSS
framework, no icon package, no state library. Bundle: 162 kB (53 kB gzipped), built
in ~0.5 s.

### Infrastructure

Docker Compose 2.x (4 services), `.env` configuration, structured JSON logging,
pinned dependency versions throughout.

---

## 3. What was built, by layer

### Intent classification (F1–F5)

Hybrid extraction. The LLM handles semantics; deterministic code handles anything a
metric depends on.

| Extracted by | Fields |
|---|---|
| LLM | business type, sector, location hints, confidence |
| Regex | budget amount and scale — `₹15L`, `15 lakh`, `1.5 crore`, `₹15,00,000`, `50k` |
| Gazetteer | ~50 Mumbai localities + ~25 metros, longest-match-first |
| Rules | `is_physical`, `requires_operations` — the routing flags |

`temperature=0.0` and deterministic parsing mean the same prompt yields the same
intent every run. That is required for F54 (every projection is anchored to the
budget) and RQ2 (both arms must route identically).

Degrades to keyword-only classification if all three providers fail, so the pipeline
always produces a routable intent.

### Orchestrator (F10–F13, F16)

```
START ──► strategy ──┬──► finance   ──┐
                     ├──► branding  ──┼──► operations ──► END
                     └──► marketing ──┘
```

- Stage 2's three departments share one LangGraph superstep — genuinely concurrent
- Operations has three inbound edges, making it a join barrier
- Digital businesses omit Operations entirely (RQ2's manipulation, a config flag)
- A failing department is caught at its node; the run continues with partial results
- Driven with `astream(stream_mode="values")` so a timeout retains the last snapshot

Concurrency is **proven, not assumed**: a test gives each runner a 150 ms delay and
asserts pairwise time-window overlap plus a wall-clock bound.

### Shared state (F14–F16)

One `SharedBusinessState` object. An agent may write only to its own department's
section; a cross-department write raises `StateContractViolation`.

Two reducer families make concurrent writes safe: telemetry lists concatenate, and
department sections merge additively so an agent's unset fields cannot erase a
sibling's output.

This contract is what makes the Consistency Score meaningful — without it, a
disagreement between agents would be silently resolved by write ordering.

### 21 agents (F17–F37)

| Department | Stage 1 (parallel) | Stage 2 |
|---|---|---|
| Strategy | market_research · competitive_analysis · location_intelligence | business_planning · risk_analysis |
| Finance | revenue_model · cost_structure | funding_strategy · pl_forecast |
| Branding | brand_naming | brand_identity · brand_voice · visual_design |
| Marketing | buyer_persona | digital_plan · campaign_plan · seo_content |
| Operations | supply_chain · staffing_plan · tech_stack | process_flow |

**Arithmetic is computed, not generated.** The P&L agent supplies six drivers; all 20
forecast periods, both margins and the break-even month are computed in Python. Cost
totals, budget utilisation, payroll and channel budgets are derived from line items.

**Cross-agent reconciliation.** Where two agents assert the same quantity, the
derived figure wins:
- P&L operating expense ← the cost agent's itemised sum (excluding inventory, since
  COGS already covers it)
- Year-1 revenue ← capped at `min(obtainable market, 10 × stated budget)`
- Revenue ramp ← clamped to 4× and rescaled to match the revenue agent's projection
- Year 2/3 ← grown from the year-1 *exit rate*, not the ramp average

**Lenient output coercion.** `AgentOutput` normalises what small models actually
emit: nested lists into `list[str]`, `null` into `""` or `[]`, `"Rs 4,50,000"` into
`450000`. Every case was observed on a real run.

### Grounding (F38–F41, F61)

Injected through one hook on the agent base, so 19 of 21 agents are unchanged.

| Feature | Source | Fallback |
|---|---|---|
| F38 competitors | Google Places → OpenStreetMap | model recall |
| F39 market research | Serper | model recall |
| F40 caching | ChromaDB, local file mode | uncached |
| F41 freshness | retrieval timestamp, 30-day staleness | marked stale |

Verified data **overrides** generated data for the same field, and
`Competitor.source` records which arm produced a stored plan. That is the RQ3
mechanism.

Overpass tag filters are grouped one clause per key using `nwr`, which took a
six-tag search from 12 statements (20–40 s, frequent 429/504) down to 2 (~3.4 s).

### Output (F42–F46)

One run becomes three artefacts from a single 19-section registry, so a section
cannot appear in one output and be missing from another.

- JSON package with full generation metadata
- Standalone HTML report — inline CSS, no web fonts, opens offline
- PDF via a two-backend chain
- Per-section API access
- A generated transparency section listing the model that served each agent, tokens,
  latency, skipped departments, every API call with its freshness verdict, and the
  RQ3 arm

Reports are styled in the palette the Branding department chose.

### Frontend (F47–F52)

| Feature | Component |
|---|---|
| F47 prompt input | `PromptForm` — one textarea, Enter to submit, example chips |
| F48 live progress | `ProgressPanel` — WebSocket stream, per-department status |
| F49 report viewer | `ReportView` — department tabs, collapsible sections |
| F50 downloads | PDF, JSON, copy-section-as-JSON |
| F51 history | `HistoryList` — SQLite-backed sidebar |
| F52 errors | `Status` — unreachable / degraded / failed, shown differently |

`Value.jsx` renders section payloads **by value shape**, so adding a field to a
department model requires no frontend change.

### Evaluation (F53–F58)

Four arms: `multi_agent`, `baseline` (RQ1 control), `all_departments` (RQ2 control),
`no_grounding` (RQ3 control). 35 prompts across 8 sectors, 8 of them digital.

Five metrics, with an explicit **refusal to impute**: a metric that cannot be
computed records `applicable=false` with a reason rather than a zero.

Arms run **per prompt, not per arm**, so a provider outage degrades every arm of that
prompt equally. Benchmark provenance is machine-checked — F54 is stamped PROVISIONAL
while any benchmark is unsourced.

---

### Operating layer (OP1–OP11)

| Module | What it does | Enforced how |
|---|---|---|
| `ledger.py` | Append-only record of what happened | SQLite triggers abort UPDATE and DELETE |
| `anchors.py` | 19 metrics derived from the ledger | Not stored at all, so there is nothing to write |
| `constitution.py` | 7 hard constraints | Predicates in the execution path, rules are code not data |
| `governance.py` | Decision → review → approval → execution → audit | Whitelisted transitions; audit table append-only |
| `loops.py` | Loop registry, two topology invariants | Validated at registration, not at run time |
| `monitors.py` | Goodhart, conflict, drift, objective review | A finding cannot be built without an anchor citation |
| `scheduler.py` | Clock-injected cadence kernel | Time is a parameter; nothing sleeps |
| `memory.py` | Five isolated stores, four types each | Scoping applied in the SQL |
| `reflection.py` | Learning from measured anchor deltas | Verdict decided before any text is written |
| `departments.py` | The five department loops | Governance refusal is a recorded outcome, not an exception |
| `monitoring.py` | Wires monitors and reflection to the scheduler | Period baselines store a ledger sequence, never anchor values |

**The invariant the whole layer rests on:**

> No department, planner, worker or reflection process may write an anchor metric,
> and no learning process may optimise directly against one. Anchors are computed,
> never reported.

It is enforced structurally rather than stated: there is no anchor table, no
column and no setter, so a caller cannot write an anchor because there is nowhere
to write one. `tests/test_anchors.py` asserts this, including that no table with
"anchor" in its name exists.

This generalises two findings the generation layer produced empirically — that
derived figures must override asserted ones (§4.4 of the paper), and that
cross-agent constraints hold only when enforced in code (§7.2).

### Paper tooling

| Addition | Purpose |
|---|---|
| `evaluation/significance.py` | Paired Wilcoxon and t-tests, rank-biserial and Cohen's d, underpowered flagging below 10 pairs |
| `scripts/make_figures.py` | Figures 2 and 4 from real data, byte-deterministic output |
| `scripts/make_deck.py` | Review deck rebuilt from the supplied template, 19 slides |
| `scripts/autonomy_demo.py` | A simulated quarter run unattended |
| `scripts/operating_demo.py` | Component-level walkthrough of the operating layer |

### Ablation harness (F59–F63)

| Module | Purpose |
|---|---|
| `app/operating/environment.py` | Seeded stochastic market that reacts to department spend |
| `app/operating/ablation.py` | Four arms (`single_loop`, `anchors_only`, `monitors_only`, `full_graph`) |
| `evaluation/operating_metrics.py` | F59 divergence, F60 latency, F61 conflicts, F62 staleness, F63 load |
| `evaluation/ablation_harness.py` | Paired-seed runner; CSV/JSON output |
| `scripts/ablation_report.py` | Per-arm outcomes plus paired Wilcoxon via `significance.py` |

Key design properties:
- All arms use the same planner, memory and execution machinery; they differ
  **only** in control topology
- The manipulated variable is *which quantity a department observes* — its proxy,
  or the anchor it is accountable for
- Marketing acquisition is value-destroying by unit economics: ~₹200 to acquire,
  ~₹58 expected lifetime contribution. The churn amplifier that would enlarge the
  effect is **defaulted to 0.0** so the result cannot rest on it
- Signals are **period-scoped**, because cumulative anchors are dominated by
  history. Only ledger sequence numbers are retained, never anchor values, so the
  anchor invariant holds

99 tests added. Run with:
```powershell
.\.venv\Scripts\python.exe -m evaluation.ablation_harness --seeds 10 --days 90 --label ablation-v2
.\.venv\Scripts\python.exe -m scripts.ablation_report --label ablation-v2
```

**Measured result at n=10: not significant.** F59 favours the full graph in every
comparison (−0.78 vs −0.59 for `single_loop`) but the best p-value is 0.059.
Between-seed SD is 33–70% of the means. RQ4–RQ7 remain unanswered. Full table,
the five defects the first sweep exposed, and the modelling caveats are in
`docs/OPERATING_LAYER.md` §4b.

---

## 4. Results measured so far

All at n ≤ 5 — direction only, not findings.

| Metric | multi_agent | baseline | Verdict |
|---|---|---|---|
| Financial accuracy (MAPE, lower better) | ~132 | **~41** | baseline wins |
| Plan completeness | **100.0** | 80.8 | multi-agent wins |
| Consistency | 97.8 | 100.0 | tied |

**RQ2 supported:** 17.3% token saving with a 0.0 pp completeness delta on prompts
where routing actually skipped a department.

**RQ3 not measurable:** needs hand-verified competitor ground truth.

### Variance compounding — the central finding

Identical prompt, five runs per arm:

| Arm | n | Mean MAPE | SD | Min | Max | Spread |
|---|---|---|---|---|---|---|
| baseline | 3 | 63.1 | 21.2 | 50.0 | 87.5 | 1.8× |
| multi_agent | 5 | 158.9 | **103.8** | 38.4 | 290.9 | **7.6×** |

Multi-agent SD is 4.9× the baseline's, and its *best* run beat the baseline's best.
The architecture is **unreliably better**, not reliably worse.

### Autonomous operation

`scripts/autonomy_demo.py`, 90 simulated days, no prompting and no LLM calls:

| Measure | Value |
|---|---|
| Scheduled loop runs | 574 |
| Ledger entries | 486 |
| Net margin | 60% → +2.5% |
| Customers acquired | 0 → 104 |
| Marketing episodic memories | 14, against 89 for each other department |
| Findings raised | CRITICAL proxy divergence, HIGH inter-department conflict |

The monitors caught the divergence, and the company then **self-corrected**:
marketing took a margin lesson, suppressed its spend task, and stopped acting —
which is what the 14-versus-89 memory gap records.

These figures changed on 8 Aug 2026. Until bug 21 was fixed the reflective lesson
was never retrieved, marketing never stopped, and the run ended at **−18.5%** margin
with 272 acquisitions and 352 ledger entries. The old numbers demonstrated the
monitors noticing a collapse; the new ones demonstrate the loop closing.

Two qualifications belong with these numbers. The planners are rule-based, so this
demonstrates the control structure rather than good judgement. And the ablation's own
result is a null at n=10, so this is a demonstration and not yet an experiment — see
`docs/OPERATING_LAYER.md` §4b.

### Reliability

| Arm | Runs | Produced a plan |
|---|---|---|
| multi_agent | 5 | 5 (100%) |
| baseline | 5 | 3 (60%) |

The multi-provider fallback chain confers real resilience. Qualified in the paper:
the baseline is pinned to one provider by experimental design.

---

## 5. Bugs found by running the real system

Twenty-five defects that mocked tests could not have caught. Each is fixed and
pinned by a regression test. Numbers 15–20 were found while building the operating
layer; **21–25 were found by running the ablation harness**, and 21 is the most
consequential in the project — a documented, "load-bearing" mechanism that could
never fire, with a test that appeared to prove it and did not.

| # | Bug | Impact if unfixed |
|---|---|---|
| 1 | Budget parser rounded before multiplying | "1.5 crore" became ₹2 Cr — 33% error on the figure every projection anchors to |
| 2 | Sector scored by longest keyword only | "saas platform for logistics" classified as services |
| 3 | structlog reserves `event` | crashed every graph execution (16 tests at once) |
| 4 | LangGraph rejects node names matching state keys | graph would not compile |
| 5 | `list[str]` received nested lists | supply_chain agent lost its entire contribution |
| 6 | `str` field received `null` | process_flow produced 0 workflow steps |
| 7 | P&L gave up when a driver was missing | 0 forecast periods, null margins |
| 8 | Empty env vars shadowed `.env` | a valid API key silently ignored |
| 9 | OSM keyword order | "dental_clinic" matched general clinics |
| 10 | `api_traces` dropped by the sub-graph | report claimed 0 API calls after using OSM |
| 11 | Short brand name scored as missing | completeness understated 92.31% vs 96.15% |
| 15 | Paired t-test divided by zero variance | scipy returned `inf`; the report would have printed `t = inf` as a result |
| 16 | `requires_operations` is separate from `is_physical` | Figure 2 rendered the wrong DAG for digital businesses |
| 17 | matplotlib SVG was non-deterministic | a regenerated paper figure differed byte-for-byte every run |
| 18 | `tokenise` dropped tokens of length ≤ 2 | "₹15 lakh" and "₹40 lakh" tokenised identically and consolidated into one memory |
| 19 | Cold-start stagger was a gate, not a phase shift | a fixed-hour tick has a constant remainder, so **strategy and finance never ran once in 90 simulated days** |
| 20 | Proxy delta required a computable baseline | a department going 0 → 40 acquisitions made no claim, so its first — and most capture-prone — period was never checked |
| 12 | `export_plan` emitted all-default sections | `/package` returned a contentless plan as 200 |
| 13 | Baseline ran on the wrong model | RQ1's control was a local 3B model, not Gemini |
| 14 | Baseline nested output validated as empty | reported a completed 0% baseline — a false RQ1 landslide |
| 21 | **Reflective lessons were unretrievable by the planner** | The planner queried memory with objective + PROXY; reflection writes in ANCHOR vocabulary. Token overlap zero, so `_score` returned 0.0 and the lesson was dropped. The documented "load-bearing" learning branch **could never fire in the live path**, and `test_learning_changes_behaviour_across_ticks` passes unchanged with its memory write deleted — it was passing because of the anchor-health branch. Found by running the ablation, where all four arms came out byte-identical |
| 22 | Simulated business was structurally unprofitable | `_anchor_unhealthy` latched on day 2 and the marketing planner proposed retention for the rest of every run, in every arm. No proxy gaming could occur |
| 23 | Cumulative anchors hid period dynamics | A cumulative ratio is dominated by history: `net_margin_pct` moved only 17.7% → 18.6% across a run in which the company steadily destroyed value. Period-over-period control and detection need **period-scoped** anchor sets |
| 24 | F60 latency was a cadence formula, not a measurement | Computed as `7 * (idx + 1) + 6` from a finding's list position; returned 6.0 with sd 0.0 for every seed and arm |
| 25 | F62 reviewed an empty objectives list | `review_objectives` could never fire, so 0.0-vs-1.0 recorded the arm configuration rather than any staleness |

Plus five financial-reconciliation defects (§3, agents) that took MAPE from ~180–450
down to ~70–200.

---

## 6. Test coverage

| File | Tests | Covers |
|---|---|---|
| `test_agents.py` | 107 | 21 agents, coercion, sub-graphs, reconciliation |
| `test_intent.py` | 82 | budget, location, sector, routing flags, classifier |
| `test_apis.py` | 67 | Places, Overpass, Serper, cache, grounding |
| `test_orchestrator.py` | 63 | routing, DAG, concurrency, completeness |
| `test_evaluation.py` | 59 | baseline, all five metrics, benchmarks |
| `test_output.py` | 49 | sections, package, HTML, PDF |
| `test_api.py` | 19 | HTTP endpoints and WebSocket |
| `test_llm_chain.py` | 19 | provider fallback, JSON repair |
| `test_state.py` | 16 | state contract, reducers |
| `test_providers_http.py` | 14 | real provider HTTP against mocks |
| `test_db.py` | 9 | SQLite persistence |
| `test_config.py` | 13 | env precedence, degradation warnings |
| `test_constitution.py` | 42 | hard constraints, injection resistance, amendment refusal |
| `test_memory.py` | 37 | department isolation, four types, consolidation, decay |
| `test_governance.py` | 34 | gate chain, audit immutability, approval cannot unlock a constraint |
| `test_scheduler.py` | 35 | cadence, single flight, restart safety, stagger starvation |
| `test_anchors.py` | 30 | the invariant, derivation, deltas, thin evidence |
| `test_loops.py` | 30 | I1 termination, I2 independence, default topology |
| `test_significance.py` | 27 | paired tests, effect sizes, underpowered labelling |
| `test_ledger.py` | 25 | append-only at the database level, integer money |
| `test_monitors.py` | 25 | the Goodhart case, conflict, drift, objective review |
| `test_departments.py` | 24 | the five loops, gating, learning changes behaviour |
| `test_reflection.py` | 21 | verdict from measurement, not from self-report |
| `test_monitoring.py` | 15 | monitor wiring, snapshots without storing anchors |
| `test_make_figures.py` | 14 | figure generation, determinism, Agg backend |
| `test_operating_e2e.py` | 6 | the whole operating layer on one scenario |
| **Total** | **869** | fully offline behind a socket guard |

A socket guard fails any test attempting an outbound connection, so the suite
provably consumes zero API quota.

---

## 7. Documentation produced

| File | Contents |
|---|---|
| `README.md` | architecture, design rationale, measured findings |
| `docs/PROJECT_SPEC.md` | all 65 features with status markers |
| `docs/FEATURE_PROMPT.md` | AI IDE prompt templates and anti-patterns |
| `docs/HOW_TO_RUN.md` | setup, run, troubleshoot |
| `docs/WORK_COMPLETED.md` | this file |
| `docs/WORK_REMAINING.md` | what is left, with ready-to-use prompts |
| `docs/CONFIGURATION_TODO.md` | keys and settings still needed |
| `docs/paper/PAPER.md` | full research paper draft |
| `docs/paper/REPRODUCIBILITY.md` | how to regenerate every number |
| `docs/paper/FIGURES.md` | 5 figures, 10 tables, with data provenance |
