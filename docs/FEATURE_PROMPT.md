# AI IDE Feature Prompt Template

Copy-paste template for asking any AI IDE (Kiro, Cursor, Copilot, Windsurf) to
implement or expand a MABGP feature. Fill the `<<< >>>` placeholders and delete
the sections that do not apply.

---

## TEMPLATE — Implement a New Feature

```
CONTEXT
I am building MABGP (Multi-Agent Autonomous Business Generation Platform), my
final-year B.E. Computer Engineering major project (2027 batch, Mumbai University).
Read docs/PROJECT_SPEC.md for the full architecture and feature list before starting.

WHAT THE SYSTEM DOES
User types one prompt ("Ice cream shop in Andheri, ₹15L budget") → 20+ specialized
AI agents across 5 departments (Strategy, Finance, Branding, Marketing, Operations)
autonomously produce a complete structured business package in 60–90 seconds.

LOCKED TECH STACK — DO NOT SUGGEST ALTERNATIVES
- Orchestration : LangGraph 0.2.x        (NOT CrewAI, NOT AutoGen)
- LLM           : Groq API (Llama 3.1 8B/70B) → Google Gemini 1.5 Flash → Ollama local
                  (NOT OpenAI, NOT Anthropic — free tiers only)
- Backend       : FastAPI 0.115.x + Uvicorn (Python 3.11+)
- Database      : SQLite                 (NOT PostgreSQL, NOT MySQL)
- Vector DB     : ChromaDB 0.5.x         (NOT Pinecone, NOT Weaviate)
- External APIs : Google Maps Places API v1, Serper.dev v1
- Frontend      : React 18 + Vite 5
- Deployment    : Docker Compose 2.x     (NOT Kubernetes)

HARD CONSTRAINTS
1. 100% free — flag immediately if anything costs money or exceeds a free tier
2. Complete runnable code only — never pseudocode, never "// implement this"
3. Exact library versions, exact API endpoints, exact field names
4. All state changes go through SharedBusinessState (append-only, never overwrite
   another department's section)
5. Every LLM call must route through the provider abstraction in app/llm/, never
   call an SDK directly from an agent
6. Type-hint everything; validate all LLM JSON output with Pydantic
7. Target hardware: local laptop, 8 GB RAM

FEATURE TO IMPLEMENT
Feature ID   : <<< F19 >>>
Feature Name : <<< Competitive Analysis Agent >>>
Category     : <<< E — Strategy Department >>>
Spec         : <<< paste the bullet list from PROJECT_SPEC.md >>>

DELIVERABLES
1. All new/modified files with full contents and correct paths
2. Pydantic schema for the feature's slice of SharedBusinessState
3. Wiring into the existing LangGraph department sub-graph
4. Unit test in backend/tests/ that runs without live API keys (mock external calls)
5. Any new dependencies added to backend/requirements.txt with pinned versions
6. Any new env vars added to .env.example

RESEARCH PAPER TIE-IN
State which research question this feature serves and which evaluation metric it
feeds. If it serves none, say so explicitly.
- RQ1: multi-agent vs single-LLM quality
- RQ2: dynamic routing efficiency
- RQ3: real-world data grounding vs text-only
- Metrics: Financial Accuracy (MAPE) · Competitor Coverage Rate ·
           Plan Completeness Score · Consistency Score

ACCEPTANCE CHECK
Before you finish:
- [ ] Code imports cleanly (no missing modules)
- [ ] Nothing in the change costs money
- [ ] Feature works when the primary LLM provider is rate-limited (fallback path tested)
- [ ] Feature degrades gracefully if its external API is unavailable
- [ ] docs/PROJECT_SPEC.md status marker updated from [ ] to [x]
```

---

## TEMPLATE — Expand an Existing Feature

```
CONTEXT
MABGP project. Read docs/PROJECT_SPEC.md first.

EXISTING FEATURE
ID    : <<< F19 >>>
Name  : <<< Competitive Analysis Agent >>>
Files : <<< backend/app/agents/strategy/competitive.py >>>

EXPANSION REQUESTED
<<< Also scrape competitor menu items and price points from their Google Maps
    listing photos and reviews, and add a price-positioning band to the output >>>

RULES
- The base feature must keep working if this expansion fails or is disabled
- Add a config flag in app/config.py to toggle the expansion on/off
- Do not change the existing Pydantic field names — only add new optional fields
- Same locked tech stack, same free-only constraint
- Update the existing unit test rather than replacing it

DELIVERABLES
1. Modified files with full contents
2. New optional Pydantic fields (backwards compatible)
3. Config flag with default = off
4. Updated unit test covering both flag states
5. One-line note in docs/PROJECT_SPEC.md expansion backlog marking this done
```

---

## TEMPLATE — Fix or Debug

```
CONTEXT
MABGP project. Read docs/PROJECT_SPEC.md first.

PROBLEM
<<< describe the symptom >>>

ERROR OUTPUT
<<< paste full traceback / logs >>>

WHAT I ALREADY TRIED
<<< list attempts >>>

RULES
- Diagnose root cause before changing code; tell me the cause in one paragraph
- Fix the cause, not the symptom
- Do not swap out any locked-stack library as a "fix"
- Add a regression test that fails before the fix and passes after
```

---

## TEMPLATE — Evaluation / Research Work

```
CONTEXT
MABGP project. Read docs/PROJECT_SPEC.md, sections 1.8–1.9.

TASK
<<< e.g. Implement F54 Financial Accuracy Score (MAPE) >>>

REQUIREMENTS
- Metric must be fully quantitative and reproducible — no LLM-as-judge unless
  explicitly requested
- Must run over evaluation/prompts.json (30+ prompts) in a single command
- Must score BOTH the multi-agent output AND the single-LLM baseline on the
  identical rubric
- Results written to SQLite (F60) and exported to CSV for paper tables
- Include the exact benchmark source used for ground truth (cite the dataset/report)

DELIVERABLES
1. evaluation/<metric_name>.py — runnable script
2. CSV output schema documented in a docstring
3. A worked example computed by hand in comments so I can verify the math
4. Statement of which RQ the result answers and what direction of result would
   support vs refute the hypothesis
```

---

## QUICK ONE-LINERS

For small asks, prefix with this compact context header:

```
[MABGP project — read docs/PROJECT_SPEC.md. Stack locked: LangGraph, Groq/Gemini/Ollama,
FastAPI, SQLite, ChromaDB, React+Vite, Docker Compose. Free-tier only. Runnable code only,
no pseudocode. All LLM calls via app/llm/ abstraction. All state via SharedBusinessState.]

<<< your request >>>
```

---

## ANTI-PATTERNS TO REJECT

If the AI IDE produces any of these, reject and re-prompt:

| Anti-pattern | Why it fails |
|--------------|--------------|
| `# TODO: implement LLM call` | Rule: runnable code only |
| `pip install openai` | Not free-tier; stack is locked to Groq/Gemini/Ollama |
| `requirements.txt` with `langgraph>=0.2` | Versions must be pinned exactly |
| Agent calling `groq.Client()` directly | Must go through `app/llm/` provider chain |
| Agent writing to another department's state section | Violates append-only rule |
| Suggesting PostgreSQL / Pinecone / CrewAI / Kubernetes | Locked decisions |
| Unvalidated `json.loads(llm_response)` | Must validate with Pydantic |
| A metric that depends on human judgement | Paper requires quantitative metrics |
