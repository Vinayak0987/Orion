# Reproducing the results

Exact steps to regenerate every number in the paper from a clean checkout.

---

## 1. Environment

```powershell
python -m venv .venv                  # Python 3.11+ (verified on 3.13.2)
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item .env.example .env
```

The system runs with **zero API keys**, falling back to a local model. Every table
in the paper, however, was produced with the hosted free tiers configured — record
in the paper which configuration you used, because latency and provider mix differ.

## 2. Verify the build before measuring

```powershell
cd backend
pytest                                # expect: 517 passed
```

The suite runs fully offline. A socket guard fails any test that opens an outbound
connection, so a passing run provably consumed no API quota. If a test fails, do not
proceed to the sweep — the metrics are computed by the same code the tests cover.

## 3. Configure providers

| Variable | Free tier | Needed for |
|---|---|---|
| `GROQ_API_KEY` | 14,400 req/day | agent execution (speed and quality) |
| `GEMINI_API_KEY` | per-minute limited | intent extraction, and the F53 baseline |
| `SERPER_API_KEY` | 2,500 searches/month | F39 market research grounding |
| `GOOGLE_PLACES_API_KEY` | $200 credit/month, card required | F38 competitor grounding |

Without `GOOGLE_PLACES_API_KEY` the system uses OpenStreetMap. That is a documented
substitution with measured consequences, not a silent degradation — see §6.4 of the
paper. Record which you used.

Confirm what the system will actually do:

```powershell
uvicorn app.main:app --port 8080
# then GET /health and read the "grounding" block:
#   competitor_source: google_places | openstreetmap | llm_inferred
#   rq3_arm:           grounded | text_only
```

## 4. Prerequisites specific to the paper's numbers

Three items must be completed or the corresponding metric is not publishable.

### 4.1 Sector margin benchmarks (blocks F54)

Fill `evaluation/benchmarks.csv`. Every row needs a citation in the `source` column:

```csv
sector,gross_margin_pct,net_margin_pct,source
food_and_beverage,62.0,9.5,"MSME Annual Report 2023-24, Table 4.2, p.61"
```

While any row is unsourced, `evaluation/report.py` stamps financial accuracy
PROVISIONAL. Do not remove that banner manually — fill the sources and it clears
itself.

Candidate sources: MSME Ministry annual report sector notes; RBI "Performance of
Private Corporate Business Sector" quarterly releases; NSSO unincorporated
non-agricultural enterprise surveys; CMIE Prowess sector aggregates (paid, check
library access).

### 4.2 Competitor ground truth (blocks F55)

Fill `ground_truth_competitors` in `evaluation/prompts.json`. For each prompt you
intend to score, count the real competing businesses within 2 km by hand — Google
Maps, Justdial, or a site visit — and list their names:

```json
"p01": ["Naturals Ice Cream", "Apsara Ice Creams", "Baskin Robbins", "Snowbite"]
```

Omit a prompt entirely rather than guessing at its ground truth; the metric records
it as not applicable and the report says so.

### 4.3 Enable the cache before sweeping

The sweep issues the same search queries once per arm. Caching prevents four times
the credit spend and, more importantly, prevents results drifting between arms —
which would make a measured difference no longer attributable to the manipulation.

Caching defaults to a local directory and needs no server:

```
ENABLE_CHROMA_CACHE=true
CHROMA_MODE=local
```

Confirm via `/health` that `knowledge_cache.enabled` is `true` before starting.

## 5. Run the sweep

```powershell
$env:PYTHONPATH="<repo>/backend;<repo>"
python -m evaluation.harness --all --label paper-run-1
```

Four arms over 35 prompts. Budget roughly 90 minutes on free tiers; individual
arm-runs took 15–60 seconds, with the spread caused by burst rate limits pushing
some agents onto the local model.

Results are written to SQLite after every prompt, so an interrupted sweep keeps what
it measured. Re-running with the same label appends; use a fresh label for a clean
run.

Smaller runs while iterating:

```powershell
python -m evaluation.harness --arms multi_agent baseline --limit 5 --label smoke
python -m evaluation.harness --all --prompts p01 p17 --label pair
```

## 6. Generate the tables

```powershell
python -m evaluation.report --label paper-run-1
```

Produces, in `evaluation/results/`:

| File | Contents |
|---|---|
| `paper-run-1-metrics.csv` | one row per (prompt, arm, metric) — the raw data |
| `paper-run-1-summary.csv` | one row per (arm, metric) with n, mean, median, sd |
| `paper-run-1-report.md` | the RQ1/RQ2/RQ3 tables, ready to paste |

Paste the generated tables into §6 of the paper rather than retyping them. Every
figure carries its own `n`, because metrics skip prompts where they do not apply and
two arms can legitimately have different sample sizes.

## 7. Reading the report honestly

The report is designed to make weak results visible rather than presentable.

- **⚠ on a mean** means n < 3. Not a finding.
- **PROVISIONAL banner** means benchmarks are unsourced (§4.1).
- **"Not measurable yet"** under RQ3 means ground truth is missing (§4.2).
- **Unscored measurements** are listed by reason at the end. A metric that could not
  be computed records why, rather than contributing a zero.

If a section says a result is not measurable, the paper must say so too.

## 8. What to record in the paper

| Item | Where to find it |
|---|---|
| Models actually used | `/health` → `llm_providers`, and any `model_substituted` warnings in the sweep log |
| Provider mix per run | generated report, and `metadata.providers_used` in any stored package |
| Grounding arm | `/health` → `grounding.rq3_arm` |
| Benchmark sources | `evaluation/benchmarks.csv` |
| Test count | `pytest` output |
| Prompt set version | `evaluation/prompts.json` → `version` |

Model availability drifts. Gemini 1.5 Flash, named in the original design, was
retired during development. Report the models you measured, not the ones you planned.
