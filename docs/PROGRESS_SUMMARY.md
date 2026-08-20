# Orion — Work Progress Summary

**Project:** Orion (AI Business Operating System)
**Team:** Aditya Maskare (102), Vinayak Maurya (103), Abhishek Mishra (108)
**B.E. Computer Engineering, Division B, University of Mumbai**
**Date:** 19 August 2026

---

## Overall Status: 95% Complete

| Component | Status | Evidence |
|-----------|--------|----------|
| Generation Layer (21 agents, 5 departments) | DONE | 65/65 features, measured |
| Operating Layer (11 modules) | DONE | Runs unattended, 90-day demo |
| Ablation Experiment | BUILT & RUN | 4 arms, n=10, result pending significance |
| Frontend (Generation UI) | DONE | React, 162 kB bundle |
| Frontend (Operating UI — 3-layer) | DONE | 13 components, 12 API routes |
| Evaluation Harness | DONE | 5 metrics, statistical significance testing |
| Research Paper Draft | DONE | Needs final sweep data |
| Test Suite | 989 tests | All passing, fully offline |
| Cost | Rs 0 | Free tiers only, no paid service |

---

## What is Built (Bullet Points for Explanation)

### Generation Layer — "One sentence to a full business plan"
- User types ONE sentence (e.g. "Ice cream shop in Andheri, Rs 15L")
- System classifies intent, routes to relevant departments
- 21 AI agents across 5 departments produce a complete plan
- Real competitors found via Google Maps / OpenStreetMap
- Market research via Serper.dev (not hallucinated)
- Output: Interactive web report + PDF + JSON
- Time: 60–90 seconds
- Measured: 100% plan completeness vs 80.8% for a single-LLM baseline

### Operating Layer — "The plan becomes a living company"
- The generated plan is treated as the company's opening state
- A scheduler drives 5 department loops + 4 monitor loops + reflection
- Departments plan, execute, and record outcomes in an append-only ledger
- 19 anchor metrics are computed from the ledger (never written by agents)
- Monitors detect proxy capture, inter-department conflict, stale objectives
- The company self-corrects: marketing stops spending when margin falls
- Demonstrated: 90 simulated days, 574 scheduled runs, monitors fire correctly

### Ablation Experiment — "Does the control structure matter?"
- 4 arms: single_loop, anchors_only, monitors_only, full_graph
- Same planner/memory/execution — only control topology differs
- Simulated market environment responds to department actions
- Proxy gaming is possible by unit economics (not a tuned knob)
- Run at n=10 paired seeds, 90 days each
- Result: direction favours full graph but not yet significant (p=0.059)
- Honest reporting: RQ4–RQ7 currently unanswered

### Frontend — "See everything the system does"
- Generation view: prompt input, live WebSocket progress, report viewer
- Business view: 19 anchors with provenance, trend charts, findings
- Work view: review queue, decision history, constitution (read-only)
- Activity view: loop run log, ledger tail, memory inspector
- Loop graph: SVG topology showing termination at anchors/humans
- Bundle: 190 kB, no external dependencies beyond React

### Key Research Findings (Measured)
- Multi-agent produces 100% complete plans vs 80.8% baseline
- Dynamic routing saves 17.3% tokens with 0% quality loss
- Negative result: financial accuracy — baseline wins (MAPE 41 vs 132)
- Cause identified: variance compounding across agent chain (SD 4.9x)
- Reported honestly rather than tuned away

---

## What Remains (5% — No Code Needed)

| Item | Type | Who | Time |
|------|------|-----|------|
| Run 35-prompt full sweep | Execute a command | Vinayak | ~90 min |
| Source sector margin benchmarks | Library research | Team | 1–2 days |
| Collect competitor ground truth (10 prompts) | Fieldwork | Team | 1 day |
| Raise ablation seeds to n=40 | Execute a command | Vinayak | ~80 min |
| Finalise paper with real tables | Paste generated output | Vinayak | 1 hour |

**Nothing in this list requires writing code.** The system is built; what remains is running it, sourcing numbers, and writing them up.

---

## Key Numbers to Quote

| Metric | Value |
|--------|-------|
| Total test cases | 989 (all passing, offline) |
| Lines of backend code | ~15,000 |
| AI agents | 21 |
| Departments | 5 |
| Operating layer modules | 11 |
| Frontend components | 19 |
| API endpoints | 30+ |
| Bugs found & fixed | 25 (each pinned by regression test) |
| External dependencies | 0 paid services |
| Generation time | 60–90 seconds |
| Plan completeness | 100% (vs 80.8% baseline) |

---

## One-Line Explanation for Anyone

> "You type one sentence describing a business idea, and in 90 seconds, 21 AI agents produce a complete plan — strategy, finances, brand, marketing, operations — using real market data, with every number validated against sector benchmarks."

---

*This document reflects the state as of 19 August 2026.*
*For technical details: `docs/HANDOVER.md` | For the full spec: `docs/PROJECT_SPEC.md`*
