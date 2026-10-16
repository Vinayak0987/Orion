# Orion (`mabgp`) — Project Structure

Deep, file-by-file map of the repository after the restructure (Phases 1–4).

- **Canonical backend:** `backend2/` (Orion v2 — mission engine). The mature v1
  generation + operating engine has been merged into it under
  `backend2/app/generation/` (a self-contained namespace with its own
  `llm/`, `config.py`, `db/`, `core/logging`).
- **Legacy backend:** `backend/` is retained as the original v1 source and the
  reference 989-test suite. It can be archived or deleted once the merged suite
  in `backend2/tests/generation/` is verified green.

Legend: 📁 directory · 📄 file · ⚙️ config · 🧪 tests · 🗑️ safe to delete/ignored

---

## Repository root

```
kiro/
├─ 📁 backend2/          CANONICAL backend (v2 mission engine + merged v1 engine)
├─ 📁 backend/           LEGACY v1 backend (source of the merge; reference tests)
├─ 📁 frontend/          React 18 + Vite SPA
├─ 📁 evaluation/        Research harness (ablations, metrics, significance)
├─ 📁 scripts/           One-off generators (decks, figures, infographics)
├─ 📁 docs/              Design docs, research, diagrams, presentations
├─ 📁 plans/             Phased feature build specs (00_MASTER … 16_ERROR_HANDLING)
├─ 📁 contracts/         API/interface contracts
├─ 📁 data/              🗑️ runtime SQLite + chroma (gitignored)
├─ 📁 .kiro/             Kiro CLI config: agents, hooks, skills, steering
├─ 📁 .worktrees/        🗑️ git worktrees (gitignored; `operating-ready` active)
├─ 📄 docker-compose.yml ⚙️ backend + frontend + ollama + chromadb stack
├─ 📄 README.md
├─ 📄 AGENTS.md          AI-assistant contract + binding rules (source of truth)
├─ 📄 CLAUDE.md          (duplicate of AI rules — candidate to consolidate)
├─ 📄 .cursorrules       (duplicate of AI rules — candidate to consolidate)
├─ 📄 .env / .env.example ⚙️ secrets + template
├─ 📄 .gitignore
├─ 📄 TRUE_SYSTEM_DESIGN.md / SYSTEM_DESIGN.md / STREAMLINED_PLAN.md
├─ 📄 HOW_SYSTEM_WORKS.md / DESIGN_SYSTEM.md   (root design docs — see note)
└─ 📄 LeadMind_SecondPresentation (1) (1).pptx (candidate → docs/presentations/)
```

> **Note (Phase 3 cleanup suggestion):** the five root-level `*_DESIGN.md` /
> `*_PLAN.md` / `HOW_SYSTEM_WORKS.md` docs overlap with `docs/`. Recommended to
> move them under `docs/design/`. The `.pptx` belongs under `docs/presentations/`.
> `CLAUDE.md` + `.cursorrules` duplicate `AGENTS.md`; keep one source of truth.

---

## `backend2/` — canonical backend

```
backend2/
├─ 📄 requirements.txt   ⚙️ v2 deps + merged v1 engine deps (langgraph, groq,
│                            gemini, jinja2, xhtml2pdf, structlog, tenacity, …)
├─ 📄 pytest.ini         ⚙️ asyncio_mode=auto, testpaths=tests
├─ 📁 data/              🗑️ runtime stores (gitignored)
│  └─ 📁 chroma2/        vector fallback docs
├─ 📁 app/               application package
└─ 📁 tests/             test suites (v2 root + merged v1 under generation/)
```

### `backend2/app/` — v2 mission-engine

```
app/
├─ 📄 __init__.py
├─ 📄 main.py            FastAPI app. Lifespan: init_db → seed default agents →
│                        Mongo auth → init_generation(). Mounts v2 routers
│                        (health, missions, settings, uploads, workspace,
│                        knowledge, chat, auth) + the 4 generation routers.
├─ 📄 config.py          ⚙️ v2 Settings (pydantic-settings): sqlite path, log
│                        level, Mongo URI, CORS, feature flags.
├─ 📁 api/               HTTP routers (thin; delegate to stores/engine)
│  ├─ 📄 health.py          GET /health — service + dependency status
│  ├─ 📄 missions.py        mission CRUD + run triggers
│  ├─ 📄 chat.py            chat sessions + streaming
│  ├─ 📄 knowledge.py       document knowledge base endpoints
│  ├─ 📄 settings.py        per-user settings
│  ├─ 📄 uploads.py         file upload intake
│  └─ 📄 workspace.py       workspace/project endpoints
├─ 📁 missions/          the mission engine (planner → router → executor → engine)
│  ├─ 📄 engine.py          top-level orchestration loop
│  ├─ 📄 planner.py         decompose a mission into steps
│  ├─ 📄 router.py          route steps to agents/tools
│  ├─ 📄 executor.py        run a step; collect output
│  ├─ 📄 events.py          mission event types / stream payloads
│  └─ 📄 store.py           mission persistence (SQLite)
├─ 📁 agents/            v2 runtime agents (NOT the 21 v1 department agents)
│  ├─ 📄 defaults.py        seed_defaults() — 7 built-in agents
│  └─ 📄 store.py           agent definitions persistence
├─ 📁 tools/             built-in tools callable by agents
│  ├─ 📄 registry.py        tool registry / dispatch
│  ├─ 📄 web_search.py      web search tool
│  └─ 📄 document_rag.py    RAG over uploaded docs
├─ 📁 knowledge/         document knowledge base
│  ├─ 📄 store.py           chroma-backed store
│  └─ 📄 fallback.py        JSON fallback when chroma unavailable
├─ 📁 workspace/ 📄 store.py    workspace/project persistence
├─ 📁 traces/    📄 store.py    execution-trace persistence
├─ 📁 settings/  📄 store.py    user settings persistence
├─ 📁 chat/      📄 store.py    chat session persistence
├─ 📁 auth/              v2 auth (MongoDB Atlas user/website data layer)
│  ├─ 📄 router.py          /auth/signup|login|refresh|logout|me
│  ├─ 📄 store.py           Mongo-backed user store (configurable/injectable)
│  ├─ 📄 security.py        Argon2id hashing + JWT sign/verify
│  ├─ 📄 deps.py            get_current_user dependency
│  └─ 📄 models.py          auth pydantic models
├─ 📁 core/
│  ├─ 📄 crypto.py          Fernet encryption for API keys at rest
│  └─ 📄 uploads.py         upload parsing (pdf/docx text extraction)
├─ 📁 llm/               v2 LLM client (separate from generation's llm/)
│  ├─ 📄 client.py          unified client
│  ├─ 📄 providers.py       Groq/Gemini/Ollama provider adapters
│  ├─ 📄 ratelimit.py       token-bucket rate limiting
│  └─ 📄 repair.py          JSON repair for malformed LLM output
├─ 📁 db/
│  ├─ 📄 sqlite.py          v2 connection + init_db
│  └─ 📄 schema.sql         v2 schema DDL
└─ 📁 generation/        ★ MERGED v1 generation + operating engine (namespaced)
```

### `backend2/app/generation/` — merged v1 engine ★

Self-contained; all internal imports rewritten `app.* → app.generation.*`.

```
generation/
├─ 📄 __init__.py        package marker
├─ 📄 lifecycle.py       init_generation() / shutdown_generation() — called from
│                        app.main lifespan (configure logging, init sqlite +
│                        operating + planning tables, close llm client).
├─ 📄 app_routes.py      APIRouter with the v1 inline endpoints:
│                        /health-gen, /intent, /generate, /sections,
│                        /sessions*, /ws/generate.  (/health renamed to
│                        /health-gen to avoid clash with v2 /health.)
├─ 📄 config.py          ⚙️ v1 Settings (budget, places/serper flags, dynamic
│                        routing, warnings()). Independent of v2 config.
├─ 📁 agents/            the 21 department agents across 5 departments
│  ├─ 📄 base.py            Agent / AgentSpec, context helpers
│  ├─ 📄 registry.py        DEPARTMENT_RUNNERS, agents_for(), get_runner()
│  ├─ 📄 subgraph.py        build_department_subgraph() (LangGraph)
│  ├─ 📄 strategy.py / strategy_scoring.py        Strategy dept
│  ├─ 📄 marketing.py / marketing_checks.py       Marketing dept
│  ├─ 📄 branding.py / branding_checks.py         Branding dept
│  ├─ 📄 finance.py / finance_cashflow.py         Finance dept
│  ├─ 📄 operations.py / operations_feasibility.py Operations dept
│  └─ 📄 benchmarks.py      shared benchmark data
├─ 📁 intent/           prompt → structured intent (F1–F5)
│  ├─ 📄 classifier.py      classify_intent(), PromptValidationError
│  ├─ 📄 taxonomy.py        business-type taxonomy
│  ├─ 📄 budget_parser.py / location_parser.py    field parsers
│  └─ 📄 schema.py          intent schema
├─ 📁 models/           frozen domain models
│  ├─ 📄 departments.py     FROZEN department field schemas (metrics depend on)
│  ├─ 📄 state.py           orchestration state container
│  └─ 📄 intent.py          BusinessIntent
├─ 📁 orchestrator/     the generation DAG
│  ├─ 📄 runner.py          orchestrate() entry point
│  ├─ 📄 graph.py           build_graph(), describe_graph()
│  ├─ 📄 routing.py         resolve_departments(), RoutingDecision
│  ├─ 📄 completeness.py    score_completeness(), contradiction detection
│  └─ 📄 progress.py        ProgressEmitter / ProgressEvent (WS streaming)
├─ 📁 operating/        the operating layer (runs a plan as a living company)
│  ├─ 📄 ledger.py          append-only event substrate (only writable store)
│  ├─ 📄 anchors.py         metrics DERIVED from ledger (never written)
│  ├─ 📄 constitution.py    hard constraints enforced in the call path
│  ├─ 📄 governance.py      gate chain + append-only audit trail
│  ├─ 📄 loops.py           loop registry + topology invariants
│  ├─ 📄 monitors.py        the four monitoring loops
│  ├─ 📄 monitoring.py      wires monitors + reflection into scheduler
│  ├─ 📄 scheduler.py       clock-injected cadence kernel
│  ├─ 📄 memory.py          per-department isolated memory stores
│  ├─ 📄 reflection.py      learning grounded in measured anchor deltas
│  ├─ 📄 departments.py     the five department loops
│  ├─ 📄 environment.py     environment model
│  ├─ 📄 ablation.py        ablation switches for research
│  └─ 📄 api.py             operating-layer APIRouter
├─ 📁 planning/         pre-execution inspect-and-confirm flow
│  ├─ 📄 service.py         report builder (intent, routing, roster, estimates)
│  ├─ 📄 store.py           planning_reports table + status machine
│  ├─ 📄 api.py             /planning routes
│  ├─ 📄 plan_models.py / plan_store.py / plan_api.py   execution plan layer
│  ├─ 📄 compile.py         compile a confirmed report into an execution plan
│  ├─ 📄 executor.py        run an execution plan
│  └─ 📄 policy.py          execution policy / guards
├─ 📁 output/           business-package assembly + export
│  ├─ 📄 sections.py        SECTION_ORDER, SECTIONS_BY_KEY, describe_sections()
│  ├─ 📄 package.py         BusinessPackage, GenerationMetadata
│  ├─ 📄 html.py            render_html()
│  ├─ 📄 pdf.py             render_pdf(), PdfUnavailable, pdf_health()
│  └─ 📁 templates/ 📄 report.html.j2   Jinja2 report template
├─ 📁 apis/             external grounding APIs (free tiers)
│  ├─ 📄 places.py          Google Places / provider selection
│  ├─ 📄 serper.py          Serper web search
│  ├─ 📄 freshness.py       result freshness checks
│  └─ 📄 cache.py           knowledge_cache (chroma-backed)
├─ 📁 llm/              v1 LLM chain (its own, separate from v2 llm/)
│  ├─ 📄 chain.py           llm_client singleton, LLMClient, JSONParseError
│  ├─ 📄 base.py            ProviderName, ModelTier, LLMRequest/Response, errors
│  ├─ 📄 groq_provider.py / gemini_provider.py / ollama_provider.py
├─ 📁 core/ 📄 logging.py    configure_logging(), bind_session(), clear_session()
└─ 📁 db/  📄 sqlite.py      v1 connection + init_db + session CRUD
```

### `backend2/tests/`

```
tests/
├─ 📄 conftest.py       🧪 v2 temp_db (autouse) + skips tests/generation/ so the
│                          merged v1 suite manages its own namespaced DB.
├─ 📄 test_auth.py / test_chat.py / test_db.py / test_engine.py
├─ 📄 test_memory.py / test_settings.py / test_units.py
├─ 📄 test_uploads.py / test_workspace.py
└─ 📁 generation/       🧪 MERGED v1 suite (imports rewritten to app.generation.*)
   ├─ 📄 conftest.py       network-block guard + gen_temp_db (inits v1 engine)
   ├─ 📄 test_agents.py, test_orchestrator.py, test_intent.py, test_apis.py
   ├─ 📄 test_output.py, test_planning_*.py, test_plan_*.py
   ├─ 📄 test_operating_*.py, test_anchors.py, test_ledger.py, test_loops.py,
   │     test_governance.py, test_constitution.py, test_monitors.py, …
   ├─ 📄 test_<department>_schema|checks|synthesis.py  (strategy/marketing/
   │     branding/finance/operations)
   └─ 📄 test_api.py / test_planning_api.py / test_plan_api.py / test_operating_api.py
         (patch app.generation.app_routes; TestClient over app.main:app)
```

---

## `backend/` — legacy v1 (reference)

Original pre-merge source. Same module layout now living under
`backend2/app/generation/`. Keep until the merged suite is verified, then
archive or delete.

```
backend/
├─ 📄 requirements.txt, pytest.ini, Dockerfile
├─ 📁 app/   (agents, apis, intent, models, operating, orchestrator, output,
│            planning, llm, core, db, auth, config.py, main.py,
│            + later additions: chat, companies, dashboard, missions, notifications)
├─ 📁 tests/ (the canonical 989-test suite)
└─ 📁 data/  🗑️ runtime stores (gitignored)
```

---

## `frontend/` — React 18 + Vite

```
frontend/
├─ ⚙️ package.json, vite.config.js, tailwind.config.js, postcss.config.js
├─ 📄 index.html, Dockerfile
├─ 📁 public/ 📄 welcome-circuit.png
└─ 📁 src/
   ├─ 📄 main.jsx            app entry
   ├─ 📄 App.jsx / PlatformApp.jsx     root shells
   ├─ 📄 api.js / missionApi.js / chatApi.js     backend clients
   ├─ 📄 settingsLocal.js    local settings persistence
   ├─ 📄 index.css / styles.css
   ├─ 📁 auth/               auth screens, session, validation, theme, authApi
   ├─ 📁 landing/            landing page + circuit visuals
   ├─ 📁 intro/              intro animation / brand dust
   ├─ 📁 dashboard/          Orion dashboard shell, mock data, icons
   ├─ 📁 views/              PlanView, ActivityView, WorkView, BusinessView,
   │                         LoopsView, plan/
   ├─ 📁 operating/          operating-layer panels (ledger, anchors, loops,
   │                         governance, review queue, memory inspector, …)
   ├─ 📁 components/         shared UI (ReportView, Status, HistoryList, forms,
   │                         ui/, layout/, views/)
   ├─ 📁 data/               navigation.js, lanConfig.js
   ├─ 📁 hooks/              usePolling.js
   ├─ 📁 lib/                shared helpers
   └─ 📁 utils/              exportDoc.js
```

---

## `evaluation/` — research harness

```
evaluation/
├─ 📄 harness.py / baseline.py / metrics.py / operating_metrics.py
├─ 📄 significance.py (Wilcoxon/t-tests) / report.py
├─ 📄 ablation_harness.py / benchmarks.csv / prompts.json
└─ 📁 results/   🗑️ generated csv/json/md (gitignored)
```

## `scripts/` — generators

```
scripts/
├─ 📄 make_deck.py / make_figures.py / make_infographic.py /
│     make_full_infographic.py / make_ipo_docs.py
├─ 📄 ablation_report.py / autonomy_demo.py / operating_demo.py
```

## `docs/` — documentation

```
docs/
├─ 📄 HANDOVER.md          ★ read first: full project state
├─ 📄 PROJECT_STRUCTURE.md this file
├─ 📄 PROJECT_SPEC.md / CODE_FLOW.md / OPERATING_LAYER.md /
│     PLANNER_SUBSYSTEM_DESIGN.md / INPUT_PROCESSING_OUTPUT.md
├─ 📄 AGENT_FLOW_EXPLAINED.md / HOW_TO_RUN.md / CONFIGURATION_TODO.md
├─ 📄 WORK_COMPLETED.md / WORK_REMAINING.md / PROGRESS_SUMMARY.md
├─ 📄 *_DEPARTMENT_PLAN.md (marketing/branding/finance/operations)
├─ 📄 FRONTEND_PROMPT.md / FEATURE_PROMPT.md / RESUME_PROMPT.md
├─ 📄 prototype.html / wireframes.html / project_structure.html / orion_system_ui.*
├─ 📁 orion/     generated decks, infographics, PDFs, src/ generators
├─ 📁 paper/     PAPER.md, FIGURES.md, REPRODUCIBILITY.md, figures/
├─ 📁 research/ · 📁 analysis/ · 📁 decisions/ · 📁 retros/
```

## `.kiro/` — Kiro CLI config

```
.kiro/
├─ 📁 steering/   phases.md, architecture.md, memory.md, design.md
├─ 📁 agents/ · 📁 hooks/ · 📁 settings/
├─ 📁 skills/     installed agent skills (superpowers, vercel, addyosmani, …)
└─ 📁 kit/        workflows, templates, plan, powers, skills-download
```

---

## Changes applied in this restructure

- **Phase 1:** removed all `__pycache__/` + `.pytest_cache/`, the orphaned
  `.worktrees/missions/` copy, `plan_all_feateuers.zip`, and stale
  `frontend/_*.log|err` + `backend2/_run.log|err` (the latter via `git rm`).
- **Phase 2a:** deleted `.venv/` (recreate per the commands below).
- **Phase 2b:** merged the v1 engine into `backend2/app/generation/` (Path 1 —
  namespaced, self-contained), wired into `app.main`, merged tests + deps.
- **Phase 4:** `.gitignore` now ignores `.worktrees/`, run logs, and
  `backend2/data/`.

## Pending (requires running commands — not executed per request)

See the command list provided separately to: recreate the venv, install
`backend2/requirements.txt`, and run the merged test suite to verify.
