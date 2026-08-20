# HANDOVER ? read this first

You are picking up a project mid-flight. This file exists so you do not have to be
told the history. Read it, then read the two files it points you at, then start.

**Last updated:** 8 August 2026
**Repo root:** `C:\Users\Vinayak\Desktop\kiro`
**Owner:** Vinayak Maurya ? B.E. Computer Engineering final-year major project,
University of Mumbai. Team: Aditya Maskare (102), Vinayak Maurya (103),
Abhishek Mishra (108), Division B.

---

## 1. What this project is, in four sentences

**Orion** is an AI Business Operating System with two layers.

The **generation layer** turns one sentence into a complete founding business plan
using 21 specialised agents across five departments (Strategy, Finance, Branding,
Marketing, Operations), coordinated by a routing orchestrator over an enforced
append-only state object. This layer is **built and quantitatively evaluated**.

The **operating layer** treats that finished plan as the company's opening state
and runs it onward on department cadences ? planning, gating, executing, recording,
reflecting. This layer is **built and runs unattended**, but its planners are
rule-based, so it demonstrates a control structure rather than good judgement.

The codebase identifier is `mabgp` (from the generation layer's original name,
Multi-Agent Business Generation Platform). It is retained for continuity with the
database and test suite. `mabgp` and `Orion` refer to the same system.

---

## 2. Current state ? verified, not claimed

```
989 tests, all passing, fully offline, pytest exit code 0
```

Verify it yourself before trusting anything below:

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
cd C:\Users\Vinayak\Desktop\kiro\backend
..\.venv\Scripts\python.exe -m pytest -q
```

If that does not say 989 passed, something changed after this file was written and
you should trust the test output over this document.

---

## 3. Read these next, in this order

| File | Why |
|---|---|
| `docs/OPERATING_LAYER.md` | What the operating layer is, module by module, and ?4 lists exactly what is NOT built |
| `docs/WORK_REMAINING.md` | Prioritised remaining work. Priority 1 blocks the paper and needs no code. Priority 5 is the experiment. |
| `docs/WORK_COMPLETED.md` | Full inventory including the 20 real bugs found by running the system |
| `docs/CONFIGURATION_TODO.md` | API keys, data files, and the packages added later |
| `docs/HOW_TO_RUN.md` | Commands for backend, frontend, evaluation |
| `docs/paper/PAPER.md` | The research paper draft. ?6 numbers are a smoke run, not findings. |
| `docs/FRONTEND_PROMPT.md` | Complete spec for the three-layer UI, if that is your task |

`docs/PROJECT_SPEC.md` is the original 65-feature specification. Still accurate for
the generation layer.

---

## 4. The one idea you must not undermine

> **Anchors are computed, never reported.** No department, planner, worker or
> reflection process may write an anchor metric, and no learning process may
> optimise directly against one.

This is enforced structurally, not by policy: **anchors are not stored.** There is
no anchor table, no column and no setter. A caller cannot write an anchor because
there is nowhere to write one. `backend/tests/test_anchors.py` asserts this,
including that no table with "anchor" in its name exists.

It generalises two findings the generation layer produced empirically and which are
recorded in the paper:

- **?4.4** ? prompts containing explicit numeric bounds were ignored repeatedly.
  Cross-agent constraints must be enforced in code, not requested in prose.
- **?7.2** ? decomposing a quantitative estimate across dependent agents compounds
  variance. Over five runs of an identical prompt the pipeline's standard deviation
  was 4.9? a single-LLM baseline's. It is *unreliably better*, not reliably worse.

If a feature you are asked to build would require relaxing the invariant, the
correct decision is to forgo the feature. Say so rather than working around it.

---

## 5. Layout

```
backend/app/
  intent/         hybrid intent classifier (LLM + deterministic parsing)
  orchestrator/   routing, LangGraph DAG, progress, completeness
  agents/         21 agents in 5 departments, base class, registry, subgraph
  models/         FROZEN field names in departments.py; state.py has the contract
  llm/            provider fallback chain. Every LLM call goes through here.
  apis/           Places/Overpass, Serper, ChromaDB cache, freshness
  output/         sections, JSON package, HTML, PDF
  db/             SQLite (stdlib sqlite3, no ORM)
  operating/      THE OPERATING LAYER ? 11 modules, see below

backend/tests/    989 tests, offline, socket guard in conftest.py
evaluation/       harness, metrics, baseline, report, significance, ablation_harness
scripts/          make_figures, make_deck, operating_demo, autonomy_demo
docs/             all documentation, plus docs/orion/ (PDFs, deck, figures)
frontend/         React 18 + Vite. react + react-dom ONLY. 162 kB bundle.
```

### The operating layer

| Module | Role | Key invariant |
|---|---|---|
| `ledger.py` | Append-only record of events | SQLite triggers abort UPDATE and DELETE |
| `anchors.py` | 19 metrics derived from the ledger | Not stored, so unwritable |
| `constitution.py` | 7 hard constraints | Rules are code, not data; `amend()` refuses at runtime |
| `governance.py` | Decision ? review ? approval ? execution ? audit | Whitelisted transitions; audit append-only |
| `loops.py` | Loop registry + 2 topology invariants | Validated at registration, not run time |
| `monitors.py` | Goodhart, conflict, drift, objective review | A finding cannot exist without an anchor citation |
| `scheduler.py` | Clock-injected cadence kernel | Time is a parameter; nothing sleeps |
| `memory.py` | 5 isolated stores, 4 types each | Scoping applied in the SQL |
| `reflection.py` | Learning from measured anchor deltas | Verdict decided before any text is written |
| `departments.py` | The 5 department loops | Governance refusal is a recorded outcome, not an exception |
| `monitoring.py` | Wires monitors + reflection to the scheduler | Baselines store a ledger sequence, never anchor values |

Assembled entry point:

```python
from app.operating import init_all, build_scheduler
init_all()                       # idempotent
sched = build_scheduler()        # wires all 10 loops
sched.run_due("company-id")      # advances the business, nothing else needed
```

---

## 6. Prove it works before you change it

Two demos, both deterministic, no LLM, no network, no API keys:

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
cd C:\Users\Vinayak\Desktop\kiro
.\.venv\Scripts\python.exe -m scripts.autonomy_demo --days 90
.\.venv\Scripts\python.exe -m scripts.operating_demo
```

`autonomy_demo` output you should see: 574 scheduled runs, 486 ledger entries, net
margin falling 60% ? +2.5% while customers acquired rises to 104, caught as CRITICAL
proxy-divergence and HIGH inter-department conflict findings.

Note marketing's memory counts against the other departments': **episodic 14 versus
89**. That gap is the learning path working ? marketing received a margin lesson,
suppressed its spend task, and stopped acting, while the other four kept going.

These figures changed on 8 Aug 2026 when the reflective-lesson retrieval defect was
fixed (bug 21 in WORK_COMPLETED ?5). Before the fix the lesson was never retrieved,
marketing never stopped spending, and the run ended at **?18.5%** margin with 272
customers and 352 ledger entries. The company now self-corrects instead of running
off a cliff, which is why the numbers are different and better.

---

## 7. What is DONE

**Generation layer:** 65/65 features. Intent classification, routing with dynamic
department skipping, 21 agents across 5 departments in staged nested graphs,
append-only state contract, deterministic reconciliation of conflicting agent
claims, external grounding (OpenStreetMap + Serper), JSON/HTML/PDF output, React
frontend for generation, evaluation harness with 5 metrics and 4 arms.

**Operating layer:** all 11 modules above, wired and running unattended.

**Paper tooling:** `evaluation/significance.py` (paired Wilcoxon + t-test, effect
sizes, underpowered flagging below 10 pairs, wired into `report.py`) and
`scripts/make_figures.py` (Figures 2 and 4 from real data, byte-deterministic).

**Ablation harness (NEW):** `app/operating/environment.py` (seeded stochastic
market), `app/operating/ablation.py` (four arms), `evaluation/operating_metrics.py`
(F59–F63), `evaluation/ablation_harness.py` (paired-seed runner),
`scripts/ablation_report.py` (outcomes + paired Wilcoxon). 99 new tests.

```powershell
.\.venv\Scripts\python.exe -m evaluation.ablation_harness --seeds 10 --days 90 --label ablation-v2
.\.venv\Scripts\python.exe -m scripts.ablation_report --label ablation-v2
```

**Run at n=10. The result is a null.** F59 divergence favours the full graph in
every comparison (−0.78 vs −0.59 for single_loop) but no comparison reaches
p < 0.05; the best is 0.059. Between-seed variance is 33–70% of the means. RQ4–RQ7
are **not** answered. `docs/OPERATING_LAYER.md` §4b has the full table, the five
defects the first sweep exposed, and the modelling choices the result is
conditional on. Do not describe the ablation as having produced a positive result.

**Documents in `docs/orion/`:** architecture explainer PDF (16pp), research
proposal PDF (14pp), two 2-page briefs, and `Orion_Presentation.pptx` ? a 19-slide
review deck rebuilt to exactly match the supplied college template, with 7
purpose-drawn diagrams (architecture, DFD 0/1/2, use case, activity, tech stack).
Rebuild any of it with `scripts/make_deck.py` or `docs/orion/src/build_pdfs.py`.

**Measured results:** completeness 100% of a 26-field rubric vs 80.8% baseline;
dynamic routing 17.3% token saving at 0.0 pp quality delta; and a reported negative
result ? on financial accuracy the single-LLM baseline wins, attributed to variance
compounding, reported rather than tuned away.

---

## 8. What is PENDING

### Blocks the paper. None of it is code. Only Vinayak can do it.

1. **Run the full 35-prompt sweep.** Everything in PAPER.md ?6 is n ? 5 and is not
   a finding. ~90 minutes, 4 arms ? 35 prompts. Enable the cache first or it burns
   4? the Serper credits and risks results drifting between arms.
   ```powershell
   .\.venv\Scripts\python.exe -m evaluation.harness --all --label paper-run-1
   .\.venv\Scripts\python.exe -m evaluation.report  --label paper-run-1
   ```
   The report now emits the significance section automatically. Paste the generated
   tables into PAPER.md ?6 ? do not retype them.
2. **Source the sector margin benchmarks.** F54 divides by these. Until
   `evaluation/benchmarks.csv` carries citations the report stamps financial
   accuracy PROVISIONAL, correctly. Candidates: MSME Ministry annual report sector
   notes, RBI private corporate business sector releases, NSSO unincorporated
   enterprise surveys. **Library research, not coding.**
3. **Collect competitor ground truth.** F55 cannot be computed without it, so RQ3
   rests on indirect evidence. Fill `ground_truth_competitors` in
   `evaluation/prompts.json` by counting real businesses within 2 km by hand. Ten
   prompts is enough. **Fieldwork, not coding.**

### The experiment ? built and run, but the result is a null

4. **Raise the seed count on the ablation.** The harness works and has been run at
   n=10; the direction favours the full graph on every F59 comparison but nothing
   reaches p<0.05 because between-seed variance is 33?70% of the means. Only the
   seed count needs to change:
   ```powershell
   .\.venv\Scripts\python.exe -m evaluation.ablation_harness --seeds 40 --days 90 --label ablation-v3
   .\.venv\Scripts\python.exe -m scripts.ablation_report --label ablation-v3
   ```
   ~30 s per arm-seed, so n=40 is roughly 80 minutes. Read `docs/OPERATING_LAYER.md`
   ?4b first: it records what the first sweep got wrong and which modelling choices
   the result is conditional on. RQ4?RQ7 are currently **unanswered**, and a larger
   n may well leave them that way ? which would itself be a reportable result.

### Product completion

5. Knowledge evolution ? templates, reusable plans, playbooks (?5.2)
6. Living business objects ? versioned, each revision citing its anchor movement (?5.3)
7. Event bus + operating-layer WebSocket (?5.4)
8. ~~Three-layer frontend~~ **DONE** ? built 10 Aug 2026
9. External reality probe ? Agent-Reach, zero-config channels only (?5.6)

### Suggested order

The ablation harness is built, so the next highest-value action is **running it**
(item 4 above) and items 1?3 (which gate the generation-layer paper results).
Product completion (5?9) is independent and can proceed in parallel.

---

## 9. Rules that are binding, not advisory

Carried from `docs/WORK_REMAINING.md` ?0. Violating these breaks things silently.

- **Stack is LOCKED.** LangGraph, Groq/Gemini/Ollama via `app/llm/` only, FastAPI,
  SQLite, ChromaDB, React 18 + Vite, Docker Compose. Free tiers only ? flag
  anything that costs money.
- **Every LLM call goes through `app.llm.llm_client`.** No agent imports a vendor
  SDK.
- **Every generation-layer state write goes through `apply_department_patch`.**
- **Field names in `app/models/departments.py` are FROZEN.** Add optional fields;
  never rename. The metrics depend on them.
- **Validate all LLM JSON with Pydantic.**
- **The suite must stay fully offline.** `conftest.py` has a socket guard that fails
  any outbound connection. If a test needs the network, mark it
  `@pytest.mark.allow_network` and justify it.
- **Add a regression test for every change.** Runnable code only, never
  pseudocode. Pinned versions.
- **Frontend depends on `react` and `react-dom` only.** 162 kB bundle. No router,
  no chart library, no CSS framework. Charts are inline SVG.

---

## 10. Environment gotchas that will waste your time

- **Two Pythons.** `.venv\Scripts\python.exe` has the app, scipy, matplotlib,
  python-pptx. **`playwright` is in the SYSTEM python only** and is used solely to
  render the PDFs and figure PNGs in `docs/orion/`. Use plain `python` for those.
- **PYTHONPATH is required** for pytest and for `scripts.*`:
  `$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"`
- **PowerShell has no `&&`.** Use `;`.
- **`$env:PYTHONIOENCODING="utf-8"` is required for the demo scripts.** They print
  `?`, `?` and box-drawing characters. Without it the default Windows console
  codepage raises `UnicodeEncodeError` and the script exits 1 for that reason
  alone. `pytest` is unaffected.
- **`Settings.sqlite_file` is a read-only property.** Tests patch the class
  attribute, not the instance:
  ```python
  monkeypatch.setattr(sqlite_module.settings.__class__, "sqlite_file",
                      property(lambda _self: db_file))
  ```
  Copy that pattern from `tests/test_db.py`. Patching the instance raises.
- **Money is integer minor units (paise)** everywhere in the operating layer.
  Divide by 100 for display only; never do arithmetic on the divided value.
- **scipy 1.14.1 constrains numpy to <2.3.** Installing it downgraded numpy
  2.5.1 ? 2.2.6. The suite was re-run and passes.
- **No git repo.** There is no version control here. Be careful with destructive
  edits; there is nothing to revert to.

---

## 11. Bugs already found and fixed ? do not reintroduce

20 defects are listed in `docs/WORK_COMPLETED.md` ?5, each pinned by a regression
test. Five worth knowing because they are easy to recreate:

| Bug | Why it mattered |
|---|---|
| **Reflective lessons were unretrievable** | The planner queried memory with its objective and PROXY; reflection writes lessons in ANCHOR vocabulary. Token overlap was zero, so `memory._score` returned 0.0 and the lesson was dropped. The documented "load-bearing" learning branch was **dead in the live path**, and the test that appeared to prove it passes unchanged with its memory write deleted. Use `departments.retrieval_query()`. |
| Cold-start stagger was a gate, not a phase shift | A fixed-hour tick has a constant `timestamp() % cadence`, so any loop with a larger offset was **never** due. Strategy and Finance never ran once in 90 simulated days. |
| Proxy delta required a computable baseline | A department going 0 ? 40 acquisitions made no claim, so its first and most capture-prone period was never checked. |
| `tokenise` dropped tokens of length ? 2 | "?15 lakh" and "?40 lakh" tokenised identically and consolidated into one memory. |
| Paired t-test divided by zero variance | scipy returned `inf`; the report would have printed `t = inf` as a result. |
| Prompt-level numeric bounds were ignored | The finding the whole architecture is built on. Constraints must be code. |
| Cumulative anchors hide period dynamics | A cumulative ratio is dominated by history: `net_margin_pct` moved only 17.7% ? 18.6% across a run in which the company was steadily destroying value. Period control needs **period-scoped** anchor sets. |

---

## 12. How to talk about this project honestly

This matters for the viva and for the paper.

**True:** the generation layer is built and measured. The operating layer's control
mechanisms are built and tested, and the system runs a company unattended. The
ablation harness is built, has a reactive simulated environment, and has been run.

**Not true:** that Orion is finished, or that the graph-of-loops claim is evidenced.
The planners are rule-based, and **the ablation's result is a null**: at n=10 the
direction favours the full graph on every F59 comparison but nothing reaches
p<0.05. RQ4?RQ7 have no answer. `docs/orion/` marks every figure **Measured** or
**Prospective** for exactly this reason, and the deck's slide 16 lists what is not
built.

If asked whether Orion is fully coded, the defensible answer is: the generation
layer is built and evaluated, the operating layer's control mechanisms are built and
tested, continuous autonomous operation is demonstrated, and the ablation that would
evidence the central claim is implemented and run but **underpowered ? it does not
yet support the claim.**

Two things worth volunteering in a viva, because they are the strongest evidence of
method rather than weaknesses to hide:

- The first ablation sweep produced four byte-identical arms. Running it exposed
  five defects, including that the documented "load-bearing" learning branch could
  never fire in the live path and that the test appearing to prove it passed for an
  unrelated reason. That is the project's own `claim_vs_ledger` failure mode found
  in the project's own code.
- The ablation's headline metric is not significant, and it is reported that way
  rather than tuned. The churn amplifier that would have produced a much larger
  effect is defaulted to 0.0 precisely so the result cannot rest on it.

Do not let a document, slide or UI imply otherwise. The honesty is the strongest
thing about this work ? the paper's central finding is a negative result reported
rather than tuned away, and that is what makes the rest credible.
