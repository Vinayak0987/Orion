# Orion (mabgp) — Operations Department: FINAL Implementation Plan

> Developer-ready, research-grounded plan to improve the **Operations business-plan
> department** (F34–F37) and add two opt-in agents. Additive, frozen-safe, deterministic
> where possible, fully offline-testable, gated behind a flag so the measured baseline is
> byte-identical. Mirrors the shipped Strategy upgrade.
>
> Grounded in: `app/agents/operations.py`, `app/models/departments.py:OperationsOutput`,
> `app/agents/base.py`, `app/agents/strategy_scoring.py` (verified 2026-09-13); the three
> reference repos (via `docs/PLANNER_SUBSYSTEM_DESIGN.md`); and the user-supplied
> **Operations Department Deep Research Compendium v2** (28 pp), cited as [DRC].

---

## 1. Scope (settled)

Orion's "Operations" is a **business-plan department** — 4 agents that write *content* about
how a business runs. It is NOT an execution engine; that concept conflicts with the locked
stack (no Temporal/Redis/broker; stdlib sqlite3; single-node; offline tests; free tier) and
is already covered by the planner executor (`app/planning/executor.py`) and operating layer
(`app/operating/`). This plan improves the **department**. [DRC] independently frames
Operations the same way: "converts a business idea into an executable operating system"
answering supply/staffing/tech/process, as a downstream join after Strategy & Finance.

---

## 2. Baseline (verified) & the gap

Existing 4 agents on frozen `OperationsOutput`:

| agent_id | Feature | Stage | Produces | Already computes in code |
|---|---|---|---|---|
| supply_chain | F34 | 1 | `inventory_requirements`, `vendors[]`, `inventory_approach` | — |
| staffing_plan | F35 | 1 | `roles[]` | `total_headcount_y1`, `total_monthly_payroll_inr` |
| tech_stack | F36 | 1 | `tools[]` | `total_tool_cost_monthly_inr` |
| process_flow | F37 | 2 | `daily_workflow[]`, `key_processes`, `quality_checkpoints` | owner_role from staffing |

**Gaps confirmed by both code inspection and [DRC]:**
1. **No feasibility/consistency check.** [DRC §52 "Agent output contract"] defines exactly
   the checks to run: *Consistency* (staffing & process agree on role ownership),
   *Feasibility* (fits budget & scale), *Risk coverage*, *Process completeness*
   (triggers/inputs/outputs/decisions/controls). Today these only surface downstream in the
   F57 Consistency Score, never inside Operations.
2. **No compliance/licensing output.** [DRC] repeatedly ties operations to
   "GST/tax and sector licensing," "licences/certificates," "compliance workflow." Today
   only the risk agent mentions FSSAI/GST in passing; there is no structured checklist.
3. **No evidence tagging** (FACT/ASSUMPTION/UNKNOWN) — Strategy now has it; Operations doesn't.

---

## 3. The plan — improve 4, add 2, gated behind `enable_operations_synthesis` (default OFF)

Same proven shape as Strategy. Default off ⇒ baseline stays 21 agents / F17–F37, all
existing tests and RQ numbers untouched. Flag on ⇒ adds two agents as a new **stage 3**
(so they can read all of stages 1–2), giving 23 total incl. F34a, F37a.

### 3.1 New frozen-safe fields on `OperationsOutput` (append only)
```python
# --- F34a Compliance & Licensing (opt-in) ---
licences: list[Licence] = Field(default_factory=list)
compliance_notes: str | None = None
# --- F37a Operations Feasibility (opt-in) ---
feasibility_score: int | None = None                 # 0-100, computed in Python
feasibility_warnings: list[str] = Field(default_factory=list)
operations_summary: str | None = None
operations_evidence: list[EvidenceItem] = Field(default_factory=list)  # REUSE Strategy model
```
New model:
```python
class Licence(BaseModel):
    name: str                          # e.g. "FSSAI Food Licence"
    authority: str = ""                # issuing body
    when_required: str = ""            # trigger condition
    est_cost_inr: int | None = None    # marked needs-verification in notes
    evidence_kind: str = "assumption"  # fact | assumption | inference | unknown
    notes: str = ""                    # always include "verify with local authority"
```

### 3.2 New agent — Compliance & Licensing (F34a), stage 3
- Reads `context_block` (sector, business_type, location, physical flag) + risk section.
- **Gazetteer seed** (static dict, [DRC §"safety, environment, GST/tax and sector
  licensing"]): sector → obligatory licences so the obvious ones are never omitted, e.g.
  F&B → {FSSAI, Shop & Establishment, GST, Trade Licence, Fire NOC if seating};
  manufacturing → {Factory Licence, Pollution NOC, GST, Shop & Est.};
  healthcare → {Clinical Establishment registration, Bio-medical waste, GST}.
  The LLM extends with business-specific ones. (MiroFish "inject required, then extend".)
- Gazetteer items tagged `evidence_kind="fact"`; LLM-added ones `assumption`/`inference`.
- All costs `est_cost_inr` optional and every item's `notes` carries "verify locally"
  ([DRC] anti-hallucination: "must not invent current prices or guarantee availability").

### 3.3 New agent — Operations Feasibility / SOP Reviewer (F37a), stage 3
- **Deterministic Python check** in a new `app/agents/operations_feasibility.py` (like
  `strategy_scoring.py`), implementing [DRC §52] directly:
  - *Consistency*: every `process_flow.owner_role` ∈ `roles.title` (else warning + score↓).
  - *Feasibility*: `total_monthly_payroll_inr + total_tool_cost_monthly_inr` within a
    sensible fraction of the intent budget (else warning).
  - *Completeness*: ≥N quality_checkpoints, workflow has ≥N steps, ≥1 key_process.
  - *Coverage*: tech stack covers the essentials for the sector (billing/POS, accounting,
    comms) — a small checklist per [DRC §"Tech-stack"].
  → returns `feasibility_score` (0–100) + `feasibility_warnings[]`.
- **Short LLM pass**: a 2–3 sentence `operations_summary` naming the biggest operational
  risk, tagged with `operations_evidence`. **Deterministic fallback** if the LLM is down
  (AgentOS graceful-degradation pattern).

### 3.4 Prompt improvements to the existing 4 (no schema change) — from [DRC]
- **supply_chain (F34):** add SCOR framing (Plan/Source/Make/Deliver/Return) and force
  monthly quantities + storage/perishability note where relevant.
- **staffing_plan (F35):** [DRC §"most important practical transformation"] — link
  headcount to work/capacity/hours/shifts, not a bare number; keep `hire_month` 1–12.
- **tech_stack (F36):** add TOE/IT-readiness criteria (cost, security, integration,
  process fit) and [DRC] rule "don't recommend software just because it's popular."
- **process_flow (F37):** [DRC §"no pretty flowchart without ownership, exceptions,
  controls"] — require each step to have an owner, and add exception/control notes into the
  existing `quality_checkpoints`; drop/flag any `owner_role` not in `roles` (feeds F37a).

---

## 4. Phased build (each phase: regression test, offline, full suite green)

Baseline after Strategy upgrade: **1107 passing**. Rules: no new deps, frozen fields
appended only, PowerShell `;`, LLM only via `app.llm.llm_client`.

| Phase | Deliverable | Files | Tests | Stop? |
|---|---|---|---|---|
| **1** | `Licence` model + 6 new optional fields on `OperationsOutput`; reuse `EvidenceItem` | `departments.py` | `test_operations_schema.py` — existing fields untouched, new default empty, roundtrip | |
| **2** | **Deterministic feasibility scorer** implementing [DRC §52] (consistency/feasibility/completeness/coverage → score+warnings), pure Python | new `operations_feasibility.py` | `test_operations_feasibility.py` — hand-checked scores, owner-role mismatch → warning, over-budget → warning, deterministic | **← stop here for your review** |
| **3** | Config flag `enable_operations_synthesis` (default False) + `build_operations_stages(synthesis)` (baseline 4 / on 6 as stage 3) | `config.py`, `operations.py` | topology test 4 vs 6 | |
| **4** | **Compliance agent (F34a)** — gazetteer seed + LLM extend + evidence tags | `operations.py` (+ `_LICENCE_GAZETTEER`) | offline scripted-LLM: F&B→FSSAI present as `fact`; costs `needs-verification`; clamps evidence_kind | |
| **5** | **Feasibility/SOP agent (F37a)** — runs the Python scorer + short evidence-tagged summary + deterministic fallback | `operations.py` | offline: mismatch→warning; LLM-down→fallback summary; score persisted | |
| **6** | Prompt upgrades to F34–F37 (§3.4); wire stage 3; full suite; confirm baseline 21/F17–F37; flag-on 23 incl. F34a/F37a once | `operations.py` | flag-on registry test; `pytest -q` full offline | |

**Acceptance:** baseline byte-identical (flag off); feasibility score deterministic (golden
test); compliance always includes sector-required licences; every generated claim
evidence-tagged; all licences/costs carry "verify locally"; suite offline & green; no frozen
field renamed; no new dependency; no operating-layer change.

---

## 5. Decisions & honesty notes
- **Default OFF** keeps RQ2/RQ4 comparable; enabling in the measured arm is a separate,
  deliberate step (flip default + update ~30 "21" assertions), same as Strategy.
- **No RAG layer for MVP.** [DRC]'s RAG chunks are used as *prompt content and gazetteer
  seeds*, not a retrieval subsystem — adding ChromaDB-backed operations RAG is deferred
  scope creep and a runtime moving part. Revisit only with a measured reason.
- **Scoring computed in Python, not LLM-asserted** — satisfies [DRC]'s consistency/feasibility
  contract honestly (same discipline as `strategy_scoring.py` and the finance totals).
- **Regulations are jurisdiction/time-sensitive** — gazetteer guarantees the obvious
  licences aren't missed; it does not guarantee completeness or current fees. Every item
  says "verify with the local authority."
- **Out of scope** (would break the project): Temporal/workers/queues/DLQ/schedulers/SLA/
  incident engines/chaos-load testing/cross-run learning. Covered by the planner executor
  and operating layer, or forbidden by the locked stack / anchor invariant.

---

## 6. Per-repo reuse summary (references, not templates)
- **MiroFish** → "inject required fallback items, then let the LLM extend" (gazetteer) +
  validate/normalize/cap. Reject simulation/process-lifecycle infra.
- **AgentOS** → two-tier blockers-vs-warnings + evidence provenance (`EvidenceItem`). Reject
  worker runtime / task-graph execution.
- **AgentArea** → compute-in-code + fail-closed discipline for the feasibility scorer.
  Reject Temporal/workers/queues/events broker.
- **[DRC]** → the output-contract checks (§3.3), sector licence set (§3.2), and the SCOR /
  capacity-staffing / TOE / BPM-maturity framings for the improved prompts (§3.4), plus
  anti-hallucination rules.

---

## 7. First action
On your go, I build **Phase 1 + Phase 2** (schema + deterministic feasibility scorer with
its tests), run them, and **stop** so you can verify before any LLM agents are added.
