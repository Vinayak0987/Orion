# Figures and tables

What each exhibit shows, and exactly where its data comes from. Nothing here is
drawn by hand; every figure traces to code or generated output, which is what makes
the paper auditable.

---

## Figure 1 — System architecture

Six-layer stack: prompt → intent classifier → orchestrator → department layer →
shared state → output layer.

**Source.** `docs/PROJECT_SPEC.md` §1.4. Redraw in draw.io or TikZ for print.
**Caption should note.** 21 agents across 5 departments; Operations conditional.

## Figure 2 — Execution DAG, both routing conditions

Side by side, because the contrast *is* RQ2's manipulation.

```
Physical                          Digital
START → strategy → ┬ finance  ┐   START → strategy → ┬ finance  → END
                   ├ branding ┼→ operations → END    ├ branding → END
                   └ marketing┘                      └ marketing→ END
```

**Source.** Generated at runtime — `GET /intent` returns `execution_plan.stages`
with each stage labelled `parallel` or `sequential`. Use the real output for two
prompts (one physical, one digital) rather than an idealised drawing.
**Caption should note.** Operations has three inbound edges and is therefore a join
barrier.

## Figure 3 — Live progress stream

Evidence that Stage 2 concurrency is real and observable, not merely asserted.

```
started strategy        → completed 20%
started finance
started branding          ← all three start before any completes
started marketing
completed branding 40% · finance 60% · marketing 80%
started operations      → completed 100%
```

**Source.** WebSocket `/ws/generate` transcript. Reproduce with a real client
against a running server; the ordering is the point.
**Alternative.** `tests/test_orchestrator.py::test_stage_2_departments_run_concurrently`
asserts pairwise time-window overlap, if a test citation is preferred to a transcript.

## Table 1 — Agent inventory

21 agents: id, department, stage, feature identifier, model tier.

**Source.** `python -c "from app.agents import describe_all_departments; ..."` —
generated from the registry, so it cannot drift from the implemented system.

## Table 2 — Provider fallback chain

Three tiers against three providers, with the model actually used per tier.

**Source.** `app/llm/chain.py::chain_for`, and `/health` → `llm_providers` for the
concrete model names at measurement time.
**Caption must note.** Models drift. Gemini 1.5 Flash was retired mid-project.

## Table 3 — Prompt set composition

Counts by sector, by budget scale, and physical versus digital.

**Source.** `evaluation/prompts.json`. Report the `version` field.

## Table 4 — Metric definitions

Five metrics: what each measures, its formula, its direction, and what makes it
inapplicable.

**Source.** `evaluation/metrics.py` docstrings. The `applicable=false` reasons are
worth listing explicitly, because the refusal to impute is a methodological choice
that a reader should be able to check.

## Table 5 — RQ1 main results

Four metrics × arms, each cell `mean (n=…, sd=…)`.

**Source.** `evaluation/results/<label>-report.md`, RQ1 section. **Paste, do not
retype.** Keep the ⚠ markers if any n < 3 survives into the final run.

## Table 6 — RQ2 routing efficiency

Token saving, time saving, completeness delta; all prompts and then restricted to
prompts where a department was actually skipped.

**Source.** Same report, RQ2 section.
**Caption must note.** Quote the restricted figure. The all-prompt mean is diluted
by physical businesses where both arms route identically and zero saving is correct.

## Table 7 — RQ3 grounding

Competitor coverage, grounded versus text-only.

**Source.** Same report, RQ3 section — **currently reports "not measurable"** until
ground truth is collected. If it still says that at submission, the table becomes a
statement of what could not be measured, and the paper says so in §8.

## Table 8 — Places versus OpenStreetMap

Measured provider trade-off, for §6.4 and §8.

| | Google Places | OpenStreetMap |
|---|---|---|
| Key required | yes, plus billing account | none |
| Ratings / review counts | yes | none at all |
| Named restaurants, Bandra 2 km | not measured | 30 |
| Named hairdressers, Bandra 2 km | not measured | 30 |
| Entries tagged as ice cream shops | not measured | zero |
| Rate limiting | quota-based | 429 on third consecutive query |
| Latency | not measured | 3.4 s tuned, 40 s untuned |

**Source.** Live probes recorded in `README.md` §"External data grounding". Re-run
before submission and date the measurement — OSM coverage changes.

## Table 9 — Reconciliation defects

The five conflicting-claim defects and their symptoms.

**Source.** Paper §4.4, cross-referenced to the regression tests that lock each fix:
`test_opex_reconciliation_overrides_an_implausible_model_figure`,
`test_revenue_ramp_is_clamped`,
`test_revenue_is_rescaled_to_the_revenue_agents_projection`,
`test_build_pl_forecast_does_not_go_backwards_into_year_two`,
`test_mape_prefers_the_steady_state_margin`.

Citing the test names is worth doing: it shows each defect is fixed and pinned.

## Figure 4 — Variance compounding

The central negative result (§7.2). Plot MAPE across repeated runs of the same
prompt, multi-agent versus baseline, to show instability rather than bias.

**Source.** Repeat one prompt ~10 times per arm and read
`<label>-metrics.csv`. Observed so far on the ice-cream prompt: 7.7, 103, 212, 95.
**This figure does not yet exist and is worth generating** — it is the strongest
available evidence for the paper's most interesting claim.

## Figure 5 — Sample generated report

One page of real output: cover, KPI row, and a financial table.

**Source.** `GET /sessions/{id}/report.pdf`. Choose a run that scored well and state
its session id and completeness score in the caption.

---

## Table 10 � Run reliability

Unplanned finding from the variance experiment.

| Arm | Runs | Produced a plan | Completion rate |
|---|---|---|---|
| multi_agent | 5 | 5 | 100% |
| baseline | 5 | 3 | 60% |

**Source.** `variance-metrics.csv`, `plan_completeness` rows.
**Caption must qualify.** The baseline is pinned to one provider by experimental
design (�5.1), so its lower reliability is partly an artefact of that control. The
defensible claim is that a multi-provider fallback chain confers resilience under
free-tier limits.

## Exhibits still to produce

| Exhibit | Blocked on |
|---|---|
| Table 5, 6 | full 35-prompt sweep |
| Table 7 | competitor ground truth |
| Figure 4 | done at n=5; raise to n=10 for a tighter SD |
| Table 8 | re-run probes and date them |
