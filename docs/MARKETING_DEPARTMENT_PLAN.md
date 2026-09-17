# Orion (mabgp) — Marketing Department: Design & Implementation Plan

> Grounded in the verified codebase (`app/agents/marketing.py`,
> `app/models/departments.py:MarketingOutput`), the three reference repos (via
> `docs/PLANNER_SUBSYSTEM_DESIGN.md`), and current practice. Mirrors the shipped
> Strategy / Operations / Finance / Branding upgrades: additive, frozen-safe,
> deterministic where possible, offline-testable, gated behind a flag (default off).
> This is the **last** of the five departments.

---

## 0. Headline: Marketing has strong objective anchors — the most quantitatively checkable of the remaining work

Unlike Branding (subjective), Marketing has real numbers that must reconcile:
- Channel `budget_share_pct` values **must sum to 100**.
- `total_marketing_budget_inr` must fit within the Finance monthly operating cost.
- Marketing spend + a persona/ticket size implies **CAC** and **funnel** economics that must
  agree with Finance's revenue and the campaign-phase budgets.

So the right addition is a **deterministic marketing-consistency & unit-economics checker**
(shares sum, budget fits, CAC/customers-needed reconciliation, campaign-budget coherence),
plus a short evidence-tagged summary — exactly the "LLM generates, Python validates the
numbers" discipline used across the other departments.

The existing 4 agents are already good: persona runs first so the others target it;
channel monthly budgets are computed in code from share × total; campaign phases coerced to
the 3-phase enum; SEO favours location long-tail. The gaps are numeric and checkable.

---

## 1. What exists today (verified)

`app/agents/marketing.py` — 4 agents on frozen `MarketingOutput`:

| agent_id | Feature | Stage | Produces (frozen fields) | Computed in code |
|---|---|---|---|---|
| buyer_persona | F31 | 1 (alone) | `personas[]` (3 personas) | — |
| digital_plan | F30 | 2 | `channels[]`, `total_marketing_budget_inr`, `channel_strategy_summary` | per-channel `monthly_budget_inr = total × share%` |
| campaign_plan | F32 | 2 | `campaign_phases[]` (pre/launch/post), `launch_hook` | phase enum coercion |
| seo_content | F33 | 2 | `target_keywords`, `content_topics`, `content_frequency`, `content_formats` | — |

**Genuine gaps (NOT FOUND in the code) — all numerically checkable:**
1. **No budget-share validation.** The prompt *asks* shares to sum to 100, but nothing
   verifies it. A channel mix summing to 80% or 130% is a real, silent defect.
2. **No marketing-vs-operating-cost check.** Prompt says keep marketing spend below monthly
   operating cost; nothing enforces it. Overspending is a common failure.
3. **No CAC / customers-needed reconciliation** — the single most valuable marketing number
   and the clearest cross-department tie: given `total_marketing_budget_inr`, Finance's
   `avg_ticket_size_inr` and `projected_revenue_y1_inr`, you can compute the **customers per
   month the plan needs** and an **implied allowable CAC**, and flag when the channel plan
   is economically incoherent with Finance.
4. **No campaign-budget coherence** — do the 3 phase budgets roughly fit the monthly
   marketing budget over 90 days?
5. **No evidence tagging** — the other four departments now have it.

---

## 2. What the three repos teach Marketing (content patterns only)

From the verified analysis (`docs/PLANNER_SUBSYSTEM_DESIGN.md`), filtered to Marketing:

- **AgentArea** → compute-in-code + fail-closed for the numeric checks (share sums, CAC are
  arithmetic — compute, don't ask the LLM); `Money`/Decimal discipline. Reject Temporal/wallet.
- **AgentOS** → two-tier blockers-vs-warnings reducer + evidence provenance (`EvidenceItem`).
  → a marketing-consistency reducer emitting warnings (shares off 100, over budget, CAC
  incoherent) + a tagged summary. Reject worker runtime.
- **MiloFish/MiroFish** → schema-constrained gen + validate/cap + "sanity-anchor a generated
  value to a sibling agent's number" (Finance revenue/ticket). Reject simulation infra.

Net: the same move as before — **LLM owns creative content (personas, hooks, topics); Python
owns the numbers (shares, budget fit, CAC/funnel) and tags evidence.** Marketing is the
cleanest cross-department reconciliation case (it must agree with Finance), which is exactly
the multi-agent coherence RQ1/F57 measures.

---

## 3. The plan — deterministic marketing checker + 1 optional synthesis agent

Same proven shape. Default **off** so the measured baseline stays 21 agents / F17–F37; flag
**on** adds one Marketing agent (F33a) as a new stage 3, giving 22 total.

### 3A. New frozen-safe fields on `MarketingOutput` (append only)
```python
# --- F33a Marketing Consistency & Unit Economics (opt-in) ---
budget_share_total_pct: float | None = None    # sum of channel shares (should be ~100)
allowable_cac_inr: int | None = None           # implied max CAC from budget/customers-needed
customers_needed_monthly: int | None = None    # from Finance revenue / avg ticket
marketing_warnings: list[str] = Field(default_factory=list)
marketing_summary: str | None = None
marketing_evidence: list[EvidenceItem] = Field(default_factory=list)  # reuse
```

### 3B. Deterministic marketing checker (new `app/agents/marketing_checks.py`, pure Python, no LLM)
- **Budget-share sum**: sum `channels[].budget_share_pct`; warn if outside 95–105.
- **Budget vs operating cost**: read Finance `total_monthly_cost_inr`; warn if
  `total_marketing_budget_inr` exceeds it (or a sensible fraction).
- **CAC / customers-needed** (the headline reconciliation): from Finance
  `projected_revenue_y1_inr` / 12 ÷ `avg_ticket_size_inr` → **customers needed per month**;
  `total_marketing_budget_inr` ÷ customers-needed → **implied allowable CAC**. Warn if the
  allowable CAC is implausibly low (channel plan can't acquire that many customers that
  cheaply) — an economically incoherent plan.
- **Campaign-budget coherence**: sum of the 3 phase budgets vs ~3 months of marketing
  budget; warn on gross mismatch.
- Returns the frozen field names (share total, allowable CAC, customers-needed, warnings).

### 3C. New agent — Marketing Consistency & Unit Economics (F33a), gated, stage 3
- Runs the deterministic checker over the completed Marketing + Finance sections, then
  writes a short evidence-tagged `marketing_summary` (e.g. "Plan needs ~420 customers/month
  at ₹95 CAC; channel mix sums to 100% and fits the marketing budget"), deterministic
  fallback if the LLM is down.
- Gated behind `enable_marketing_synthesis` (default False).

### 3D. Optional prompt hardening to the existing 4 (no schema change)
- **digital_plan**: reinforce "shares MUST sum to 100 and total spend MUST stay below the
  monthly operating cost" (the checker now verifies both).
- **campaign_plan**: hint that the 3 phase budgets should roughly fit ~3 months of the
  marketing budget.

---

## 4. Per-repo designs (as requested)

| Aspect | MiroFish-based | AgentOS-based | AgentArea-based | Independent (recommended) |
|---|---|---|---|---|
| Approach | schema-gen + sanity-anchor to Finance numbers | enrich() reducer + warnings + evidence | compute-in-code for shares/CAC + fail-closed | deterministic share/budget/CAC checker + evidence agent |
| New capability | (channel monthly already computed) | consistency warnings + provenance | CAC/funnel arithmetic | **share-sum + budget-fit + CAC/customers-needed + campaign coherence + summary** |
| Fit for Orion | partial | good add | the numeric core | **best — Marketing is a numeric department; reconcile with Finance, don't invent taste** |

The **independent** design is the recommendation: Marketing's value here is *numeric
coherence with Finance*, which is objectively checkable and directly strengthens the F57
Consistency Score and the multi-agent claim (RQ1).

---

## 5. Phased implementation plan (each phase offline-testable, full suite green)

Baseline after the other four departments: **1176 passing**. Rules: regression test per
phase, offline, no new deps, frozen fields appended only, PowerShell `;`, LLM only via
`llm_client`.

| Phase | Deliverable | Files | Tests |
|---|---|---|---|
| **1** | Frozen-safe fields on `MarketingOutput` (share total, allowable CAC, customers-needed, warnings, summary, evidence) | `departments.py` | `test_marketing_schema.py` |
| **2** | Deterministic marketing checker (share sum + budget-vs-opcost + CAC/customers-needed + campaign coherence) | new `marketing_checks.py` | `test_marketing_checks.py` (hand-checked CAC, share sums, warnings) |
| **3** | Config flag `enable_marketing_synthesis` (default False) + `build_marketing_stages(synthesis)` (baseline 4 / on 5 as stage 3) | `config.py`, `marketing.py` | topology test 4 vs 5 |
| **4** | Marketing Consistency & Unit Economics agent (F33a) — runs checker + evidence-tagged summary + fallback | `marketing.py` | offline scripted-LLM test |
| **5** | Optional prompt hardening (share/budget hints) to F30/F32; wire stage 3; full suite; confirm baseline 21/F17–F37; flag-on 22 incl F33a | `marketing.py` | flag-on registry test |

**Acceptance:** baseline byte-identical (flag off); CAC/customers-needed deterministic and
hand-checked (e.g. revenue ₹84L/yr ÷ 12 ÷ ₹500 ticket = 1400 customers/month); share-sum
warning fires outside 95–105; every claim evidence-tagged; full suite offline & green; no
frozen field renamed; no new dependency.

---

## 6. Honesty notes (must appear in output)
- CAC / customers-needed are **derived from the model's own revenue and ticket assumptions**,
  so they inherit that uncertainty — they measure *internal coherence*, not real-world
  acquisition cost, and are evidence-tagged as inferences.
- The allowable-CAC "implausibly low" threshold is a **heuristic sanity flag**, not a
  guarantee; it catches gross incoherence (plan needs 5,000 customers/month on a ₹10k budget).
- Channel-mix quality (is Instagram the *right* channel?) is **not** scored — only the
  numeric coherence is. No fake "marketing quality" score.
- Default-off keeps RQ2/RQ4 comparable; promoting F33a into the measured arm is a separate
  decision (flip default + update the "21" assertions), same as the other departments.

## 7. Out of scope (would break the project)
Live ad-platform APIs / real CPM/CPC data (network + paid), keyword search-volume APIs,
a subjective channel-quality score, Temporal/workers/queues.

## 8. First action
On your go: I'll build **all 5 phases in one go** (as with Operations/Finance/Branding) —
schema → deterministic checker → flag+topology → F33a agent → prompt hardening + full suite —
and report when fully done.
