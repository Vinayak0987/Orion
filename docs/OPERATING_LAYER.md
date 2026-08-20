# Operating layer — implementation status

The generation layer (21 agents, 5 departments) produces a company's opening
state. This document records the **operating layer** that runs that state onward:
what is built, what it is for, and what is not built yet.

Nothing here changes the generation layer. No frozen field was renamed, no
existing module was modified except `evaluation/report.py` (one new section) and
`backend/requirements.txt` (two analysis dependencies).

---

## Test baseline

| Point | Tests | Note |
|---|---|---|
| Before this work | 517 | all passing, fully offline |
| After operating layer | 869 | all passing, fully offline |
| After ablation harness | **989** | all passing, fully offline |

The socket guard is intact: every new test runs without a network connection and
consumes no API quota. No new test calls an LLM.

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

---

## 1. Paper-unblocking work (WORK_REMAINING §2.2, §2.3)

### `evaluation/significance.py` — paired significance testing

Wilcoxon signed-rank as the primary test, paired t-test alongside for reference,
with rank-biserial correlation and Cohen's d as effect sizes. Arms are paired by
`prompt_id`, and only prompts scored in **both** arms contribute a pair — the
refusal-to-impute policy carries through.

Comparisons with fewer than 10 pairs are labelled `UNDERPOWERED` and the report
states plainly that their p-values are not evidence either way. Wired into
`evaluation/report.py`; also writes `<label>-significance.json`.

One defect found and fixed during testing: when every paired difference is
identical the t-test's denominator is zero and scipy returns `inf`, which would
have printed `t = inf` into the report. The t-test is now recorded as undefined in
that case while Wilcoxon — which does not depend on that variance — still stands.

*27 tests, including the three pairable observations from PAPER.md §6.3, which
must come out UNDERPOWERED.*

### `scripts/make_figures.py` — Figures 2 and 4

- **Figure 2** — execution DAG for both routing conditions, rendered from
  `app.orchestrator.routing.resolve_departments`.
- **Figure 4** — variance compounding as a dot chart per arm, from
  `<label>-metrics.csv`, annotated with n, mean, sd and best-to-worst spread.

Two deviations from `FIGURES.md`, both deliberate:

1. It derives Figure 2 from the routing module rather than `GET /intent`. Same
   function the endpoint calls, but no server and no LLM call, so the figure
   regenerates offline and is covered by tests. `--from-api` is accepted.
2. Figure 4 is a dot chart, not bars, as the spec requires — the spread is the
   finding and bars of means would conceal it.

Output is byte-deterministic (`svg.hashsalt` pinned, timestamp stripped), so a
regenerated figure diffs cleanly instead of changing on every run.

*14 tests. Three real bugs were caught by them: `requires_operations` is a
separate field from `is_physical` and was not being set; SVG output was
non-deterministic; and `relative_to` crashed when the output directory was outside
the repository.*

Generate:
```powershell
.\.venv\Scripts\python.exe -m scripts.make_figures --label paper-run-1
```

---

## 2. Operating layer — `backend/app/operating/`

### `ledger.py` — the append-only record

Every anchor is derived from this table and nothing else, so two properties are
enforced by SQLite rather than by convention:

- **Append-only.** Triggers abort any `UPDATE` or `DELETE`.
- **Attributed.** Every entry names the department and actor that produced it.

Amounts are integer minor units (paise), never floats. A project reporting on
numerical reliability should not accumulate binary floating-point error in its own
accounting. Kinds are partitioned into monetary and count, and mixing them is
rejected at validation.

*25 tests, including database-level proof that a rejected `UPDATE` leaves the
entry intact.*

### `anchors.py` — the invariant

> No department, planner, worker or reflection process may write an anchor
> metric, and no learning process may optimise directly against one. Anchors are
> computed, never reported.

Enforced structurally rather than stated: **anchors are not stored.** There is no
anchor table, no column and no setter. `AnchorSet` is frozen and its only
constructor reads the ledger. A caller cannot write an anchor because there is
nowhere to write one.

Nineteen anchors derived deterministically: revenue, COGS, opex, marketing spend,
capex, cash balance, gross and net profit, gross and net margin, customers
acquired/churned/active, churn, retention, CAC, ARPC, SLA breaches, tasks
completed. Each carries the number of ledger entries it rests on, and thin
evidence is flagged rather than presented as equivalent to a large sample.

`delta()` is what reflection and the monitors consume: a department is judged on
measured movement, not on its own account.

*30 tests. The first six assert the invariant, including that no anchor table
exists and that the module exposes no writer.*

### `constitution.py` — hard constraints in the call path

This is PAPER.md §4.4 generalised. That section records that prompts containing
explicit numeric bounds were ignored repeatedly and had to be re-implemented as
post-conditions. The same reasoning applied to operating constraints:

| Rule | Severity |
|---|---|
| `C1_DAILY_SPEND_CAP` | block |
| `C2_SINGLE_SPEND_CAP` | block |
| `C3_NO_OVERDRAFT` | block |
| `C4_NO_CUSTOMER_DATA_DELETION` | block, unconditional |
| `C5_PAYMENT_REQUIRES_VERIFICATION` | block |
| `C6_IRREVERSIBLE_REQUIRES_APPROVAL` | require human |
| `C7_LEDGER_APPEND_MUST_BE_ATTRIBUTED` | block |

Rules are **code, not data** — an agent with database access still cannot alter
one, and a test asserts the module performs no rule loading. `amend()` always
refuses at runtime and explains that the module must be changed under review.

Spend-to-date and cash come from the ledger via `context_from_ledger`, not from a
department's report of what it has spent.

*42 tests, including that a persuasive description and an injected payload
claiming pre-approval both fail to change a verdict.*

### `loops.py` — the topology invariants

**I1 Termination.** Every cycle must contain a code-computed anchor or a human
decision. Decided by deleting all anchor and human nodes and testing the residual
graph for cycles — a surviving cycle is exactly a cycle with no external
referent. The offending path is reported.

**I2 Independence.** A monitor may not share an evaluation signal with the loop it
monitors.

Validation runs on `register`, so an invalid topology cannot be built and then
discovered at run time. `default_graph()` is the real topology: 1 anchor, 1 human,
5 execution loops for the implemented departments, 4 monitors, 1 learning loop.

*30 tests. The A→B→C→A rejection is the headline case; each invariant is also
tested against a minimally different topology it must accept.*

### `monitors.py` — the four loops that check the work

| Monitor | Failure mode |
|---|---|
| `claim_vs_ledger` | proxy capture — claimed gain with no matching anchor movement |
| `detect_conflict` | two departments improving while a shared anchor falls |
| `detect_drift` | a threshold still in use after its shelf life |
| `review_objectives` | an objective in force while its anchor declines |

`claim_vs_ledger` is the claim-versus-code lens from `production-audit`, adapted:
the department's claimed success stands in for the public promise, and the ledger
stands in for the code.

Two disciplines borrowed from that methodology. **Every finding must cite an
anchor and a measured delta** — `Finding` cannot be constructed without one, so a
suspicion that cannot be grounded is not emitted. And the report is a flat
severity-ordered list with no executive summary, because a summary is where an
audit softens.

A `Claim` must nominate the anchor it expects to move. A department is free to
choose its proxy but not to avoid naming a real quantity, which is what makes
capture visible.

*25 tests. `test_goodhart_scenario_is_detected` is the one that matters.*

### `governance.py` — the gate chain

```
Decision -> Review Queue -> Approval Gate -> Execution Gate -> Audit Trail
```

Three stages can halt an action. State transitions are whitelisted, so a decision
cannot reach execution without passing the gates before it.

**Policy** (approval gate) is configurable: review thresholds, which kinds are
subjective, auto-approval of routine work. **Hard constraints** (execution gate)
are the Constitution and are not. Collapsing the two would make the Constitution
configurable, and a configurable hard constraint is a policy.

The Constitution is re-checked at execution rather than at proposal, because the
facts it depends on move while a decision waits in the queue.

The audit trail is append-only by the same triggers as the ledger, and records
halts as well as successes.

*34 tests, including that a human approval does not unlock a hard constraint, and
that the audit trail cannot be rewritten to hide a block.*

### `scheduler.py` — what makes the business continue

A **deterministic, clock-injected kernel**, not a background thread. Time is a
parameter: `run_due(company_id, now=<timestamp>)`. Nothing sleeps and no test
waits.

That is deliberate rather than a shortcut. The ablation planned for RQ4–RQ7
compares arms on paired seeds; if the schedule depended on wall-clock timing, two
runs of the same seed would interleave differently and the comparison would be
confounded by scheduling noise rather than by control topology. `run_forever` is a
thin real-time driver over the same kernel whose only job is deciding what `now`
is.

Three mechanisms keep local inference load flat: a deterministic per-loop
**stagger offset** derived from the loop id, a **single-flight guard** that holds
while the handler executes, and `max_per_tick`. Last-run times are persisted, so a
company restarted mid-quarter resumes its cadence rather than firing everything at
once. `clear_stale_flights` releases a flag left set by a crashed process —
without it, a crash would silently retire one loop forever while the business kept
running.

Anchor and human nodes are never scheduled: an anchor is recomputed on read and a
human acts when they choose.

*33 tests, including a simulated month in which four daily loops each run 30 times
and a weekly loop runs 4–5, a re-entrant handler that cannot overlap itself, and
proof that one failing department does not stop the others.*

### `memory.py` — one isolated store per department, four typed

Episodic, semantic, procedural, reflective. Scoping is applied in the SQL, so
there is no code path by which one department's query can surface another's
entries. `retrieve_shared` exists only as the **control arm** for the
scoped-versus-shared comparison the proposal sets out; the operating layer does not
call it.

Retrieval is lexical and deterministic — token overlap weighted by recency and by
how often an entry has proved useful. No embedding model, because ChromaDB's
default embedding function downloads a model on first use, which would break the
offline guarantee and make retrieval vary with whatever model version was fetched.
The invariant that matters is scoping, and it is independent of how relevance is
scored.

Consolidation promotes a repeated episode into one semantic conclusion at three
occurrences, so eleven repeats carry one conclusion rather than eleven competing
anecdotes. Decay retires unretrieved aged episodes — retires, not deletes — and
spares semantic conclusions and anything that has proved useful.

*37 tests. One real defect was caught: `tokenise` dropped tokens of length ≤ 2, so
"₹15 lakh" and "₹40 lakh" tokenised identically and consolidated into one memory.
Numeric tokens are now kept regardless of length.*

### `reflection.py` — learning grounded in measurement

The mechanism is unremarkable; the constraint is the contribution:

> Reflection is grounded in measured anchor deltas, not in the department's
> account of its own performance.

`Reflection.verdict` is arithmetic on the ledger, decided before any text is
written. A department's narrative is recorded as `claimed`, and where the two
disagree, `contradicted` is set, the measured verdict stands, and the disagreement
is itself written into reflective memory as a lesson.

Each anchor's direction is interpreted correctly — rising churn is a decline even
though the number went up. Lessons must name a measured movement and carry its
delta; an anchor with no lesson template produces no lesson, because generic
advice recorded as knowledge is the failure mode this module exists to avoid.

Nothing here calls an LLM. Keeping the grounding free of inference is what makes it
testable and reproducible.

*21 tests, including that a department claiming a record month during a margin
collapse still produces a DECLINED verdict.*


### `departments.py` ? the five department loops

`DepartmentProfile` names **both** the proxy a department watches and the anchor it
is accountable for. Naming both is what makes proxy capture detectable: the monitor
compares one against the other, and a profile naming only a proxy would make
capture invisible.

`run_tick` performs the full sequence: read anchors, retrieve the department's own
memory, plan, submit to governance, execute only what was approved, append the
declared ledger effects, write episodic memory. A governance block or review-queue
placement is a normal recorded outcome rather than an exception, so one gated task
never looks like a crashed department.

Tasks declare their `effects` up front, which is what lets an outcome be checked
against the intent rather than inferred afterwards.

The planner is rule-based deliberately. The ablation varies *control topology*; a
non-deterministic planner would reintroduce the variance compounding PAPER.md ?7.2
measured and confound the comparison.

One branch is load-bearing: a reflective lesson warning against spend suppresses
the spend task. That is the only place memory changes behaviour, and it is what
makes "the department learned something" a claim a test can check.

*24 tests, including that a queued task appends nothing to the ledger, that a
Constitution violation appends nothing, and that one failing department does not
stop the other four.*

### `monitoring.py` ? wiring the monitors to the scheduler

A monitor compares one period against the previous one, so it needs a baseline.
Anchors are never stored, so a "snapshot" records only the ledger sequence number
the period ended at; the anchor set is recomputed from the ledger up to that point
whenever needed.

That indirection is deliberate. Storing anchor values would create exactly the
writable copy the invariant exists to prevent ? a stored number can drift from the
ledger, and once it can drift it can be wrong in a convenient direction. A sequence
number cannot.

`claims_from_ledger` reconstructs each department's implicit claim from what it
actually did, nominating the anchor its profile says it serves. The department is
never asked to self-report.

*15 tests. One real defect was found: `AnchorSet.delta` only reports anchors
computable in both readings, which is correct for it but wrong for a proxy ? a
department going from no acquisitions to forty has clearly claimed progress, and
that first active period is exactly when capture is most likely. An absent baseline
is now read as zero for proxies only.*

---

## 3. End-to-end

`backend/tests/test_operating_e2e.py` — 6 tests driving one company through two
trading periods: healthy quarter, then deep discounting that lifts the proxy and
destroys margin. The detector fires CRITICAL, the conflict detector fires HIGH,
both escalate, a human rejects the proposal to double down, and the audit trail
records the whole passage.

`scripts/autonomy_demo.py` — a simulated quarter run unattended:

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
.\.venv\Scripts\python.exe -m scripts.autonomy_demo --days 90
```

`scripts/operating_demo.py` — the component-level walkthrough, no LLM, no
network, deterministic:

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
.\.venv\Scripts\python.exe -m scripts.operating_demo
```

Measured output from the demo: net margin 35.0% → 11.11%, churn 0% → 30%, CAC
₹100 → ₹233.33, while customers acquired went 200 → 600. The Goodhart detector
cites `net_margin_pct -23.89` against a claimed `+200`.

---

## 4. What is NOT built

Stated plainly, because the documents in `docs/orion/` describe the full
architecture and this is the boundary.

- **Knowledge evolution.** Reflection writes lessons into reflective memory, and
  a lesson does change what the marketing planner proposes, but there are no plan
  templates, no reusable plans and no department playbooks. A completed project
  does not yet yield anything a later project retrieves.
- **Living business objects.** No versioned strategy, financial model or roadmap.
- **Event bus and WebSocket for operating events.** The existing `/ws/generate`
  covers generation only. Monitor findings and cadence runs are recorded in
  SQLite but not published.
- **External reality probe.** No Agent-Reach integration.
- **Intelligent planning.** The planners are rule-based by design. LLM-backed
  planning is a substitution behind the same `Planner` protocol and is not wired,
  so the demonstration shows the control structure working, not that the decisions
  are good.

**The three-layer interface is NOW BUILT** (10 Aug 2026): 12 API endpoints in
`app/operating/api.py`, 13 React components, 4 views with hash routing, and the
bundle stays at 188.62 kB (no new dependencies). See `frontend/src/operating/`.

**The ablation harness is NOW BUILT** — see §4a below.

---

## 4a. The ablation harness (BUILT)

The operating-layer experiment (RQ4–RQ7) is now runnable.  Three new modules:

### `app/operating/environment.py` — the reactive market

A seeded stochastic model where the world responds to what departments do:

- **Organic demand:** base customer arrivals with Gaussian noise
- **Marketing response:** spend converts customers at a known rate
- **The Goodhart mechanism:** heavy marketing spend increases acquisitions (proxy)
  but brings low-quality customers who churn faster and have lower revenue,
  depressing net margin (anchor)
- **Deterministic with a seed:** same seed → identical outcome, enabling
  paired-seed comparison across arms

The environment uses a custom `DeterministicRNG` (64-bit xorshift) — no numpy
dependency, fully offline, no OS random state.

`SimulatedEnvironment.can_game_proxy()` asserts the key design property at
construction.

*22 tests, including proof that heavy spend increases acquisition while
increasing churn (the proxy-gaming property).*

### `app/operating/ablation.py` — the four arms

| Arm | Anchors | Monitors | Governance | Human gates |
|---|---|---|---|---|
| `single_loop` | ✗ | ✗ | ✗ | ✗ |
| `anchors_only` | ✓ | ✗ | ✗ | ✗ |
| `monitors_only` | ✗ | ✓ | ✗ | ✗ |
| `full_graph` | ✓ | ✓ | ✓ | ✓ |

All four use the same rule-based planner, the same memory, and the same execution
machinery.  They differ **only** in control topology.  `single_loop` is the
baseline: same machinery, no structural checks.

`run_arm(arm, seed=N, days=90)` runs one arm with the simulated environment.
`run_paired(seed=N)` runs all four arms with the same seed.

*23 tests, including determinism, fair baseline verification, and proof that
all arms use the same execution machinery.*

### `evaluation/operating_metrics.py` — F59–F63

Five metrics, all computed from the append-only ledger and from findings:

| ID | Metric | What it measures |
|---|---|---|
| F59 | proxy-anchor divergence | Spearman rank correlation over a sliding window (negated: higher = worse) |
| F60 | detection latency | Days from known onset to first citing finding |
| F61 | conflict incident rate | Inter-department conflicts per operating day |
| F62 | objective staleness | Fraction of review periods with stale objectives |
| F63 | human decision load | Human decisions required per operating day |

*28 tests, including known-answer checks for the Spearman implementation and
each metric's edge cases.*

### `evaluation/ablation_harness.py` — the runner

Ties it all together:

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
.\.venv\Scripts\python.exe -m evaluation.ablation_harness --seeds 10 --days 90 --label ablation-v2
.\.venv\Scripts\python.exe -m scripts.ablation_report --label ablation-v2
```

Produces three output files:
- `evaluation/results/<label>-ablation-metrics.csv` — per-seed per-arm per-metric
- `evaluation/results/<label>-ablation-summary.csv` — arm-level aggregates
- `evaluation/results/<label>-ablation-sweep.json` — full run metadata

`scripts/ablation_report.py` reads them back and runs paired Wilcoxon tests
through `evaluation/significance.py`, pairing arms by **seed** rather than by
prompt_id.

*11 tests, including an end-to-end sweep and CLI verification.*

---

## 4b. What the first two sweeps actually measured

This section exists because the first sweep produced a table of numbers that
looked like results and were not.

### Sweep 1 (`ablation-v1`) — a null result by construction

Every arm produced **byte-identical** business outcomes: same ledger count, same
acquisitions, same churn, same revenue, zero blocks. Five defects, all found by
running the thing rather than by reading it:

| # | Defect | Why it invalidated the sweep |
|---|---|---|
| A | The simulated business was structurally unprofitable — revenue ~Rs 940/day against Rs 3,000/day of cost | `_anchor_unhealthy` latched permanently on day 2, so the marketing planner proposed its retention task for the rest of the run in **every** arm. Marketing spent Rs 4,000 once, ever. No proxy gaming could occur |
| B | Reflection was never wired into the arms | The only mechanism by which measurement changes behaviour was absent from all four arms |
| C | F60 computed detection latency from a finding's index in a list, `7 * (idx + 1) + 6` | A restatement of the monitor cadence, not a measurement. Returned 6.0 with sd 0.0 for every seed and arm |
| D | F62 passed an empty objectives list to `review_objectives` | The monitor could never fire, so 0.0-vs-1.0 recorded the arm configuration |
| E | **The documented "load-bearing" learning branch was dead in the live path** | See below |

### Defect E, in detail

`departments.py` and this document both stated that a reflective lesson
suppressing the spend task was "the only place memory changes behaviour" and "a
claim a test can check."

Memory retrieval is lexical token overlap: `memory._score` returns `0.0` when
overlap is zero and `retrieve` drops anything scoring zero. Reflection phrases its
lessons in **anchor** vocabulary — "net margin fell over the period; volume gained
without margin is not progress" — while the planner's retrieval query was built
from the objective and the **proxy**. For marketing:

```
query  tokens: {acquire, customers, stay, who, acquired}
lesson tokens: {net, margin, fell, over, period, volume, gained, ...}
overlap:       {}                      -> score 0.0 -> never retrieved
```

So `_warned_against_spend` could not fire, and memory could not change behaviour.

The branch *is* unit-tested, by passing a memory dict straight into the planner,
which bypasses retrieval. And `test_learning_changes_behaviour_across_ticks`,
which appeared to prove learning end to end, **passes unchanged with its memory
write deleted**: the first tick's own spend drives net margin to -40%, the
anchor-health branch latches, and the retention task is proposed for that reason
alone. Verified by running both variants.

Fixed by including `serves_anchor` in the query, extracted as
`departments.retrieval_query()` so tests exercise the production query rather than
one they construct. Three new tests isolate the memory effect from the
anchor-health effect by holding the anchor healthy; the discriminating one fails
with the old query and reports exactly why.

This is the failure mode `claim_vs_ledger` exists to catch, found in this
project's own code.

### Sweep 2 (`ablation-v2`) — measured, and not significant

Ten paired seeds, 90 simulated days per arm, four arms.

| arm | acquisitions | mkt spend Rs | lessons | corrections | human decisions |
|---|---|---|---|---|---|
| `single_loop` | 2069 ± 676 | 192,352 ± 134,349 | 0.0 | 4.9 | 0.0 |
| `anchors_only` | 1808 ± 344 | 146,720 ± 65,509 | 5.0 | 8.2 | 0.0 |
| `monitors_only` | 2069 ± 676 | 192,352 ± 134,349 | 0.0 | 4.9 | 0.0 |
| `full_graph` | 1731 ± 368 | 128,800 ± 72,536 | 3.4 | 6.5 | 24.2 |

**F59 proxy-anchor divergence** is the only metric whose value is not fixed by an
arm's definition. Lower is healthier:

| comparison | means | diff | Wilcoxon p | |
|---|---|---|---|---|
| `single_loop` vs `anchors_only` | −0.59 / −0.69 | +0.10 | 0.674 | not significant |
| `single_loop` vs `monitors_only` | −0.59 / −0.59 | 0.00 | n/a | no variation |
| `single_loop` vs `full_graph` | −0.59 / −0.78 | +0.18 | 0.463 | not significant |
| `anchors_only` vs `full_graph` | −0.69 / −0.78 | +0.09 | 0.059 | not significant |
| `monitors_only` vs `full_graph` | −0.59 / −0.78 | +0.18 | 0.463 | not significant |

**The direction favours the full graph in every comparison, and no comparison
reaches p < 0.05.** RQ4–RQ7 are therefore still unanswered. Between-seed variance
swamps the between-arm difference: standard deviations run 33–70% of the means,
which is the same variance-compounding problem PAPER.md §7.2 reports for the
generation layer.

F60, F61, F62 and F63 are **structural**: an arm without monitors scores exactly
zero on the conflict rate because it runs no conflict detector, so a significant
p-value there confirms the arm configuration rather than any difference in
behaviour. `scripts/ablation_report.py` labels them so and says why. The only
non-structural comparison available among them is `monitors_only` vs `full_graph`,
and none of those reach significance either.

### One clean finding

`single_loop` and `monitors_only` are **identical on every behavioural measure** —
same acquisitions, same spend, same corrections, to the unit. Monitors detect
divergence and escalate findings, but without gates they have no authority to act,
so the business does exactly what it would have done unwatched. That is asserted
by `test_monitors_without_gates_do_not_change_the_outcome` rather than left to be
noticed.

### The control rule, stated because it is a modelling choice

For proxy/anchor divergence to be observable **within** a run, a department has to
escalate its pursuit of the quantity it is judged by. The rule is:

> if the signal I observe improved, do more of what I did; if it deteriorated, stop
> and correct.

It is applied identically in all four arms; the only thing that varies is which
quantity the arm lets a department observe. Two consequences worth stating
plainly:

1. Results are **conditional on this rule**. It is a plausible and neutral control
   rule, not a derived one.
2. Anchors are cumulative-to-date, and a cumulative ratio is dominated by history:
   measured that way `net_margin_pct` moved only 17.7% → 18.6% across a run in
   which the company was steadily destroying value. The escalation signal and
   reflection therefore use **period-scoped** anchor sets, computed from one
   period's ledger entries. Nothing is stored — only sequence numbers are retained
   between periods, following the pattern `monitoring.py` already uses for monitor
   baselines, so the anchor invariant holds.

The environment's churn amplifier is defaulted to **0.0**, so the divergence rests
on unit economics alone: a marketing-acquired customer costs about Rs 200 and
returns an expected lifetime contribution of about Rs 58. With the amplifier off
and the pool stable, Rs 4,000/day of spend still moves acquisitions +32% while net
margin falls 35.4% → 18.7%. `test_goodhart_holds_without_the_churn_amplifier`
pins it.

The operating layer now **runs a business unattended.** `app.operating.build_scheduler()`
wires all ten schedulable loops — five departments, four monitors, reflection — and
`scheduler.run_due(company_id)` advances the company with nothing else prompting it.

`scripts/autonomy_demo.py` runs a simulated quarter: 574 scheduled runs, 486 ledger
entries, net margin moving from 60% to +2.5% while acquisitions rise to 104 —
caught as CRITICAL proxy-divergence findings and HIGH inter-department conflict.
Marketing ends with 14 episodic memories against 89 for each other department, which
is the learning path visible in the output: it took a margin lesson and stopped
spending.

These figures were 352 entries, −18.5% margin and 272 acquisitions until 8 Aug 2026,
when the reflective-lesson retrieval defect was fixed (§4b, defect E). Before that
the lesson was never retrieved and marketing never stopped.

Two honest qualifications. The planners are rule-based, so this demonstrates the
control structure rather than good judgement. And the ablation's own measured result
is a null at n=10 (§4b), so RQ4–RQ7 are still unanswered.

---

## 5. Still blocking the paper

Unchanged by this work, and none of it is code:

1. **Full 35-prompt sweep** — everything in PAPER.md §6 is currently n ≤ 5.
2. **Sourced sector benchmarks** — F54 stays PROVISIONAL until
   `evaluation/benchmarks.csv` carries citations.
3. **Competitor ground truth** — F55 is unmeasurable, so RQ3 rests on indirect
   evidence.
4. **More ablation seeds.** The harness is built and has been run at n=10. The
   direction favours the full graph on F59 in every comparison but nothing reaches
   p < 0.05, because between-seed variance is 33–70% of the means. RQ4–RQ7 remain
   unanswered. Raise `--seeds` and re-run; the machinery does not change.
