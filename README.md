# MABGP — Multi-Agent Autonomous Business Generation Platform

Final-year B.E. Computer Engineering major project (2027 batch, Mumbai University).

One natural-language prompt → 20+ specialized AI agents across 5 departments →
a complete structured business package in 60–90 seconds.

```
"Ice cream shop in Andheri, ₹15L budget"
        ↓
Strategy · Finance · Branding · Marketing · Operations
        ↓
Structured business plan (JSON / HTML / PDF)
```

**Everything in this project is free.** No paid API tier is used anywhere.

- **How to run it:** [`docs/HOW_TO_RUN.md`](docs/HOW_TO_RUN.md)
- **What is built, and with what:** [`docs/WORK_COMPLETED.md`](docs/WORK_COMPLETED.md)
- **What is left, with prompts:** [`docs/WORK_REMAINING.md`](docs/WORK_REMAINING.md)
- **Configuration still needed:** [`docs/CONFIGURATION_TODO.md`](docs/CONFIGURATION_TODO.md)
- Full specification and 65-feature breakdown: [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md)
- Research paper draft: [`docs/paper/PAPER.md`](docs/paper/PAPER.md)
- How to reproduce every number: [`docs/paper/REPRODUCIBILITY.md`](docs/paper/REPRODUCIBILITY.md)
- AI IDE prompt templates for adding features: [`docs/FEATURE_PROMPT.md`](docs/FEATURE_PROMPT.md)

---

## Current status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Foundation & Architecture (F62, F63, F65) | done |
| 2 | Core Infrastructure (F6–F9, F14–F16, F59, F60, F64) | done |
| 3 | Intent Classification (F1–F5) | done |
| 4 | Business Orchestrator (F10–F13, F16) | done |
| 5 | Department Agents (F17–F37) | done |
| 6 | External APIs (F38–F41, F61) | done |
| 7 | Output Layer (F42–F46) | done |
| 8 | React Frontend (F47–F52) | done |
| 9 | Evaluation & Benchmarking (F53–F58) | done |
| 10 | Research Paper (draft) | done |

---

## Quick start — local Python

```powershell
# 1. Virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Dependencies
pip install -r backend/requirements.txt

# 3. Configuration (works with zero keys — falls back to Ollama)
Copy-Item .env.example .env

# 4. Tests (517 tests, fully offline, no API keys needed)
cd backend
pytest

# 5. Run the API
uvicorn app.main:app --reload --port 8080
```

Then open http://localhost:8080/health and http://localhost:8080/docs

---

## Quick start — Docker Compose

```bash
cp .env.example .env          # fill in free API keys (optional)
docker compose up --build

# One-time: pull the local fallback model (~4.7 GB download)
docker compose exec ollama ollama pull llama3.1:8b
```

| Service | URL | Purpose |
|---------|-----|---------|
| backend | http://localhost:8080 | FastAPI |
| frontend | http://localhost:5173 | React + Vite |
| ollama | http://localhost:11434 | Local LLM fallback (F8) |
| chromadb | http://localhost:8000 | Vector store (F61) |

---

## Free API keys

All optional — the system runs without any of them, degrading to Ollama-only.

| Key | Where to get it | Free tier |
|-----|-----------------|-----------|
| `GROQ_API_KEY` | https://console.groq.com/keys | 14,400 requests/day |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey | 15 RPM, 1M tokens/day |
| `GOOGLE_PLACES_API_KEY` | https://console.cloud.google.com/apis/credentials | $200 credit/month (card required) |
| `SERPER_API_KEY` | https://serper.dev/api-key | 2,500 searches/month |

`/health` reports which keys are missing and what capability is degraded as a result.

---

## Architecture

```
Input Layer          natural language prompt
      ↓
Intent Classifier    LLM → {business_type, location, sector, scale, budget}
      ↓
Orchestrator         routing rules → active_departments → execution DAG
      ↓
Department Layer     5 LangGraph sub-graphs, 21 specialized agents
      ↓
SharedBusinessState  single append-only Pydantic state object
      ↓
Output Layer         JSON package → HTML report → PDF
```

Execution order:

```
Stage 1   Strategy                              (sequential)
Stage 2   Finance ∥ Branding ∥ Marketing         (parallel)
Stage 3   Operations                             (conditional)
```

### LLM fallback chain (F9)

```
STRUCTURED tier  →  Gemini    →  Groq 8B   →  Ollama
REASONING  tier  →  Groq 70B  →  Gemini    →  Ollama
FAST       tier  →  Groq 8B   →  Gemini    →  Ollama
```

Agents never import a vendor SDK. Every call goes through `app.llm.llm_client`,
which walks the chain, retries with backoff, and records which provider served
the request. That telemetry is what makes the cost/latency table in the paper
reproducible.

### Hybrid intent extraction (F1–F5)

The classifier splits work between the LLM and deterministic code:

| Extracted by | Fields |
|--------------|--------|
| LLM (semantic) | `business_type`, `business_type_label`, `sector`, location hints, `confidence` |
| Regex / gazetteer (exact) | `budget.amount` + `scale` (F4), location normalization (F3), `is_physical` / `requires_operations` (F5) |

The routing flags and the budget are deterministic on purpose. Every financial
projection is anchored to the budget, so if that number drifted between providers
the MAPE variance in F54 would no longer be attributable to the agents. Likewise,
RQ2 compares a dynamic-routing run against an all-departments run on the same
prompts — if the routing decision itself were stochastic, the two arms would not
be comparable.

`temperature=0.0` and the `STRUCTURED` tier (Gemini first) are used for the same
reason: the same prompt yields the same intent on every run.

If all three providers are down, the classifier falls back to keyword-only
classification rather than raising, so the pipeline always produces a routable
intent:

```bash
curl -X POST localhost:8080/intent \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Ice cream shop in Andheri, Rs 15L budget"}'
```

```
sector food_and_beverage · area Andheri · Rs 15.0 L · scale small
active_departments  strategy, finance, branding, marketing, operations
```

```bash
# Digital business -> Operations is skipped (F10 dynamic routing)
-d '{"prompt": "Start an online tutoring platform for CBSE students"}'
```

```
sector education · Rs unspecified
skipped_departments  ["operations"]
```

---

### Orchestrator DAG (F10–F13)

`resolve_departments(intent)` produces a `RoutingDecision`, which `build_graph()`
compiles into a LangGraph `StateGraph`. Physical business:

```
START ──► strategy ──┬──► finance   ──┐
                     ├──► branding  ──┼──► operations ──► END
                     └──► marketing ──┘
```

Digital business — Operations is absent and Stage 2 fans straight into END:

```
START ──► strategy ──┬──► finance   ──► END
                     ├──► branding  ──► END
                     └──► marketing ──► END
```

Stage 2's three departments share one LangGraph superstep, so they run
concurrently. Operations has three inbound edges, which makes it a join barrier:
it cannot start until all of Stage 2 has finished.

`tests/test_orchestrator.py::test_stage_2_departments_run_concurrently` proves the
concurrency rather than assuming it — each runner sleeps 150 ms and the test
asserts pairwise time-window overlap plus a wall-clock bound.

The two RQ2 arms run off the same flag:

```bash
# experimental arm - dynamic routing
curl -X POST localhost:8080/generate -H 'Content-Type: application/json' \
  -d '{"prompt": "Start an online tutoring platform"}'
# -> 4 departments, skipped_departments: ["operations"]

# control arm - all departments
  -d '{"prompt": "Start an online tutoring platform", "force_all_departments": true}'
# -> 5 departments, skipped_departments: []
```

Both arms consume the identical `BusinessIntent`, so the measured token and time
delta is attributable to routing alone.

Failure isolation: a department that raises is caught at its graph node, recorded
in `errors` and `agent_traces`, and the run continues — so `/generate` returns
partial results (F52) instead of a 500. A timeout does the same, because the graph
is driven with `astream(stream_mode="values")` and the last snapshot is retained.

---

### Department agents (F17–F37)

21 agents across 5 nested LangGraph sub-graphs. Within a department, agents are
grouped into stages: same stage runs concurrently, a later stage reads what an
earlier stage wrote.

| Department | Stage 1 (parallel) | Stage 2 |
|------------|--------------------|---------|
| Strategy | market_research · competitive_analysis · location_intelligence | business_planning · risk_analysis |
| Finance | revenue_model · cost_structure | funding_strategy · pl_forecast |
| Branding | brand_naming | brand_identity · brand_voice · visual_design |
| Marketing | buyer_persona | digital_plan · campaign_plan · seo_content |
| Operations | supply_chain · staffing_plan · tech_stack | process_flow |

The staging encodes real dependencies. Business Planning sizes the market against
research that already ran; the P&L agent needs revenue and costs; the three
branding agents all reference the name that was chosen; process flow assigns
workflow steps to roles the staffing agent actually created.

Two supporting mechanisms make that work:

- `merge_section` reducer on each department channel, so several agents in one
  superstep each contribute their own fields to a shared section instead of
  overwriting each other (a naive reducer would let an agent's empty defaults
  erase a sibling's output).
- `context_block()` renders the business facts once, identically, for all 21
  agents. If each agent restated the intent in its own words, cross-department
  disagreement would be a prompt artefact and the Consistency Score (F57) would
  be measuring noise.

**Arithmetic is computed, not generated.** The P&L agent asks the model for six
drivers (opening revenue, exit revenue, COGS %, fixed opex, two growth rates) and
then generates all 20 forecast periods, both margins and the break-even month in
Python. Those drivers are also *reconciled* before use: opex against the cost
agent's itemised total, and year-1 revenue against `min(SOM, 10 x budget)`.
Where two agents assert the same quantity, the derived figure wins. Cost totals, budget utilisation, payroll and per-channel budgets are
derived the same way. F54 measures margin accuracy against an MSME benchmark — if
the margin were itself generated text, the metric would partly be scoring the
model's arithmetic rather than its business judgement, and it would not be
reproducible across providers.

**Lenient output coercion.** `AgentOutput` coerces the shapes small local models
actually emit before validation: nested lists into `list[str]`, `null` into `""`
or `[]`, and `"Rs 4,50,000"` into `450000`. Every case in that layer was observed
on a real llama3.2:3b run and previously cost an agent its entire contribution.

---

### External data grounding (F38–F41)

Two agents are grounded in real-world data; the other 19 are unchanged. Grounding
is injected through a single `gather_grounding()` hook on the agent base, so no
existing agent signature changed.

| Feature | Source | Fallback |
|---------|--------|----------|
| F38 competitors | Google Places → OpenStreetMap | LLM recall |
| F39 market research | Serper.dev | LLM recall |
| F40 caching | ChromaDB | uncached |
| F41 freshness | retrieval timestamp | marked stale |

**How RQ3 is run.** Verified data *overrides* generated data for the same field:

```python
patch = self.to_patch(parsed, state)
patch.update(grounding.patch)     # real competitors replace recalled ones
```

`Competitor.source` records which arm produced a stored plan — `google_places`,
`openstreetmap`, or `llm_inferred` — so F55 Competitor Coverage can score the two
conditions apart. Turning grounding off is a config flag, not a code change.

**Measured provider trade-off.** Live probes against Mumbai, worth reporting in
the paper's limitations section rather than glossing over:

| | Google Places | OpenStreetMap |
|---|---|---|
| Key required | yes, plus a billing account | none |
| Ratings / review counts | yes | **none at all** |
| Coverage (Bandra, 2 km) | not yet measured | 30 restaurants, 30 hairdressers |
| `amenity=ice_cream` coverage | — | **zero** — Indian ice cream shops aren't tagged that way |
| Rate limiting | quota-based | throttles on the 3rd query in a row |
| Latency | not yet measured | 3.4 s tuned, 40 s untuned |

Two mitigations came out of those measurements. Tag filters are grouped one clause
per key using `nwr`, which took a six-tag sector search from 12 Overpass statements
(20–40 s, frequent 429/504) down to 2 (~3.4 s). And when specific tags return
nothing, the query broadens once to the sector — which is what turns an ice cream
search in Bandra from zero results into `Naturals`, `Snowbite`, `Baba Falooda`.

OpenStreetMap is a genuine substitute for *existence* checking but not for
*ratings*. F19's price positioning and any review-count analysis need Places.

**Cache economics.** The evaluation harness runs 30+ prompts across several arms.
Without caching, each arm re-issues the same Serper queries — 4× the credits, and
results that could drift between arms so a measured difference would no longer be
attributable to the manipulation. Cached entries keep their original retrieval
timestamp, so a hit still ages out under F41 instead of looking permanently fresh.

---

### Output layer (F42–F46)

One finished run becomes three artefacts from a single source of truth:

```
SharedBusinessState
      ↓  build_package()          F42  JSON package + F46 metadata
      ↓  render_html()            F43  standalone HTML report
      ↓  render_pdf()             F44  PDF
```

| Endpoint | Returns |
|----------|---------|
| `GET /sections` | section catalogue (19 sections) |
| `GET /sessions/{id}/package` | full JSON package |
| `GET /sessions/{id}/sections/{key}` | one section only (F45) |
| `GET /sessions/{id}/report` | HTML report |
| `GET /sessions/{id}/report.pdf` | PDF download |

**One registry, one template.** `output/sections.py` defines all 19 sections —
order, title, source department, member fields. The JSON package, the HTML report,
the PDF and the per-section API all read from it, so a section cannot appear in one
output and be missing from another. A test asserts every listed field actually
exists on its department model, which keeps the report honest against the frozen
field names.

Sections are finer-grained than departments (Strategy yields five) so the frontend
can collapse them independently and re-fetch just `projections` without the
backend re-deriving what "finance" means.

**PDF without paid tools or native-library pain.** Two free backends, tried in
order of quality:

| Backend | Quality | Dependencies |
|---------|---------|--------------|
| WeasyPrint | best CSS support | Pango/Cairo — installed in the Docker image only |
| xhtml2pdf | CSS2 subset | pure Python, works anywhere including Windows |

The template deliberately avoids flexbox, grid and web fonts so **the same file
renders correctly in both** — one template, two targets, no drift. If neither
backend imports, `/report.pdf` returns 503 with guidance instead of a 500, and the
HTML report still prints to PDF from any browser. `/health` reports which backend
is active.

**Transparency is built into the document (F46).** Every report ends with a
generated section listing the model that served each agent, tokens, latency, which
departments were skipped and why, every external API call with its freshness
verdict, and the RQ3 arm the plan belongs to. Reports are styled in the palette the
Branding department chose, and the HTML is fully self-contained — no external
stylesheet, no web font — so it opens offline and needs no network at PDF time.

---

### Frontend (F47–F52)

React 18 + Vite. **The only runtime dependencies are `react` and `react-dom`** — no
UI framework, no CSS framework, no icon package. Styling is one 205-line
stylesheet using system fonts, so there is no web-font request, nothing to
configure, and the production bundle is 162 kB (53 kB gzipped) built in ~0.5 s.

| Feature | Component |
|---------|-----------|
| F47 prompt input | `PromptForm` — one textarea, Enter to submit, example chips |
| F48 live progress | `ProgressPanel` — WebSocket stream, per-department status |
| F49 report viewer | `ReportView` — department tabs, collapsible sections |
| F50 downloads | PDF, JSON, copy-section-as-JSON |
| F51 history | `HistoryList` — sidebar backed by SQLite |
| F52 errors | `Status` — unreachable / degraded / failed, each shown differently |

**Live progress reuses the orchestrator's existing hook.** `/ws/generate` passes
its `send_event` function straight into the `progress_callback` the orchestrator
has accepted since Phase 4, so the socket is a transport detail rather than a
second execution path. A verified stream for a physical business:

```
session_started   Unisex salon in Bandra with 12 lakh investment
intent_resolved   unisex_salon / services / Bandra, Mumbai, Maharashtra
routing_resolved  operations active: unisex_salon is physical
started strategy  → completed 20%
started finance · started branding · started marketing      ← Stage 2 overlaps
completed branding 40% · finance 60% · marketing 80%
started operations → completed 100%
result            status=partial completeness=96.15% tokens=17094
```

Stage 2's three departments all *start* before any of them completes, so the
concurrency the paper claims is visible in the UI rather than only in a test.

**One rendering contract.** `Value.jsx` renders section payloads by value shape —
lists of objects become tables, `*_inr` fields get Indian digit grouping,
`color_palette` becomes swatches. Combined with the backend's section registry
(F45), adding a field to a department model needs no frontend change.

Opening a stored session reshapes the SQLite row into the same object the
WebSocket returns, so `ReportView` has a single input contract for both paths.

---

### Evaluation harness (F53–F58)

```bash
python -m evaluation.harness --all --label paper-run-1     # run every arm
python -m evaluation.report  --label paper-run-1           # tables + CSV
```

Four arms over a fixed 35-prompt set (`evaluation/prompts.json`, 8 sectors, 4 budget
scales, 8 digital businesses):

| Arm | Purpose |
|-----|---------|
| `multi_agent` | treatment: 21 agents, dynamic routing, grounding on |
| `baseline` | RQ1 control: one Gemini call (F53) |
| `all_departments` | RQ2 control: routing forced off |
| `no_grounding` | RQ3 control: external APIs off |

Arms run **per prompt, not per arm**, so a provider outage degrades every arm of
that prompt equally instead of ruining one arm. Results are written to SQLite after
each prompt, so an interrupted sweep keeps what it measured.

**Metrics refuse to impute.** A metric that cannot be computed records
`applicable=false` with a reason rather than scoring zero. F54 in particular does
*not* score a missing margin as 100% error — absence is already penalised by F56,
and double-counting it would inflate the apparent gap between arms. The report
lists unscored measurements by reason.

**Benchmark provenance is machine-checked.** F54 divides by the sector margin
benchmarks, so every entry carries a `source` and unsourced entries are flagged.
While any benchmark in use is unsourced, the report prints F54 under a
`PROVISIONAL` banner instead of presenting it as a finding. Fill
`evaluation/benchmarks.csv` with cited figures and the banner clears.

#### Financial-accuracy debugging (worth reporting in the paper)

The first sweep put multi-agent MAPE in the hundreds. Diagnosing it found **five
separate defects**, each fixed and regression-tested:

| Defect | Symptom |
|---|---|
| P&L opex ignored the cost agent's itemised total | fixed opex below the derived cost base |
| F54 compared a ramp-up year to a mature benchmark | a plausible −9.9% year 1 scored as a 182% error |
| Revenue drivers were unbounded | a ₹12 L salon projected at ₹9 crore/month by month 12 |
| Revenue ceiling trusted model-generated SOM alone | SOM came back at ₹3 crore for that ₹12 L salon |
| Y2/Y3 grew from the year-1 *total*, not the exit rate | revenue fell entering year 2; steady margin −1% while month 12 was +20% |

The fixes follow one principle, applied consistently: **where two agents assert the
same quantity, the derived figure wins over the asserted one.** Cost totals are
summed from line items, P&L opex is reconciled against that sum, and year-1 revenue
is capped at `min(SOM, 10 × budget)` — arithmetic on a number the user supplied,
which holds regardless of what any agent claims. Soft prompt instructions were not
enough; the model ignored "must not exceed SOM" repeatedly.

MAPE fell from ~180–450 to ~70–200. **The remaining error is run-to-run model
variance, not a defect.** Five runs of the identical prompt gave a standard deviation
of 103.8 for multi-agent against 21.2 for the baseline — a 7.6× spread versus 1.8× —
while the multi-agent *best* run (38.4) beat the baseline's best (50.0). Chasing the
mean further would be tuning to the metric.

```bash
# reproduce the variance measurement
python -m evaluation.harness --arms multi_agent baseline --prompts p01 --repeat 5 --label variance
```

That variance is itself a finding worth stating: decomposing the task into
specialists **compounds estimation variance**, because each agent's error
propagates through the chain (market sizing → revenue → P&L drivers → margin),
whereas the single-LLM baseline emits one margin directly. On financial accuracy
the baseline is currently the stronger arm, and the paper should say so.

#### Smoke-test findings (n≤5 — direction only, not results)

| Metric | multi_agent | baseline | Verdict |
|---|---|---|---|
| Financial accuracy (MAPE, lower better) | ~132 | **~41** | **baseline wins** |
| Plan completeness | **100.0** | 80.8 | multi-agent wins |
| Consistency | 97.8 | 100.0 | roughly tied |

RQ2 behaved as hypothesised: on the one prompt where routing actually skipped a
department, **17.3% token saving with a 0.0 pp completeness delta**.

RQ3's direction held — grounded MAPE below text-only — but Competitor Coverage is
**not yet measurable**, because it needs hand-verified ground truth in
`prompts.json`.

---

### Append-only state contract (F15)

An agent may write only to its own department's section. Cross-department writes
raise `StateContractViolation`. This is what makes the Consistency Score (F57)
measure real cross-department agreement rather than last-writer-wins artefacts.

```python
from app.models import Department, apply_department_patch

update = apply_department_patch(state, Department.FINANCE, {"break_even_month": 9})
# writing {"strategy": ...} from the Finance department raises StateContractViolation
```

---

## Project layout

```
mabgp/
├── docker-compose.yml            F62
├── .env.example                  F63
├── docs/
│   ├── PROJECT_SPEC.md           architecture + 65 features
│   └── FEATURE_PROMPT.md         AI IDE prompt templates
├── backend/
│   ├── requirements.txt          pinned versions
│   ├── pytest.ini
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py               FastAPI, /health (F64), /sessions (F51)
│   │   ├── config.py             F63
│   │   ├── core/logging.py       F64
│   │   ├── models/
│   │   │   ├── intent.py         F2–F5 schema
│   │   │   ├── departments.py    per-department output schemas
│   │   │   └── state.py          F14/F15/F16 SharedBusinessState
│   │   ├── llm/
│   │   │   ├── base.py           interface + FreeTierTracker
│   │   │   ├── groq_provider.py      F6
│   │   │   ├── gemini_provider.py    F7
│   │   │   ├── ollama_provider.py    F8
│   │   │   └── chain.py              F9 fallback chain
│   │   └── db/sqlite.py          F59/F60
│   └── tests/                    517 offline tests
├── frontend/                     React 18 + Vite
└── evaluation/                   F53–F58 benchmarking
```

---

## Research questions

| ID | Question | Metrics |
|----|----------|---------|
| RQ1 | Multi-agent pipeline vs single-LLM baseline quality? | Financial Accuracy, Completeness, Consistency |
| RQ2 | Does dynamic routing improve efficiency without quality loss? | Token/time savings, quality delta |
| RQ3 | Does real-world API grounding improve accuracy vs text-only? | Competitor Coverage, Financial Accuracy |

Baseline: same prompt → one Gemini Flash call → scored on the identical rubric.
Sample: 30+ prompts across sectors, budgets and locations (`evaluation/prompts.json`).

> **Model availability note.** The original spec named Gemini 1.5 Flash. Google has
> since retired it (404 for new API keys) and closed 2.5-flash to new users, so the
> project uses `gemini-3.5-flash-lite` for the STRUCTURED tier and
> `gemini-3.6-flash` for the F53 baseline. Both are configurable via
> `GEMINI_MODEL` / `GEMINI_BASELINE_MODEL`; the paper must report the models
> actually used, not the ones originally planned.

---

## Testing

```bash
cd backend
pytest                    # 517 tests
pytest -v                 # verbose
pytest tests/test_llm_chain.py
```

Every test runs offline. External HTTP is mocked with `respx`, so the suite
consumes zero free-tier quota and requires no credentials.

---

## Security note

The backend has **no authentication**. It is designed to run on localhost for a
research project. Add auth before exposing it to any network.
