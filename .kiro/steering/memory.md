# Memory — durable project knowledge

> Kiro steering document. Facts an agent must retain across sessions. Verified
> 10 September 2026; when reality and this file disagree, re-verify with the
> commands given, then update the file.

## 1. Environment gotchas (Windows, PowerShell)

- `PYTHONPATH` must include BOTH `backend` and the repo root:
  `C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro`.
- App Python is `..\.venv\Scripts\python.exe` (the venv sits at the repo root,
  not inside `backend/`). System `python` is used only for playwright
  rendering of `docs/orion/` PDFs and figures.
- PowerShell has no `&&` — use `;`.
- Set `$env:PYTHONIOENCODING="utf-8"` before demo scripts, or Unicode output
  dies with `UnicodeEncodeError` (a display failure, not a bug).
- Ports: backend 8080, Vite 5173, Ollama 11434, Chroma 8000. Frontend base URL
  via `VITE_API_BASE_URL`, default `http://localhost:8080`.
- `backend/pytest.ini`: `testpaths=tests`, `pythonpath = . ..`,
  `asyncio_mode=auto`, `--strict-markers`; the only marker is `allow_network`.
- Money in the operating layer is integer paise; divide by 100 for display.

## 2. Git — the truth (resolves a stale doc)

The repo IS a git repository: branch `main`, tracking `origin/main`, two
commits, HEAD `d2a048c`. The "**No git repo.** Nothing to revert to" line in
`AGENTS.md` (and copied into `CLAUDE.md`/`.cursorrules`) is STALE. Equally, do
not assume everything is committed: as of 10 Sep 2026 the tree was dirty —
modified `docs/project_structure.html`,
`frontend/src/components/ReportView.jsx`, `frontend/src/styles.css`; untracked
`docs/CODE_FLOW.md`, `docs/page_critique.md`, `docs/prototype.html`,
`docs/prototype_pages.js`, `docs/wireframes.html`,
`frontend/src/components/PipelineView.jsx`. `.gitignore` correctly excludes
`.env`, `.env.local`, `*.key`, `*.db`, `.venv/`, `node_modules/`, data paths and
evaluation results. NEVER commit `.env` — it holds live API keys. Commit
messages: English, Conventional Commits, short imperative subject.

## 3. Documentation drift ledger — trust runnable artifacts

| Claim | Where | Reality |
|---|---|---|
| 989 tests | AGENTS.md, WORK_REMAINING, OPERATING_LAYER | current — re-verify with pytest |
| 869 tests | CLAUDE.md, .cursorrules, HOW_TO_RUN | stale snapshot |
| 517 tests | README quick start | older snapshot |
| 162 kB bundle | AGENTS.md binding rules | stale; 188.62 kB after the operating UI (WORK_REMAINING §5.5), within tolerance |
| "no git repo" | AGENTS.md, CLAUDE.md, .cursorrules | false — see §2 |
| AgentOS "planner" cited as pattern source | design.md §6/§7 `inferences` | verified 10 Sep 2026 — `lib/openclaw/planner-core.ts` (MIT, 2,880 lines); shape adapted, no code ported |

`CLAUDE.md` and `.cursorrules` are older copies of `AGENTS.md`, not independent
sources. Rule: pytest output and `npm run build` output outrank every document,
including these steering files. Update the ledger when you measure a drift.

## 4. Naming hazard

`sessions.plan_json`, `run_summary()["plan"]` and `export_plan()` all mean the
FINISHED BUSINESS PLAN (F59). The pre-execution feature must therefore say
"planning report" everywhere — `planning_reports` table, `report_id`,
`planning_report_id` — and never "plan".

## 5. Test-suite rules

Fully offline: `backend/tests/conftest.py` monkeypatches `socket.connect` to
fail any non-loopback connection (`NetworkAccessAttempted`); the suite must
consume zero free-tier quota. Mock HTTP with `respx`; replace department
runners with `make_placeholder`; script the LLM with `ScriptedProvider` /
`DeadProvider` and point `sqlite.settings.sqlite_file` at a tmp path (the
`tests/test_api.py` `offline_api` fixture shows the full pattern). Add a
regression test for every change.

## 6. Free-tier budgets (why quota gating matters)

Groq 14,400 requests/day; Gemini 15 requests/minute and 1M tokens/day; Serper
2,500 searches/month; Google Places $200/month credit (card required).
`FreeTierTracker.snapshot()` (per provider) and `llm_client.health()` expose
live usage — the readiness layer reads them and must not re-implement them.

## 7. Invariants (short form)

Anchors are computed, never reported — no anchor table exists, nothing may
write or optimise against one (`tests/test_anchors.py` asserts it). Every LLM
call goes through `app.llm.llm_client`. Every generation-layer department
write goes through `apply_department_patch`. `app/models/departments.py` field
names are FROZEN. Free tiers only. Frontend dependencies are `react` and
`react-dom` only. User-facing copy is English.

## 8. Quick file map for the Planning flow

Read from: `app/intent/classifier.py` (`classify_intent`,
`PromptValidationError`), `app/orchestrator/routing.py`
(`resolve_departments`, line 58), `app/orchestrator/graph.py`
(`describe_graph`, line 149), `app/agents/registry.py`
(`describe_all_departments`, line 88), `app/llm/chain.py`
(`llm_client.health()`), `app/config.py` (`settings`, `warnings()`),
`app/main.py` (lifespan, routers, `/intent`, `/generate`, `/ws/generate`),
`app/db/sqlite.py` (SQL patterns to copy). Write to: the new
`app/planning/` package only.

## 9. Steering docs

These four files live in `.kiro/steering/` and Kiro offers them as context
automatically. Keep them truthful; update them on drift. The project's
authoritative documents remain `docs/HANDOVER.md` and its siblings — steering
files summarise and steer, they do not replace them.
