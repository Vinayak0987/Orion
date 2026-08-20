# Configuration Still To Be Done

Current state of every credential, setting and data file, and what changing each one
actually affects.

---

## 1. Current state

Run this to see it live:

```powershell
curl http://localhost:8080/health
```

| Item | State | Blocks |
|---|---|---|
| `GROQ_API_KEY` | **set and verified** | — |
| `GEMINI_API_KEY` | **set and verified** | — |
| `SERPER_API_KEY` | **set and verified** | — |
| `GOOGLE_PLACES_API_KEY` | **empty** | weakens F55 / RQ3 |
| Ollama + `llama3.2:3b` | **installed** | — |
| ChromaDB cache | **local mode, working** | — |
| PDF backend | **xhtml2pdf active** | — |
| Docker | **not installed** | nothing — not required |
| `evaluation/benchmarks.csv` | **all sources empty** | **F54 is PROVISIONAL** |
| `ground_truth_competitors` | **empty** | **F55 unmeasurable** |

**Two items block publishable results: the benchmarks and the ground truth.** Both are
data-entry tasks, not configuration.

---

## 2. API keys

### 2.1 Already configured

| Key | Free tier | Verified |
|---|---|---|
| `GROQ_API_KEY` | 14,400 req/day | 8B at 88 ms, 70B at 141 ms |
| `GEMINI_API_KEY` | per-minute limited | `gemini-3.5-flash-lite` on `v1` |
| `SERPER_API_KEY` | 2,500 searches/month | 15 snippets, 3 credits/run |

> **Rotate these.** All three were pasted into a chat transcript during development.
> If those logs are ever shared or submitted, regenerate the keys first.

### 2.2 `GOOGLE_PLACES_API_KEY` — the one decision left

**Currently empty.** The system falls back to OpenStreetMap, which works but is
weaker in a specific, measured way.

| | Google Places | OpenStreetMap (in use) |
|---|---|---|
| Key required | yes, **plus a billing account** | none |
| Ratings / review counts | yes | **none at all** |
| Named restaurants, Bandra 2 km | not measured | 30 |
| Entries tagged as ice cream shops | not measured | **zero** |
| Rate limiting | quota-based | 429 on the 3rd consecutive query |
| Latency | not measured | 3.4 s |

**What this costs you.** F55 Competitor Coverage is RQ3's headline metric. OSM
verifies *existence* but publishes no ratings, so F19's price positioning has nothing
to work from. Indian ice cream shops are not tagged as such in OSM at all, which is
why the code broadens to sector-level tags.

**Two honest options:**

**A. Attach a card to Google Cloud.** $200 free credit per month; 35 prompts use a
trivial fraction. No charge within the credit. Enable "Places API (New)", create a
key, set:

```
GOOGLE_PLACES_API_KEY=your-key
ENABLE_PLACES_API=true
```

Verify: `/health` → `grounding.competitor_source` becomes `google_places`.

**B. Stay on OpenStreetMap.** Costs nothing, requires no card. Then say so plainly in
the paper's limitations, cite the coverage measurements in `FIGURES.md` Table 8, and
scope F55 to existence-checking only.

Either is defensible. Option B is already documented in `PAPER.md` §6.6 and §8.

---

## 3. Data files that block metrics

### 3.1 `evaluation/benchmarks.csv` — blocks F54

**F54 divides by these numbers.** The shipped values are planning midpoints. While
any `source` cell is empty, `evaluation/report.py` stamps Financial Accuracy
`PROVISIONAL`.

```csv
sector,gross_margin_pct,net_margin_pct,source
food_and_beverage,62.0,9.5,"MSME Annual Report 2023-24, Table 4.2, p.61"
retail,28.0,6.0,"RBI Performance of Private Corporate Business Sector, Q3 FY24"
services,,,
technology,,,
education,,,
healthcare,,,
manufacturing,,,
creative,,,
unspecified,,,
```

Nine sectors. Candidate sources: MSME Ministry annual report sector notes; RBI
"Performance of Private Corporate Business Sector" quarterly releases; NSSO
unincorporated non-agricultural enterprise surveys; CMIE Prowess (paid — check
library access).

The loader skips `#` comment lines and malformed rows with a warning, so a partly
filled file still helps. Delete a row entirely to fall back to the built-in estimate.

Verify: the PROVISIONAL banner disappears from the generated report. Do not remove it
by hand.

### 3.2 `ground_truth_competitors` — blocks F55

In `evaluation/prompts.json`. Currently three empty lists.

```json
"ground_truth_competitors": {
  "p01": ["Naturals Ice Cream", "Apsara Ice Creams", "Baskin Robbins", "Snowbite"],
  "p12": ["Rewind The Salon", "Manish Salon", "Jawed Habib"],
  "p25": ["Clove Dental", "Dr Batra's", "Sabka Dentist"]
}
```

Count real competing businesses within 2 km by hand — Google Maps, Justdial, or a
site visit. Ten prompts is enough for a defensible F55.

**Omit a prompt rather than guessing.** The metric records it as not applicable with a
reason, which is honest; a fabricated ground truth would not be.

Verify: RQ3 in the generated report stops saying "not measurable yet".

---

## 4. Settings worth reviewing

Full list in `.env.example`. These are the ones that materially change behaviour.

### 4.1 Timeout

```
GENERATION_TIMEOUT_SECONDS=600
```

Currently 600, correct for this machine. The 120 default is sized for Groq/Gemini and
is too tight for a keyless run — 21 agents on local CPU took 120.8 s against a 120 s
limit. Lower it to 120 only if you always run with hosted keys.

### 4.2 Cache — enable before any sweep

```
ENABLE_CHROMA_CACHE=true
CHROMA_MODE=local
CHROMA_PATH=./data/chroma
```

Local file mode: no server, no Docker. Confirm `/health` →
`knowledge_cache.enabled: true`.

**This matters for the sweep.** Four arms × 35 prompts re-issues the same search
queries. Without the cache that is 4× the Serper credits *and* results that could
drift between arms — which would make a measured difference no longer attributable to
the manipulation.

### 4.3 Model selection

```
GEMINI_MODEL=gemini-3.5-flash-lite       # STRUCTURED tier, ~63 tokens per intent
GEMINI_BASELINE_MODEL=gemini-3.6-flash   # F53 baseline, pinned
GEMINI_API_VERSION=v1
GROQ_MODEL_FAST=llama-3.1-8b-instant
GROQ_MODEL_REASONING=llama-3.3-70b-versatile
OLLAMA_MODEL=llama3.2:3b
```

> Gemini 1.5 Flash, named in the original spec, was **retired** during development and
> 404s for new keys; 2.5-flash is closed to new users. **The paper must report the
> models actually used.** Re-check availability before the final sweep — this drifts.

Optionally pull the spec's larger local model (~4.7 GB, needs ~6 GB free RAM):

```powershell
ollama pull llama3.1:8b
# then OLLAMA_MODEL=llama3.1:8b
```

### 4.4 Experiment flags — leave at defaults

```
ENABLE_DYNAMIC_ROUTING=true
ENABLE_PLACES_API=true
ENABLE_OVERPASS=true
ENABLE_SERPER_API=true
```

The harness toggles these per arm and restores them afterwards. **Do not change them
manually while a sweep is running** — the `no_grounding` arm sets and restores three
of them, and a manual override would corrupt the arm assignment.

---

## 5. Environment gotcha (Windows)

An earlier PowerShell session exported some of these variables. A **non-empty** shell
variable legitimately overrides `.env`, so config can look wrong:

```powershell
foreach ($n in @("GEMINI_MODEL","GROQ_API_KEY","GEMINI_API_KEY","SERPER_API_KEY",
                 "GOOGLE_PLACES_API_KEY","OLLAMA_MODEL","GENERATION_TIMEOUT_SECONDS",
                 "CHROMA_HOST","APP_ENV","LOG_LEVEL","SQLITE_PATH")) {
  Remove-Item "env:$n" -ErrorAction SilentlyContinue
}
```

*Empty* variables are already handled — `NonEmptyEnvSettingsSource` in `config.py`
ignores them. That fix exists because an empty `SERPER_API_KEY` silently shadowed a
valid key during development, and the same thing happens with Docker `environment:`
blocks and CI runners that export unpopulated secrets.

---

## 6. Not required

| Item | Why not |
|---|---|
| Docker | ChromaDB runs in local file mode; Ollama runs natively |
| ChromaDB server | same |
| WeasyPrint locally | xhtml2pdf is pure Python and works; WeasyPrint is in the Docker image |
| PostgreSQL | SQLite is a locked decision and sufficient |
| Any paid tier | nothing in the code path costs money |
| Authentication | localhost research project — but see `WORK_REMAINING.md` §4.1 before any network exposure |

---

## 7. Pre-sweep checklist

Before `--label paper-run-1`:

- [ ] `pytest` → 869 passed
- [ ] `/health` → `status: ok`
- [ ] `/health` → `knowledge_cache.enabled: true`
- [ ] `/health` → `grounding.rq3_arm` is the arm you intend to report
- [ ] `GENERATION_TIMEOUT_SECONDS` appropriate for your provider mix
- [ ] `benchmarks.csv` sources filled (or accept PROVISIONAL)
- [ ] `ground_truth_competitors` filled for ≥10 prompts (or accept F55 unmeasured)
- [ ] Places decision made and recorded
- [ ] Stale shell variables cleared (§5)
- [ ] Fresh `--label` chosen
- [ ] Model names recorded from `/health` for the paper

Then:

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
cd backend
..\.venv\Scripts\python.exe -m evaluation.harness --all --label paper-run-1
..\.venv\Scripts\python.exe -m evaluation.report --label paper-run-1
```

---

## 8. Packages added after the original build

Installed into `.venv` and pinned in `backend/requirements.txt`. All free.

| Package | Version | Needed by | Notes |
|---|---|---|---|
| `scipy` | 1.14.1 | `evaluation/significance.py` | Constrains numpy to <2.3, so installing it downgraded numpy 2.5.1 → 2.2.6. The full suite was re-run afterwards and passes. |
| `matplotlib` | 3.9.2 | `scripts/make_figures.py` | Forced to the Agg backend at import, so it needs no display. |
| `python-pptx` | 1.0.2 | `scripts/make_deck.py` | Only used to build the review deck. Not imported by the served application. |

Neither `scipy` nor `matplotlib` is imported on the request path, so the backend
runs without them if you only want the API.

To reproduce a clean environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install python-pptx==1.0.2
```

`playwright` is installed in the **system** Python, not the venv, and is used only
to render the PDFs and figure PNGs in `docs/orion/`. It is not needed to run or
test the system.

---

## 9. Operating layer configuration

**None required.** This is worth stating explicitly because it is unusual.

The operating layer needs no API keys, no external service and no settings. It
creates its own tables on first use:

```python
from app.operating import init_all, build_scheduler
init_all()                      # idempotent; safe alongside app.db.sqlite.init_db()
sched = build_scheduler()       # wires all ten loops
sched.run_due("company-id")     # advances the business
```

Three deliberate design consequences:

- **No LLM calls.** The planners are rule-based, so a tick costs no quota. When
  LLM-backed planning is wired it must go through `app.llm.llm_client` like
  everything else, and `max_per_tick` should be lowered from its default.
- **No clock configuration.** Time is a parameter (`run_due(company, now=...)`).
  `run_forever` is the only thing that consults the wall clock.
- **No anchor configuration.** Anchors are derived from the ledger by code. There
  is nothing to set, which is the point.

### Optional: register thresholds and objectives

The drift monitor and objective review have nothing to check until you give them
something. Both are optional and both report plainly when empty:

```python
from app.operating import build_scheduler, monitors
sched = build_scheduler(
    thresholds=[monitors.Threshold("sector_margin", "gross_margin_pct", 62.0,
                                   calibrated_at="2026-01-15T00:00:00+00:00",
                                   max_age_days=90)],
    objectives=[monitors.Objective("o1", "marketing", "grow the customer base",
                                   "net_margin_pct",
                                   in_force_since="2026-04-01T00:00:00+00:00")],
)
```

Note that `sector_margin` above should use whichever figure you source in §3.1.
Registering an unsourced threshold makes the drift monitor police a number that is
itself provisional.

---

## 10. Constitution values — review before any real use

`app/operating/constitution.py` ships with placeholder limits:

| Rule | Shipped value |
|---|---|
| `C1_DAILY_SPEND_CAP` | ₹10,000 per day |
| `C2_SINGLE_SPEND_CAP` | ₹50,000 per action |

These are **code, not configuration**, deliberately: a configurable hard
constraint is a policy, and the separation is the whole point of the two-layer
design. Changing them means editing the module under review, which is what
`amend()` refuses to do at runtime and explains why.

Review them before the system is ever pointed at anything real. The policy
thresholds that decide *what a human is asked about* live separately in
`governance.Policy` and are configurable.
