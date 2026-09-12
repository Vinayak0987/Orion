# Phases — Planning Report implementation plan

> Kiro steering document. Dependency-ordered phases for the flow specified in
> `design.md`. Each phase lists files, work, tests and the exact validation
> command. Do not start a phase before the previous phase's exit criteria hold.

## Ground rules (all phases)

1. Add a regression test for every change; the suite stays fully offline.
2. No new dependencies; no renames of frozen fields; English copy only.
3. All SQL for this feature lives in the new `app/planning/` package.
4. Run the phase validation, then the full suite, before moving on.
5. Nothing costs money; if a step would, stop and flag it.

## Phase 0 — Baseline and safety net

Capture the current state so every later change is measurable.

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
cd C:\Users\Vinayak\Desktop\kiro\backend
..\.venv\Scripts\python.exe -m pytest -q            # expect: 989 passed
git -C C:\Users\Vinayak\Desktop\kiro status --short  # note the dirty files
```

**Exit:** 989 passed. If not, the tree changed since this document was
written — stop and re-verify the anchors in `architecture.md` before
proceeding. Note the dirty files from `git status`; never fold unrelated
uncommitted work into this feature's commits.

## Phase 1 — Planning store (`app/planning/store.py`)

**Build:** the `planning_reports` DDL from `design.md` §5, plus
`init_planning()` (idempotent `executescript`), `create_report(**fields)`,
`get_report(id)`, `list_reports(limit, offset)`, `confirm_report(id, by)` with
a legal-transition guard, `mark_executed(id, session_id)`, a TTL check helper
(24 h), and `_decode_report` following `_decode_session`. Timestamps via the
`_now()` UTC-ISO pattern; JSON columns decode to dicts/lists with `[]`/`None`
defaults. No `pending` row is ever stored — creation computes everything, then
inserts a final `ready` or `blocked` row.

**Tests (`tests/test_planning_store.py`):** create/get/list roundtrip; decode
defaults; confirm only `ready` → `confirmed` (every other status is rejected);
`mark_executed` sets `session_id` + `executed_at`; TTL boundary. Use the
tmp-path DB fixture pattern from `tests/test_api.py`.

**Validation:**
```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_planning_store.py -q
..\.venv\Scripts\python.exe -m pytest -q
```

**Exit:** new tests green; full suite green (total now above 989); the table
creates idempotently under a temporary database.

## Phase 2 — Report builder (`app/planning/service.py`)

**Build:** `build_report(prompt, force_all=False, client=None) -> dict`:

1. `validate_prompt` — `PromptValidationError` propagates (422 at the route).
2. `classify_intent(prompt, client=client)` — at most one LLM call. Flag the
   heuristic path from the provider-availability snapshot already collected
   (the classifier's documented fallback fires only when every provider is
   unavailable); do NOT modify `classifier.py`.
3. `resolve_departments(intent, force_all=force_all)`.
4. Agent enumeration: `describe_all_departments()` filtered to the ACTIVE
   departments; flatten to per-agent entries with `AgentSpec` tier/max_tokens
   per `design.md` §6. No topology is re-derived.
5. Readiness: `llm_client.health()`, the `/health`-style `SELECT 1` database
   ping, `settings.warnings()`, `select_provider()`; blockers per
   `design.md` §7.
6. Estimates: `intent_llm_calls`, `agent_llm_calls`, and the
   `600 + Σ spec.max_tokens` token bound.
7. Persist via the store; return the decoded report.

**Tests (`tests/test_planning_service.py`):** offline with scripted/dead
providers; ready vs blocked; 21 vs 17 agents (physical vs digital prompt);
force-all path; estimate arithmetic; heuristic warning when no provider is up;
the `inferences` entries and the §7 warning derivation per design.md §10.

**Validation:** phase tests, then the full suite, as in Phase 1.

**Exit:** a complete report builds with zero network access and correct
blocker logic.


## Phase 3 — API routes (`app/planning/api.py`)

**Build:** the router from `design.md` §8 (`prefix="/planning"`,
`tags=["planning"]`); wire `init_planning()` into the `main.py` lifespan next
to `init_all()` (idempotent); `include_router` beside the operating router.
Thin routes only — every rule lives in the service/store, never in a handler
(the operating router's own rule). `422` carries the classifier's message
verbatim, like `/intent`.

**Tests (`tests/test_planning_api.py`):** 201 shape (ready and blocked);
422 on a short prompt; list pagination caps; get 404; confirm 200/409 on each
illegal transition; router stays offline via the scripted-provider fixture.

**Validation:** phase tests, then the full suite.

**Exit:** all four routes behave per §8 under TestClient; OpenAPI
(`/docs`) shows the planning tag; no generation-layer route changed.

## Phase 4 — Frontend (`#/plan`)

**Build:** `api.js` `planning` namespace; `App.jsx` adds `"plan"` to `ROUTES`
and the nav; new `views/PlanView.jsx` plus small components
(`PlanForm`, `ReadinessBanner`, `AgentRoster`, `EstimatesPanel`,
`ConfirmBar`) following existing class names and `Status`/`callout` patterns;
confirm hands off to `#/generate` with the prompt and report id, and
`streamGeneration` gains the optional `planningReportId` sent as
`planning_report_id`. All copy English and cost-honest. No new dependencies.

**Validate:** `cd frontend; npm run build` — record the bundle size; no new
packages in `package.json`; spot-check the flow with the backend running
locally.

**Exit:** build passes; bundle growth reported and small; the operator can
create → read → confirm a report end to end against the real backend.

## Phase 5 — Run linkage and documentation

**Build:** `/ws/generate` accepts optional `planning_report_id` with the
§8 validations (error event `kind: "planning"`, no run, no quota); on
`result`, `mark_executed`. **Docs:** add a Planning section to
`docs/HOW_TO_RUN.md`; list the routes in `README.md`; note the feature in
`docs/WORK_REMAINING.md`; refresh the test count in `AGENTS.md` and correct
its stale "**No git repo.**" line (the repo exists — `main`, `origin/main`;
`CLAUDE.md`/`.cursorrules` are copies of the same text and get the same
one-line fix).

**Tests:** in `tests/test_api.py` (or a new `test_planning_linkage.py`):
confirm → run with placeholder runners → `executed` + `executed_session_id`;
rejections for unknown id, blocked, expired, mismatched prompt; absence of the
field keeps today's behaviour byte-identical (the harness path).

**Exit:** linkage green offline; docs updated; no evaluation-harness
behaviour change (`planning_report_id` never sent there).

## Phase 6 — Full validation and acceptance

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
cd C:\Users\Vinayak\Desktop\kiro\backend
..\.venv\Scripts\python.exe -m pytest -q          # whole suite, still offline
cd ..\frontend
npm run build
```

**Acceptance checklist:**

- [ ] 989 baseline + all new tests pass, fully offline, socket guard intact
- [ ] Report persisted for every create; no `pending` rows ever observable
- [ ] Physical prompt → 21 agents; digital prompt → 17 + skipped Operations;
      force-all → 21 with the RQ2 warning
- [ ] All-providers-down → `blocked` with the two real blockers; zero-key run
      (Ollama up) → `ready` with degraded-mode warnings
- [ ] Confirm is free (no LLM call); run spends only after a `confirmed` report
- [ ] Expired report → 409 on confirm; linkage rejects it
- [ ] Frontend shows estimate as an upper bound; copy is English
- [ ] No frozen field renamed; no new dependency; no operating-layer change
- [ ] Commits: one per phase, Conventional Commits, English
      (e.g. `feat(planning): add planning report store`)

## Summary

| Phase | Deliverable | New tests |
|---|---|---|
| 0 | baseline verified | — |
| 1 | `planning_reports` store | store suite |
| 2 | report builder + readiness | service suite |
| 3 | `/planning` routes | API suite |
| 4 | `#/plan` frontend | build + manual |
| 5 | WS linkage + docs | linkage suite |
| 6 | full validation | acceptance above |

Out of scope (explicitly): plan editing, auth, TTL reaper, operating-layer
changes, reusing report intent at run time, `/generate` HTTP linkage.

