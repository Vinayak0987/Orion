# AGENTS.md

**Read `docs/HANDOVER.md` before doing anything else.** It contains the full state
of this project: what is built, what is pending, the next steps, and the
environment gotchas. You do not need the conversation history.

## One-line summary

**Orion** (codebase identifier `mabgp`) is an AI Business Operating System. A
generation layer turns one sentence into a founding business plan using 21 agents
across 5 departments; an operating layer then runs that plan as a living company on
department cadences. B.E. final-year major project, University of Mumbai.

## Verify state first

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

Expect **989 passed**, fully offline. Trust the test output over any document.

## The invariant you must not break

> Anchors are computed, never reported. No department, planner, worker or
> reflection process may write an anchor metric.

Enforced structurally: anchors are not stored, so there is nowhere to write one.
`backend/tests/test_anchors.py` asserts it. If a task would require relaxing this,
say so rather than working around it.

## Binding rules

- Stack is LOCKED: LangGraph, Groq/Gemini/Ollama via `app/llm/` only, FastAPI,
  SQLite, ChromaDB, React 18 + Vite. Free tiers only ? flag anything costing money.
- Every LLM call goes through `app.llm.llm_client`.
- Every generation-layer state write goes through `apply_department_patch`.
- Field names in `app/models/departments.py` are FROZEN. Add optional fields, never
  rename ? the metrics depend on them.
- The test suite must stay fully offline. `conftest.py` fails any outbound socket.
- Add a regression test for every change. Runnable code only. Pinned versions.
- Frontend depends on `react` and `react-dom` ONLY, 162 kB bundle. No router, no
  chart library. Charts are inline SVG.

## Environment

- Two Pythons: `.venv\Scripts\python.exe` for the app; **system `python` for
  playwright** (used only to render `docs/orion/` PDFs and figures).
- PowerShell has no `&&` ? use `;`.
- **Set `$env:PYTHONIOENCODING="utf-8"` before running the demo scripts.** They
  print `?`, `?` and box-drawing characters; the default Windows console codepage
  raises `UnicodeEncodeError` and the script exits 1 for that reason alone, not
  because anything is broken.
- `PYTHONPATH` must include both `backend` and the repo root.
- Money is integer paise in the operating layer. Divide by 100 for display only.
- **No git repo.** Nothing to revert to. Be careful with destructive edits.

## Where to start

`docs/HANDOVER.md` ?8 lists pending work in priority order. Short version: three
non-code items gate the paper (35-prompt sweep, sourced benchmarks, competitor
ground truth); the largest code task is the ablation harness in
`docs/WORK_REMAINING.md` ?5.1; the frontend spec is ready in
`docs/FRONTEND_PROMPT.md`.

## Honesty requirement

The generation layer is measured. The operating layer runs unattended but its
planners are rule-based. The ablation harness is built and has been run at n=10:
the direction favours the full graph but **nothing reaches p<0.05**, so RQ4?RQ7 have
no answer. Documents in `docs/orion/` mark every figure **Measured** or
**Prospective**. Do not let any document, slide or UI imply the system is
experimentally validated when it is not.

Read `docs/OPERATING_LAYER.md` ?4b before touching the ablation. It records five
defects the first sweep exposed ? including that the documented "load-bearing"
learning branch could never fire in the live path ? and the modelling choices the
result is conditional on.
