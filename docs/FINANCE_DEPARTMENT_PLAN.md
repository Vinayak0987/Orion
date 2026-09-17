# Orion (mabgp) — Finance Department: Design & Implementation Plan

> Grounded in the verified codebase (`app/agents/finance.py`, `app/agents/benchmarks.py`,
> `app/models/departments.py:FinanceOutput`), the three reference repos (via
> `docs/PLANNER_SUBSYSTEM_DESIGN.md`), and current practice. Mirrors the shipped
> Strategy/Operations upgrades: additive, frozen-safe, deterministic where possible,
> offline-testable, gated behind a flag.

---

## 0. Honest headline: Finance is already the most mature department

Unlike Strategy and Operations (which had real gaps), **Finance is already excellent.**
`finance.py` already implements the exact disciplines the repos and research recommend, and
more thoroughly than the other departments:

- **"LLM supplies drivers, Python does the arithmetic"** — the P&L agent asks for 6 drivers
  and computes all 20 periods, both margins and break-even in code (`_build_pl`).
- **Cross-agent reconciliation** — `_resolve_opex` (P&L opex vs cost agent's itemised sum),
  `_reconcile_revenue` (P&L ramp vs revenue agent's Y1), `_bounded_revenue` (Y1 capped at
  Strategy's SOM and a budget multiple). These are anti-hallucination guards derived from
  *real observed failures* on live sweeps (documented in the code comments).
- **Benchmark provenance discipline** — `benchmarks.py` already has `sourced`/`UNSOURCED`
  tracking, a CSV loader (`load_benchmarks_csv`), and the evaluation report refuses to
  present an unqualified F54 MAPE while any benchmark is unsourced.
- **Steady-state vs year-1 margin** — already separates ramp-up from mature margin for F54.

So the Finance plan is **different in kind** from Strategy/Operations: there is little
"missing capability" to bolt on. The highest-value work is (a) **the dataset** you asked
about — sourcing the benchmark CSV so F54 becomes publishable — and (b) a small,
optional **synthesis agent** for the one genuine gap: cash-flow/runway and unit economics,
which the current P&L does not surface.

---

## 1. What exists today (verified)

`app/agents/finance.py` — 4 agents on frozen `FinanceOutput`:

| agent_id | Feature | Stage | Produces (frozen fields) | Computed in code |
|---|---|---|---|---|
| revenue_model | F22 | 1 | `revenue_streams[]`, `pricing_strategy`, `avg_ticket_size_inr`, `projected_revenue_y1/2/3_inr`, `seasonality_notes` | Y1 capped at SOM/budget (`_bounded_revenue`) |
| cost_structure | F23 | 1 | `setup_costs[]`, `recurring_costs[]`, totals, `budget_utilization_pct`, `within_budget` | totals + utilisation |
| funding_strategy | F24 | 2 | `funding_approach`, `funding_amount_inr`, `funding_schemes[]`, `funding_timeline` | — (named Indian schemes: Mudra, CGTMSE, PMEGP, Stand-Up India) |
| pl_forecast | F25 | 2 | `pl_forecast[]` (20 periods), `gross_margin_pct`, `net_margin_pct`, `steady_state_net_margin_pct`, `break_even_month`, `benchmark_margin_pct` | all periods, margins, break-even, reconciliations |

**Genuine gaps (NOT FOUND in the code):**
1. **No cash-flow / runway view.** The P&L computes profit but not *cash position* over
   time — the single most common reason Indian SMEs fail is running out of cash before
   break-even, and the plan never shows months-of-runway or the low-cash point.
2. **No unit economics.** No CAC / contribution-margin / payback surfaced, even though the
   ingredients exist (avg_ticket, COGS %, marketing spend).
3. **The benchmark dataset is unsourced.** `benchmarks.py` is wired for real data but ships
   planning midpoints marked `UNSOURCED`; F54 is therefore "provisional" by the code's own
   rule. **This is the dataset you asked about.**
4. **No evidence tagging** (FACT/ASSUMPTION/…) — Strategy/Operations now have it; Finance
   doesn't.

---

## 2. What the three repos teach Finance (content patterns only)

From the verified analysis (`docs/PLANNER_SUBSYSTEM_DESIGN.md`), filtered to Finance:

- **AgentArea** → `EffectivePolicy`/finance-totals discipline (compute-in-code, fail-closed)
  and `Money`/Decimal accounting to avoid float drift. **Finance already does the first;
  the Decimal point is a minor hardening option.** Reject Temporal/wallet/x402 payments.
- **AgentOS** → derived-not-asserted reducer + evidence provenance (`EvidenceItem`). →
  Finance can add evidence tags and a deterministic cash-flow computed from existing
  numbers. Reject worker runtime.
- **MiroFish** → schema-constrained generation + rule fallback (already present as the
  benchmark fallbacks) + `report_agent`'s "sanity-anchor a number to a known quantity"
  (already present as SOM/budget caps). Reject simulation infra.

Net: Finance already embodies the repos' best lessons. The transferable *new* ideas are
**Decimal money**, **evidence tags**, and a **deterministic cash-flow/unit-economics
computation** — plus the dataset.

---

## 3. The plan — dataset first, then one optional synthesis agent

Two workstreams. The **dataset** is the highest-value, lowest-risk item and needs no flag.
The **synthesis agent** mirrors the Strategy/Operations pattern (gated, default off).

### 3A. Benchmark dataset (the "dataset if necessary" you asked for) — DO THIS FIRST
The infrastructure already exists (`benchmarks.py` + `load_benchmarks_csv` +
`evaluation/benchmarks.csv`). The work is **sourcing real cited figures**, not code.

Recommended sources (India MSME margins, per the code's own suggestions + best practice):
- **MSME Ministry Annual Report** sector notes (gross/net margin by activity).
- **RBI "Performance of Private Corporate Business Sector"** quarterly releases (sector aggregates).
- **NSSO / Annual Survey of Industries (ASI)** for manufacturing.
- **CMIE Prowess** sector aggregates (paid; cite if accessible).
- Trade-body reports (e.g. NRAI for F&B, RAI for retail) for sector-specific net margins.

Deliverable: fill `evaluation/benchmarks.csv` with `sector,gross_margin_pct,net_margin_pct,source`
rows citing exact table + year. The harness auto-loads it; `all_sourced()` flips true; the
evaluation report drops the "provisional" label on F54. **No code change — this is a
research/data task with a clear, tested ingestion path.**

> Honesty: I cannot fabricate these figures. I can (a) wire a documented CSV template with
> placeholder rows clearly marked unsourced, and (b) if you want, search for and propose
> specific cited values for you to verify — but the citations must be real and checked by
> you before they go in the paper.

### 3B. New agent — Cash-Flow & Unit-Economics (F25a), gated, stage 3
The one genuine capability gap, computed deterministically from existing numbers.
- **Deterministic Python** (new `app/agents/finance_cashflow.py`, like `strategy_scoring.py`):
  from the existing `pl_forecast` periods + `total_setup_cost_inr` + `funding_amount_inr`,
  compute a **monthly cash balance** (opening capital − setup − cumulative net profit path),
  the **lowest-cash month**, **months of runway**, and **unit economics**
  (contribution margin = avg_ticket × (1 − COGS%); CAC from marketing spend ÷ acquisitions
  if available; payback). No LLM.
- **Short LLM pass**: a 2–3 sentence `finance_summary` naming the biggest financial risk
  (e.g. "cash dips to ₹1.2L in month 4 — arrange the Mudra loan before then"), evidence-tagged,
  with a deterministic fallback.
- New frozen-safe fields on `FinanceOutput` (append only): `cash_flow[]` (month, cash_balance),
  `lowest_cash_month`, `lowest_cash_inr`, `runway_months`, `contribution_margin_pct`,
  `finance_summary`, `finance_evidence` (reuse `EvidenceItem`).

Gated behind `enable_finance_synthesis` (default False → baseline 21 agents / F22–F25
unchanged; on → finance has 5 agents, adds F25a as stage 3).

### 3C. Optional hardening to the existing 4 (no schema change)
- Consider `Decimal` for the P&L arithmetic (AgentArea `Money` pattern) to remove float
  rounding drift — low priority, current `int` rounding is already stable.
- Minor prompt: have `funding_strategy` size funding against the *cash gap* (from 3B) rather
  than just cost — only if 3B lands.

---

## 4. Per-repo designs (as requested)

| Aspect | MiroFish-based | AgentOS-based | AgentArea-based | Independent (recommended) |
|---|---|---|---|---|
| Approach | schema-gen + rule fallback + sanity anchors | enrich() reducer + evidence provenance | compute-in-code + fail-closed + Decimal money | dataset + deterministic cash-flow agent + evidence |
| New capability | (already present) | evidence tags | Decimal hardening | **cash-flow/runway/unit-economics + sourced benchmarks** |
| Fit for Orion | already done | good add | minor | **best — fills the real gap, keeps discipline** |

The **independent** design is the recommendation: Finance's arithmetic discipline is already
world-class for this project; the missing pieces are *cash* (not profit), *unit economics*,
*evidence tags*, and *a citable dataset*.

---

## 5. Phased implementation plan (each phase offline-testable, full suite green)

Baseline after Strategy+Operations: **1130 passing**. Rules: regression test per phase,
offline, no new deps, frozen fields appended only, PowerShell `;`, LLM only via `llm_client`.

| Phase | Deliverable | Files | Tests |
|---|---|---|---|
| **1** | Benchmark CSV: documented template + (with your verification) sourced rows; confirm `load_benchmarks_csv` applies them and `all_sourced()` flips | `evaluation/benchmarks.csv` | extend `test_evaluation.py` (already tests the loader) |
| **2** | Frozen-safe fields + models on `FinanceOutput` (cash_flow, runway, unit econ, evidence) | `departments.py` | `test_finance_schema.py` |
| **3** | Deterministic cash-flow / unit-economics scorer | new `finance_cashflow.py` | `test_finance_cashflow.py` (hand-checked, deterministic) |
| **4** | Config flag `enable_finance_synthesis` (default False) + `build_finance_stages(synthesis)` (baseline 4 / on 5 as stage 3) | `config.py`, `finance.py` | topology test 4 vs 5 |
| **5** | Cash-Flow & Unit-Economics agent (F25a) — runs the scorer + evidence-tagged summary + fallback | `finance.py` | offline scripted-LLM test |
| **6** | Optional Decimal hardening / funding-vs-cash-gap prompt; wire stage 3; full suite; confirm baseline 21/F22–F25; flag-on 22 incl F25a | `finance.py` | flag-on registry test |

**Acceptance:** baseline byte-identical (flag off); cash-flow deterministic (golden test);
runway/lowest-cash computed from real P&L periods; every claim evidence-tagged; benchmark
CSV sourced (or clearly marked unsourced); full suite offline & green; no frozen field
renamed; no new dependency.

---

## 6. Honesty notes (must appear in output)
- **Benchmark figures cannot be fabricated.** I will wire the ingestion and, if asked,
  propose *specific cited* values — but you must verify every citation before it enters the
  paper. Until then F54 stays "provisional" by the code's own rule (correct behaviour).
- Cash-flow/runway is a **projection from the model's drivers**, not a guarantee; it inherits
  the same uncertainty as the P&L and is evidence-tagged accordingly.
- Default-off keeps RQ2/RQ4 comparable; promoting F25a into the measured arm is a separate
  decision (flip default + update the "21" assertions), same as Strategy/Operations.

## 7. Out of scope (would break the project)
Real-time market data feeds, live accounting integrations, payment rails (AgentArea
wallet/x402), Monte-Carlo cash simulation, Temporal — all conflict with the offline/free/
single-node locked stack or the anchor invariant.

## 8. First action
On your go: **Phase 1 (benchmark CSV template + loader confirmation)** and **Phase 2–3
(schema + deterministic cash-flow scorer)**, then stop for your review before the LLM agent.
Tell me whether you want me to also research and propose specific cited benchmark values for
you to verify.
