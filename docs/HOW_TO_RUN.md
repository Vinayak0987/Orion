# How to Run MABGP

Everything needed to get the system running, verified against this machine
(Windows, Python 3.13.2, PowerShell).

---

## 0. What you need

| Requirement | Status on this machine | Notes |
|---|---|---|
| Python 3.11+ | 3.13.2 installed | 3.11 is the minimum (`StrEnum`, `datetime.UTC`) |
| Node.js 18+ | v23.1.0 installed | frontend only |
| Ollama | installed, `llama3.2:3b` pulled | optional but recommended |
| Docker | **not installed** | not required — see §6 |
| API keys | Groq, Gemini, Serper set; Places empty | all optional |

The system runs with **zero API keys**. It falls back to a local model.

---

## 1. First-time setup

```powershell
cd C:\Users\Vinayak\Desktop\kiro

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r backend/requirements.txt

Copy-Item .env.example .env      # already done; skip if .env exists
```

The virtual environment lives at the **repo root**, not inside `backend/`.

### Extra packages installed beyond requirements.txt

These were added during development and are needed for the full feature set:

```powershell
pip install langgraph==0.2.62 langchain-core==0.3.29 chromadb==0.5.23 jinja2==3.1.5 xhtml2pdf==0.2.16
```

---

## 2. Verify the build before anything else

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
```

**Expect: `869 passed`.**

The suite runs fully offline. A socket guard in `tests/conftest.py` fails any test
that opens an outbound connection, so a passing run provably spent no API quota.

Useful variants:

```powershell
..\.venv\Scripts\python.exe -m pytest -v                        # verbose
..\.venv\Scripts\python.exe -m pytest tests\test_agents.py      # one file
..\.venv\Scripts\python.exe -m pytest -k "revenue"              # by name
```

---

## 3. Run the backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8080
```

| URL | What it shows |
|---|---|
| http://localhost:8080/health | every subsystem, and what is degraded |
| http://localhost:8080/docs | interactive OpenAPI browser |

**Read `/health` first.** The `grounding` block tells you what the next run will
actually do:

```json
"grounding": {
  "competitor_source": "openstreetmap",
  "market_research_source": "serper",
  "rq3_arm": "grounded"
}
```

### A Windows gotcha

If a previous PowerShell session exported `GEMINI_MODEL` or similar, that stale
variable overrides `.env` (non-empty environment variables legitimately win). Clear
them in a fresh shell if config looks wrong:

```powershell
foreach ($n in @("GEMINI_MODEL","GROQ_API_KEY","GEMINI_API_KEY","SERPER_API_KEY",
                 "GOOGLE_PLACES_API_KEY","OLLAMA_MODEL","GENERATION_TIMEOUT_SECONDS")) {
  Remove-Item "env:$n" -ErrorAction SilentlyContinue
}
```

*Empty* environment variables are already handled — `config.py` ignores them.

---

## 4. Run the frontend

In a second terminal:

```powershell
cd frontend
npm install          # first time only
npm run dev
```

Open http://localhost:5173

The UI expects the backend on port 8080. Override with
`VITE_API_BASE_URL=http://localhost:9000 npm run dev`.

```powershell
npm run build        # production bundle -> dist/  (~162 kB, ~0.5 s)
```

---

## 5. Generate a plan

### From the UI
Type a prompt, press Enter. Watch the department progress stream, then read the
report and download PDF or JSON.

### From the API

```powershell
# classify only - shows routing without spending a full run
curl -X POST localhost:8080/intent -H "Content-Type: application/json" `
  -d '{\"prompt\": \"Ice cream shop in Andheri West, Rs 15L budget\"}'

# full generation
curl -X POST localhost:8080/generate -H "Content-Type: application/json" `
  -d '{\"prompt\": \"Ice cream shop in Andheri West, Rs 15L budget\"}'
```

### All endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | subsystem status |
| POST | `/intent` | classify a prompt, show the execution plan |
| POST | `/generate` | run the full pipeline |
| WS | `/ws/generate` | run with live progress events |
| GET | `/sections` | the 19-section catalogue |
| GET | `/sessions` | run history |
| GET | `/sessions/{id}` | one stored run |
| DELETE | `/sessions/{id}` | delete a run |
| GET | `/sessions/{id}/package` | full JSON package |
| GET | `/sessions/{id}/sections/{key}` | one section only |
| GET | `/sessions/{id}/report` | HTML report |
| GET | `/sessions/{id}/report.pdf` | PDF download |

### Expected timings

| Configuration | Wall time |
|---|---|
| Groq + Gemini | 9–40 s |
| Ollama only (no keys) | ~120 s |

Groq's free tier rate-limits under burst, so 1–3 of the 21 agents sometimes fall
through to the local model. That is the fallback chain working, and it is why the
range is wide.

---

## 6. Ollama (local fallback)

Already set up. To verify:

```powershell
ollama list                      # expect llama3.2:3b
```

To use the larger model named in the original spec (~4.7 GB, needs ~6 GB free RAM):

```powershell
ollama pull llama3.1:8b
# then set OLLAMA_MODEL=llama3.1:8b in .env
```

**If running keyless, raise the timeout.** Local CPU inference for 21 agents takes
~120 s against a 120 s default:

```
GENERATION_TIMEOUT_SECONDS=600
```

Already set in `.env`.

---

## 7. Caching (no Docker needed)

ChromaDB runs in local file mode by default — no server, no container:

```
ENABLE_CHROMA_CACHE=true
CHROMA_MODE=local
CHROMA_PATH=./data/chroma
```

Confirm via `/health` → `knowledge_cache.enabled: true`.

**Turn this on before any evaluation sweep.** Without it each arm re-issues the same
search queries — four times the credit spend, and results that could drift between
arms, which would invalidate the comparison.

`CHROMA_MODE=server` targets the docker-compose service instead, if you ever install
Docker.

---

## 8. Evaluation

The `evaluation` package sits outside `backend/`, so it needs `PYTHONPATH`:

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
```

```powershell
# smoke test - 2 arms, 5 prompts, a few minutes
..\.venv\Scripts\python.exe -m evaluation.harness --arms multi_agent baseline --limit 5 --label smoke

# variance measurement - same prompt repeated
..\.venv\Scripts\python.exe -m evaluation.harness --arms multi_agent baseline --prompts p01 --repeat 5 --label variance

# full sweep - 4 arms, 35 prompts, ~90 minutes
..\.venv\Scripts\python.exe -m evaluation.harness --all --label paper-run-1

# build the tables
..\.venv\Scripts\python.exe -m evaluation.report --label paper-run-1
```

Output lands in `evaluation/results/`:

| File | Contents |
|---|---|
| `<label>-metrics.csv` | one row per (prompt, arm, metric) |
| `<label>-summary.csv` | one row per (arm, metric) with n, mean, sd |
| `<label>-report.md` | RQ1/RQ2/RQ3 tables, ready to paste |

Results are written to SQLite after every prompt, so an interrupted sweep keeps what
it measured. Use a fresh `--label` for a clean run.

---

## 9. Docker (optional, not installed here)

```bash
cp .env.example .env
docker compose up --build
docker compose exec ollama ollama pull llama3.1:8b
```

| Service | Port |
|---|---|
| backend | 8080 |
| frontend | 5173 |
| ollama | 11434 |
| chromadb | 8000 |

The Docker image additionally installs WeasyPrint, which produces better PDFs than
the pure-Python fallback used locally.

---

## 10. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `/health` shows a key missing that is in `.env` | stale non-empty shell variable — see §3 |
| Generation times out | keyless run on local CPU; set `GENERATION_TIMEOUT_SECONDS=600` |
| `/report.pdf` returns 503 | no PDF backend; `pip install xhtml2pdf==0.2.16` |
| `knowledge_cache.enabled: false` | set `CHROMA_MODE=local`; check `./data/chroma` is writable |
| `ModuleNotFoundError: evaluation` | set `PYTHONPATH` — see §8 |
| Frontend shows "Cannot reach the backend" | backend not running, or wrong `VITE_API_BASE_URL` |
| Overpass returns 429 | public endpoint throttles on rapid queries; enable the cache |
| Baseline run fails | Gemini free-tier rate limit; it is pinned to one provider by design |
| Tests fail with `NetworkAccessAttempted` | a test tried a real network call; mock it with respx |

---

## 11. Security note

The backend has **no authentication**. It is built to run on localhost for a
research project. Add auth before exposing port 8080 to any network.
