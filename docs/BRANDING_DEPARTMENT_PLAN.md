# Orion (mabgp) — Branding Department: Design & Implementation Plan

> Grounded in the verified codebase (`app/agents/branding.py`,
> `app/models/departments.py:BrandingOutput`), the three reference repos (via
> `docs/PLANNER_SUBSYSTEM_DESIGN.md`), and current practice. Mirrors the shipped
> Strategy / Operations / Finance upgrades: additive, frozen-safe, deterministic where
> possible, offline-testable, gated behind a flag (default off).

---

## 0. Honest headline: Branding is the most *subjective* department

Strategy/Operations/Finance had objective anchors to compute against (SOM, budget, margins,
cash). Branding is different: a brand name, tone, colour palette and logo direction are
**creative and largely subjective** — there is no ground-truth "correct" tagline. This
matters for the design:

- The "LLM generates, Python validates/scores" discipline still applies, but the Python
  part can only check **objective, verifiable properties** (hex validity, name uniqueness
  vs competitors, WCAG colour contrast, font availability) — **not** taste.
- So the highest-value additions are a **deterministic brand-consistency & accessibility
  checker** (things that are genuinely checkable) and a **naming safety/uniqueness check**,
  not a "brand quality score" that would just be the LLM grading its own taste.

The existing 4 agents are already solid: naming runs first so the others reference the
chosen name; hex is validated (`_clean_hex`); fonts are constrained to Google Fonts;
visual direction adapts to physical vs digital. The gaps are specific and checkable.

---

## 1. What exists today (verified)

`app/agents/branding.py` — 4 agents on frozen `BrandingOutput`, all FAST tier:

| agent_id | Feature | Stage | Produces (frozen fields) | Already validated in code |
|---|---|---|---|---|
| brand_naming | F26 | 1 (alone) | `name_candidates[]`, `recommended_name` | recommended∈candidates; dedup vs competitors (prompt only) |
| brand_identity | F27 | 2 | `personality_traits`, `color_palette` (hex), `heading_font`, `body_font` | `_clean_hex` validates/repairs hex |
| brand_voice | F28 | 2 | `tone`, `taglines`, `sample_social_post`, `voice_dos`, `voice_donts` | — |
| visual_design | F29 | 2 | `logo_style`, `visual_mood`, `signage_direction` | physical/digital branch |

**Genuine gaps (NOT FOUND in the code) — all objectively checkable:**
1. **No colour-contrast / accessibility check.** The palette is generated but never checked
   for **WCAG contrast** (primary vs white/black text). A brand whose primary colour fails
   contrast is a real, measurable defect — and this is pure math (relative luminance ratio).
2. **No name-safety / uniqueness signal.** Naming *asks* the LLM not to reuse competitor
   names, but nothing verifies it. A deterministic check against the Strategy competitor
   list (and a small "big Indian chains" denylist) catches obvious collisions.
3. **No brand-consistency check.** Nothing verifies the palette/tone/personality are
   internally coherent or that the recommended name actually appears in the candidate list
   with a rationale.
4. **No evidence tagging** (FACT/ASSUMPTION/…) — the other three departments now have it.

---

## 2. What the three repos teach Branding (content patterns only)

From the verified analysis (`docs/PLANNER_SUBSYSTEM_DESIGN.md`), filtered to a creative
content department:

- **MiroFish** → schema-constrained generation + validate/normalize/cap
  (`ontology_generator`), and "sanity-anchor a generated value to a known constraint". →
  Branding already does this for hex; extend to contrast + name uniqueness. Reject
  simulation infra.
- **AgentOS** → `enrich()` reducer + evidence provenance + the readiness/blocker discipline
  (`collectPlanBlockers` vs `collectPlanWarnings`). → a brand-consistency reducer that emits
  **warnings** (low contrast, name collision, missing rationale) rather than a fake score.
  Reject worker runtime.
- **AgentArea** → compute-in-code + fail-closed for the objective checks (contrast is
  arithmetic, so compute it, don't ask the LLM). Reject Temporal/wallet.

Net: the repos point at the same move — **the LLM owns taste; Python owns the objective,
measurable brand properties (contrast, uniqueness, coherence) and tags evidence.**

---

## 3. The plan — deterministic brand checker + 1 optional synthesis agent

Same proven shape. Default **off** so the measured baseline stays 21 agents / F17–F37; flag
**on** adds one Branding agent (F29a) as a new stage 3, giving 22 total.

### 3A. New frozen-safe fields on `BrandingOutput` (append only)
```python
# --- F29a Brand Consistency & Accessibility (opt-in) ---
contrast_ratio: float | None = None          # primary vs white, WCAG luminance ratio
contrast_rating: str | None = None           # "AAA" | "AA" | "AA-large" | "fail"
brand_warnings: list[str] = Field(default_factory=list)
name_collision: bool | None = None           # recommended name clashes with a known/competitor name
brand_summary: str | None = None
brand_evidence: list[EvidenceItem] = Field(default_factory=list)  # reuse
```

### 3B. Deterministic brand checker (new `app/agents/branding_checks.py`, pure Python, no LLM)
- **WCAG contrast**: compute relative luminance of `primary_hex` and the contrast ratio
  against white (#FFFFFF) and black (#000000); pick the better; classify AAA (≥7), AA (≥4.5),
  AA-large (≥3), else fail. Pure math, deterministic, unit-testable — this is the standard
  W3C formula, a real accessibility standard.
- **Name collision**: lowercase-compare `recommended_name` against (a) the Strategy
  competitor names in state and (b) a small static denylist of major Indian chains
  (e.g. common national F&B/retail names). Returns `name_collision: bool` + a warning.
- **Consistency warnings** (AgentOS two-tier): recommended name not in candidates; palette
  missing; fewer than N personality traits; no taglines; heading==body font.
- Returns a dict of the frozen field names (contrast_ratio/rating, name_collision,
  brand_warnings).

### 3C. New agent — Brand Consistency & Accessibility (F29a), gated, stage 3
- Runs the deterministic checker over the completed Branding section (reads
  `color_palette`, `recommended_name`, competitors), then writes a short evidence-tagged
  `brand_summary` (e.g. "Primary colour passes AA contrast; name is distinct from nearby
  competitors"), with a deterministic fallback if the LLM is down.
- Gated behind `enable_branding_synthesis` (default False).

### 3D. Optional prompt hardening to the existing 4 (no schema change)
- **brand_identity**: add "ensure the primary colour has adequate contrast for text
  legibility" to the prompt so the LLM aims for a palette the checker will pass (the checker
  still verifies, but this reduces failures).
- **brand_naming**: keep the competitor-dedup instruction; the checker now verifies it.

---

## 4. Per-repo designs (as requested)

| Aspect | MiroFish-based | AgentOS-based | AgentArea-based | Independent (recommended) |
|---|---|---|---|---|
| Approach | schema-gen + validate/cap (hex already) | enrich() reducer + warnings + evidence | compute-in-code for objective checks | deterministic contrast+uniqueness checker + evidence agent |
| New capability | (hex already present) | consistency warnings + provenance | WCAG contrast math | **WCAG contrast + name-collision + coherence warnings + summary** |
| Fit for Orion | partial | good add | the checkable core | **best — adds only what's objectively verifiable, no fake taste score** |

The **independent** design is the recommendation: it adds *only checkable* value (contrast,
uniqueness, coherence) and refuses to invent a subjective "brand quality" number — which is
the honest choice for a creative department and defensible in the paper.

---

## 5. Phased implementation plan (each phase offline-testable, full suite green)

Baseline after Strategy+Operations+Finance: **1150 passing**. Rules: regression test per
phase, offline, no new deps, frozen fields appended only, PowerShell `;`, LLM only via
`llm_client`.

| Phase | Deliverable | Files | Tests |
|---|---|---|---|
| **1** | Frozen-safe fields on `BrandingOutput` (contrast, collision, warnings, summary, evidence) | `departments.py` | `test_branding_schema.py` |
| **2** | Deterministic brand checker (WCAG contrast math + name collision + coherence warnings) | new `branding_checks.py` | `test_branding_checks.py` (hand-checked contrast ratios, known collisions) |
| **3** | Config flag `enable_branding_synthesis` (default False) + `build_branding_stages(synthesis)` (baseline 4 / on 5 as stage 3) | `config.py`, `branding.py` | topology test 4 vs 5 |
| **4** | Brand Consistency & Accessibility agent (F29a) — runs checker + evidence-tagged summary + fallback | `branding.py` | offline scripted-LLM test |
| **5** | Optional prompt hardening (contrast hint) to F27; wire stage 3; full suite; confirm baseline 21/F17–F37; flag-on 22 incl F29a | `branding.py` | flag-on registry test |

**Acceptance:** baseline byte-identical (flag off); contrast ratio deterministic and matches
the WCAG formula (golden test with hand-computed ratios, e.g. black-on-white = 21.0);
name-collision detects a competitor-name reuse; warnings surface real coherence issues;
every claim evidence-tagged; full suite offline & green; no frozen field renamed; no new
dependency.

---

## 6. Honesty notes (must appear in output)
- **No subjective "brand score."** Branding quality (is this a *good* name?) is not
  computable; the checker only measures objective properties (contrast, uniqueness,
  coherence). Claiming a taste score would be dishonest for the paper.
- Contrast rating uses the **W3C WCAG 2.x relative-luminance formula** — a real, citable
  standard, computed in Python (not asserted by the LLM).
- The name-collision denylist is a *best-effort* signal, not a trademark search — flagged
  as such; real IP clearance needs a professional search.
- Default-off keeps RQ2/RQ4 comparable; promoting F29a into the measured arm is a separate
  decision (flip default + update the "21" assertions), same as the other departments.

## 7. Out of scope (would break the project or add no honest value)
Live trademark/domain-availability APIs (network + paid), image/logo generation (no image
model in the free/offline stack), a subjective brand-quality LLM score (not verifiable),
Temporal/workers/queues.

## 8. First action
On your go: **Phase 1 (schema) + Phase 2 (deterministic WCAG contrast + collision checker)**,
then stop for review before the LLM agent — same rhythm as the other departments.
