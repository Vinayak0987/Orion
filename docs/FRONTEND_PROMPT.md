# Frontend prompt

A prompt to hand to an AI IDE (Cursor, Claude Code, Windsurf, Copilot, Kiro) to
build the Orion three-layer interface. Everything below was verified against the
running code, not assumed. Paste from the marked line down.

Two things to know before you use it. The endpoints under "Operating layer API" do
not exist yet ? the data is in SQLite but nothing serves it, so the prompt asks for
those routes to be written first. And the frontend currently depends on `react` and
`react-dom` only, at a 162 kB bundle; that constraint is load-bearing and the prompt
enforces it.

---
---
--- PASTE FROM HERE ---

You are extending the frontend of **Orion**, an AI Business Operating System. A
React + Vite app already exists and works. Your task is to add the **three-layer
operating interface** alongside it without breaking what is there.

Read these first: `docs/OPERATING_LAYER.md`, `docs/WORK_COMPLETED.md`,
`frontend/src/api.js`, `frontend/src/styles.css`.

## Non-negotiable constraints

1. **Dependencies are frozen.** `frontend/package.json` depends on `react@18.3.1`
   and `react-dom@18.3.1` only, dev-deps `vite@5.4.11` and
   `@vitejs/plugin-react@4.3.4`. **Do not add any package** ? no router, no state
   library, no chart library, no icon library, no CSS framework. The current bundle
   is 162 kB and must stay in that region. Charts are hand-written inline SVG using
   `path`, `rect`, `circle` and `line`. Icons are inline SVG or text.
2. **Reuse the existing design tokens** from `frontend/src/styles.css`. Do not
   introduce a new palette:
   `--bg:#f5f7fa  --panel:#ffffff  --ink:#1f2733  --muted:#6b7480  --line:#e2e7ee
    --primary:#1f3a5f  --primary-soft:#eaf0f7  --ok:#15803d  --warn:#b45309
    --bad:#b91c1c  --radius:8px`
3. **All backend access goes through `frontend/src/api.js`.** Extend that module;
   never call `fetch` from a component. It reads `VITE_API_BASE_URL`, defaulting to
   `http://localhost:8080`.
4. **Accessibility is required, not optional.** Every SVG chart needs a `<title>`
   and a `<table>` fallback for screen readers. Keyboard focus must be visible.
   Colour must never be the only carrier of meaning ? pair it with text or a shape.
5. **No auth exists.** The backend has no authentication. Do not add a login
   screen; do not invent a user model. Assume localhost.
6. Routing must be hand-rolled from `window.location.hash` plus `useState`. No
   router package.

## The architecture you are building an interface for

Orion has two layers. The **generation layer** turns one sentence into a founding
business plan using 21 agents across five departments (Strategy, Finance,
Branding, Marketing, Operations). The **operating layer** then runs that plan as a
living company on department cadences.

One concept governs the whole UI and you must not undermine it:

> **Anchors are computed, never reported.** Every number the business is judged by
> is derived by code from an append-only ledger. No agent can write one. Proxy
> metrics, by contrast, are what departments watch day to day and *can* be gamed.

The interface must make that distinction visible at all times. An anchor and a
proxy must never look alike. Suggested treatment: anchors get a small lock glyph
and a "computed from N ledger entries" provenance line; proxies are visually
lighter and labelled "proxy". If a user cannot tell which is which at a glance,
the interface has failed at its main job.

## Layer separation ? the core requirement

Three views, strictly separated. Do not blend them. The questions "how is the
business doing?", "what is being worked on?" and "what exactly did that loop do at
14:32?" have almost nothing in common, and mixing them produces a screen that
serves nobody.

### Layer 1 ? Business View  `#/business`

For someone asking whether the company is healthy.

- **Anchor board.** The 19 anchors, grouped: money (revenue, COGS, opex,
  marketing spend, capex, cash balance, gross profit, net profit), margins (gross
  margin %, net margin %), customers (acquired, churned, active, churn %,
  retention %), unit economics (CAC, ARPC), delivery (SLA breaches, tasks
  completed). Each shows value, unit, and the entry count it was derived from.
  Anchors with fewer than 5 contributing entries are marked **thin evidence** ?
  a metric resting on three events and one resting on three thousand must not look
  alike.
- A value of `null` means **not computable**, not zero. Render it as "not yet
  measurable" with the reason. Never show 0 for absent evidence; the backend
  deliberately refuses to impute and the UI must not undo that.
- **Anchor trend**, inline SVG line chart from the anchor history endpoint. Plot
  the anchor and, where one exists, the corresponding proxy on the same axes ?
  divergence between them is the single most important thing this product shows.
- **Open findings**, worst first: severity chip, kind, department, the anchor cited
  and its delta. Every finding cites an anchor movement; if one does not, that is a
  bug worth surfacing rather than hiding.
- **Departments strip**: five cards with name, objective, last-run time, and its
  proxy and anchor side by side.

### Layer 2 ? Work View  `#/work`

For someone asking what is happening and what needs a decision.

- **Review queue**, the primary element. Pending decisions ordered
  irreversible ? subjective ? elevated ? routine. Each row: department, action
  kind, amount, risk, and the reason it was queued. Actions: **Approve**,
  **Reject**, **Return for revision**. Approve and reject both require a named
  human ? the field is mandatory and the backend records it. Show a confirmation
  step for anything irreversible.
- Make clear that **an approval does not unlock a hard constraint**. If a decision
  would violate the Constitution it will still be blocked at execution. Surface
  that in the UI rather than letting a user discover it after approving.
- **Decision history**: state, risk, who decided, outcome. Blocked decisions must
  show the rule id that blocked them (e.g. `C4_NO_CUSTOMER_DATA_DELETION`).
- **Constitution panel**, read-only, listing all 7 rules with severity and
  rationale. Label it plainly: these are code, not settings, and cannot be edited
  from the UI.
- **Cadence status**: each loop with its cadence, last run, run count, whether a
  handler is registered, and whether it is currently in flight.

### Layer 3 ? Activity View  `#/activity`

For someone debugging.

- **Loop run log**, newest first: loop, status (completed / failed /
  skipped_in_flight / skipped_no_handler), duration, and the result payload
  expandable as formatted JSON.
- **Ledger tail**: sequence, kind, department, actor, amount or quantity, memo.
  State visibly that this is append-only and cannot be edited.
- **Audit trail** per decision: every stage traversed, including halts, with actor
  and timestamp.
- **Memory inspector**: pick a department, see its four typed stores with counts,
  and browse entries with retrieval counts. Make the isolation legible ? a
  department's store shows only its own entries, and that is the point.

### Loop Graph view  `#/loops`

An inline SVG node-graph of the control topology, rendered from
`GET /operating/loops`.

- Circular nodes, hue-coded by kind: execution, monitor, learning, anchor
  (with a lock), human.
- Solid edges for work and data flow; dashed for control and evaluation signals.
- **Show that every cycle terminates at an anchor or a human.** If
  `unterminated_cycles` is non-empty, render those edges in `--bad` with a warning
  ? that would mean an invalid topology is running, which the backend refuses at
  registration, so it should always be empty. Surfacing it anyway is a check on
  the backend, not decoration.
- A legend on the graph. Do not rely on hue alone.

## Operating layer API ? write these routes first

**These endpoints do not exist yet.** The data is all in SQLite but nothing serves
it. Add them to `backend/app/main.py`, thin, calling only existing functions, with
tests in `backend/tests/test_api.py` following the patterns already there.

| Route | Returns | Backed by |
|---|---|---|
| `GET /operating/anchors?company_id=` | anchor name ? {value, unit, entries, thin, note} | `anchors.read_only_view(company).anchors` |
| `GET /operating/anchors/history?company_id=&points=30` | series per anchor over recent ledger sequence marks | `monitoring.anchors_at(company, seq)` sampled |
| `GET /operating/findings?company_id=&limit=` | findings, worst severity first | `monitoring.open_findings` |
| `GET /operating/decisions?company_id=&state=` | decision rows | `governance.review_queue` and a new list-by-state helper |
| `POST /operating/decisions/{id}/approve` | body `{by}` ? updated decision | `governance.approve` |
| `POST /operating/decisions/{id}/reject` | body `{by, reason}` | `governance.reject` |
| `POST /operating/decisions/{id}/return` | body `{by, reason}` | `governance.return_for_revision` |
| `GET /operating/audit/{decision_id}` | ordered audit rows | `governance.audit_for` |
| `GET /operating/constitution` | the 7 rules | `constitution.describe()` |
| `GET /operating/loops` | topology, cycles, unterminated_cycles, valid | `loops.default_graph().describe()` |
| `GET /operating/schedule?company_id=` | per-loop cadence state | `Scheduler.status(company)` |
| `GET /operating/runs?company_id=&loop_id=&limit=` | loop run log | `scheduler.run_history` |
| `GET /operating/ledger?company_id=&limit=` | ledger tail, newest first | `ledger.read` reversed |
| `GET /operating/memory?company_id=&department=` | typed counts and entries | `memory.stats`, `memory.retrieve` |
| `GET /operating/departments` | the five profiles with proxy and anchor | `departments.PROFILES` |
| `POST /operating/tick?company_id=` | run due loops once, return outcomes | `build_scheduler().run_due` |

Two API rules. Approve and reject **must** require a non-empty `by`; the backend
raises `ValueError` without it and the route should return 422, not 500. And
`POST /operating/tick` is the manual trigger for demonstrations ? the real driver
is the scheduler, so label it in the UI as a manual tick, not as "run the
business".

Data shapes worth knowing exactly:

```
anchor  = { name, value: number|null, unit: "INR"|"%"|"count", entries: int,
            thin: bool, note: string }
finding = { severity: "critical"|"high"|"medium"|"low",
            kind: "proxy_divergence"|"proxy_unsupported"|"department_conflict"
                  |"metric_stale"|"objective_stale",
            department, anchor, anchor_delta: number, message, detected_at,
            escalated: 0|1 }
decision= { id, company_id, department, actor, action_kind, amount_minor: int,
            description, state, risk, reason, decided_by, created_at }
loop    = { id, kind: "execution"|"monitor"|"learning"|"anchor"|"human",
            sends_to: [], monitors: [], evaluation_signal, cadence_seconds }
```

`amount_minor` is **integer paise**. Divide by 100 for display and never do
arithmetic on the divided value ? the backend keeps money in integers deliberately,
and the UI must not reintroduce float drift.

## Existing endpoints ? do not change them

`GET /health`, `POST /intent`, `POST /generate`, `GET /sections`,
`GET /sessions`, `GET /sessions/{id}`, `DELETE /sessions/{id}`,
`GET /sessions/{id}/package`, `GET /sessions/{id}/sections/{key}`,
`GET /sessions/{id}/report`, `GET /sessions/{id}/report.pdf`,
`WEBSOCKET /ws/generate`.

The existing generation UI (`PromptForm`, `ProgressPanel`, `ReportView`,
`HistoryList`) keeps working unchanged at `#/generate`. Add a top-level nav:
Generate ? Business ? Work ? Activity ? Loops.

## Files to create

```
frontend/src/
  operating/
    AnchorBoard.jsx        L1 anchor grid, thin-evidence marking, null handling
    AnchorTrend.jsx        inline SVG line chart, anchor vs proxy, a11y table
    FindingsList.jsx       severity-ordered, each citing an anchor delta
    DepartmentStrip.jsx    five cards, proxy and anchor side by side
    ReviewQueue.jsx        approve / reject / return, named human required
    DecisionHistory.jsx    with blocking rule ids
    ConstitutionPanel.jsx  read-only, 7 rules
    CadenceStatus.jsx      per-loop schedule state
    RunLog.jsx             L3 loop runs, expandable JSON
    LedgerTail.jsx         L3 append-only ledger
    AuditTrail.jsx         L3 per-decision passage
    MemoryInspector.jsx    L3 four typed stores per department
    LoopGraph.jsx          inline SVG topology with legend
  views/
    BusinessView.jsx
    WorkView.jsx
    ActivityView.jsx
    LoopsView.jsx
  hooks/
    usePolling.js          interval fetch with cleanup, pause when tab hidden
```

Extend `api.js` with an `operating` namespace mirroring the routes above.

## Behaviour

- **Polling, not sockets**, for operating data. There is no event bus yet. Poll
  every 5 s on Business and Work, 3 s on Activity, and pause when
  `document.hidden`. Do not invent a WebSocket endpoint that does not exist.
- **Loading and empty states are distinct.** "Loading" is not "no data", and "no
  data" is not "zero". A company with no ledger entries should say so, not show a
  wall of zeros.
- **Errors are shown, not swallowed.** If the backend is unreachable, say which
  URL failed, exactly as the existing `streamGeneration` does.
- Every mutation refetches the affected list rather than optimistically patching
  local state. Governance state transitions are validated server-side and a local
  guess can be wrong.

## Definition of done

1. `npm run build` succeeds; bundle stays within roughly 20% of 162 kB.
2. `package.json` dependencies are unchanged.
3. All three layers render against a live backend seeded by
   `python -m scripts.autonomy_demo --days 90`.
4. Anchors and proxies are visually distinguishable without reading the labels.
5. A `null` anchor renders as "not yet measurable", never as 0.
6. Approving a decision without a name is rejected by the UI before it reaches the
   API.
7. A blocked decision shows the rule id that blocked it.
8. The loop graph shows zero unterminated cycles for the default topology.
9. Every chart has a `<title>` and a table fallback.
10. New backend routes have tests, and the full suite still passes ? 869 tests,
    fully offline. Run:
    `cd backend; python -m pytest -q` with
    `PYTHONPATH=<repo>\backend;<repo>`.

## What not to do

- Do not add dependencies.
- Do not let a department appear to report its own anchor. Departments propose
  work and record events; anchors are computed. If a screen implies otherwise it
  contradicts the architecture.
- Do not show a proxy and an anchor with identical styling.
- Do not add an "edit Constitution" affordance. Those rules are code.
- Do not imply the system runs unsupervised. The gate chain is the product; a UI
  that hides the queue defeats it.
- Do not display `amount_minor` raw, and do not do arithmetic on the divided value.
- Do not fabricate an endpoint. If data is needed that no route provides, add the
  route with a test.
