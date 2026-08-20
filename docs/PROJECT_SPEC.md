# MABGP — Multi-Agent Autonomous Business Generation Platform

> Master project specification. Single source of truth for architecture, concepts, and feature scope.

---

## PART 1: GENERAL PROJECT STRUCTURE

### 1.1 Basic Information

| Field | Detail |
|-------|--------|
| **Project Title** | Multi-Agent Autonomous Business Generation Platform (MABGP) |
| **Degree** | B.E. Computer Engineering (Final Year, 2027 Batch) |
| **University** | Mumbai University |
| **Deliverables** | Working software system + Research paper with quantitative evaluation |
| **One-Line Summary** | User types one natural language prompt → 20+ specialized AI agents autonomously produce a complete structured business package in 60–90 seconds |
| **Cost Constraint** | 100% free tools and free API tiers only |
| **Hardware Target** | Local laptop, 8 GB RAM minimum, Docker Compose |

---

### 1.2 Problem Statement

Starting a new business requires expertise across multiple domains (strategy, finance,
branding, marketing, operations). Existing tools either:

- Provide generic templates with no personalization
- Require manual input across 10+ forms
- Cost ₹10,000–₹1,00,000+ for professional consulting

**MABGP solves this** by decomposing business plan generation into specialized autonomous
agents that collaborate through shared state — producing location-aware, budget-specific,
sector-appropriate plans from a single sentence.

---

### 1.3 Core Concepts

| Concept | Description |
|---------|-------------|
| **Multi-Agent System** | Multiple specialized AI agents, each with a narrow responsibility, collaborating on a complex task |
| **Autonomous Generation** | Agents operate without human-in-the-loop; user provides only the initial prompt |
| **Departmental Decomposition** | Business planning split into 5 departments mirroring real organizations |
| **Shared Business State** | A single structured data object all agents read from and append to — the source of truth |
| **Dynamic Routing** | Orchestrator activates only relevant departments per business type |
| **LLM Fallback Chain** | Groq → Gemini → Ollama ensures zero downtime and zero cost |
| **Grounded Generation** | Agents use real-world data (Google Places, Serper) instead of hallucinating facts |
| **Quantitative Evaluation** | Every paper claim backed by measurable metrics vs a baseline |

---

### 1.4 System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   USER INPUT                         │
│         "Ice cream shop in Andheri, ₹15L"           │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│              INTENT CLASSIFIER                       │
│   LLM call → structured JSON extraction             │
│   {business_type, location, sector, budget, scale}  │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│            BUSINESS ORCHESTRATOR                     │
│   Reads intent → routing rules →                    │
│   active_departments → execution DAG                │
└────┬────────┬────────┬────────┬────────┬────────────┘
     ▼        ▼        ▼        ▼        ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌─────────────┐
│STRATEGY││FINANCE ││BRANDING││MARKETNG││ OPERATIONS  │
│(always)││(always)││(always)││(always)││(conditional)│
│5 agents││4 agents││4 agents││4 agents││  4 agents   │
└────┬───┘└───┬────┘└───┬────┘└───┬────┘└─────┬───────┘
     └────────┴─────────┴─────────┴───────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│            SHARED BUSINESS STATE                     │
│   Single Pydantic TypedDict — all agents append     │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│              OUTPUT LAYER                            │
│   JSON package → Structured Report → PDF/HTML       │
└─────────────────────────────────────────────────────┘
```

---

### 1.5 Technology Stack

| Layer | Technology | Version | License / Cost |
|-------|-----------|---------|----------------|
| Orchestration | LangGraph | 0.2.x | MIT, free |
| LLM (Primary) | Groq API — Llama 3.1 8B / 70B | — | Free: 14,400 req/day |
| LLM (Secondary) | Google Gemini Flash (see model note) | — | Free tier |
| LLM (Fallback) | Ollama local — Llama 3.1 8B | 0.3.x | Free, no limits |
| Backend | FastAPI + Uvicorn | 0.115.x | MIT, free |
| Database | SQLite | built-in | Free |
| Vector DB | ChromaDB | 0.5.x | Apache 2.0, free |
| Maps API | Google Maps Places API | v1 | $200 free credit/month |
| Search API | Serper.dev | v1 | 2,500 free searches/month |
| Frontend | React 18 + Vite | 18.x / 5.x | MIT, free |
| Deployment | Docker Compose | 2.x | Free, local |

---

### 1.6 Data Flow

```
User Prompt
  → Intent JSON (structured extraction)
    → Orchestrator (routing decision)
      → Department sub-graphs (parallel where possible)
        → Each agent reads SharedState, calls LLM/API, appends result
          → Completed SharedState
            → Output formatter
              → Structured business report (JSON / HTML / PDF)
```

---

### 1.7 Execution Model

```
Stage 1: Strategy                              (sequential — others depend on it)
Stage 2: Finance + Branding + Marketing        (parallel)
Stage 3: Operations                            (conditional, needs Finance cost data)
```

---

### 1.8 Research Questions

| ID | Question |
|----|----------|
| **RQ1** | Does a multi-agent pipeline produce measurably better business plans than a single-LLM baseline? |
| **RQ2** | Does dynamic routing improve efficiency without degrading output quality? |
| **RQ3** | How does multi-modal input (location + competitor data) affect plan accuracy vs text-only? |

---

### 1.9 Evaluation Metrics

| Metric | Computation | Purpose |
|--------|-------------|---------|
| **Financial Accuracy (MAPE)** | Projected margins vs MSME industry benchmarks | RQ1, RQ3 |
| **Competitor Coverage Rate** | Real nearby businesses found ÷ manual count | RQ3 |
| **Plan Completeness Score** | Sections present and substantive ÷ expected sections | RQ1, RQ2 |
| **Consistency Score** | Alignment between Strategy TAM and Finance revenue | RQ1 |
| **Routing Efficiency** | Token & time savings with dynamic vs all-departments | RQ2 |

**Baseline:** same prompt → single Gemini Flash call → scored on the same rubric.
**Sample size:** 30+ diverse prompts across sectors, budgets, and locations.

---

### 1.10 Key Design Principles

1. **Zero-cost constraint** — every tool/API must have a sufficient free tier
2. **Append-only state** — agents never overwrite other departments' data
3. **Graceful degradation** — rate limits trigger silent provider fallback
4. **Reproducibility** — `docker compose up` runs the entire system
5. **Modularity** — each agent independently testable; departments pluggable
6. **Research-first** — every design decision maps to a measurable metric

---

### 1.11 Repository Structure

```
mabgp/
├── docker-compose.yml
├── .env.example
├── README.md
├── docs/
│   ├── PROJECT_SPEC.md          # this file
│   ├── FEATURE_PROMPT.md        # AI IDE prompt template
│   └── paper/
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── config.py            # env vars, settings
│   │   ├── models/              # Pydantic schemas + SharedBusinessState
│   │   ├── llm/                 # provider abstraction + fallback chain
│   │   ├── intent/              # intent classifier
│   │   ├── orchestrator/        # routing rules + LangGraph DAG
│   │   ├── agents/              # department sub-graphs
│   │   │   ├── strategy/
│   │   │   ├── finance/
│   │   │   ├── branding/
│   │   │   ├── marketing/
│   │   │   └── operations/
│   │   ├── apis/                # Google Places, Serper wrappers
│   │   ├── output/              # report generation
│   │   └── db/                  # SQLite + ChromaDB
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   └── src/
└── evaluation/
    ├── prompts.json             # 30+ test prompts
    ├── baseline.py              # single-LLM baseline
    ├── metrics.py               # 4 metric implementations
    └── results/
```

---

## PART 2: DETAILED FEATURE BREAKDOWN

> 65 features across 15 categories. Each feature is minimal, self-contained, and
> independently expandable. Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

### CATEGORY A — Input & Intent Processing

#### `[x]` F1 · Natural Language Prompt Input
- Accept a single free-form text prompt
- No forms, no dropdowns — one text field
- Support informal styles: `"bakery near Dadar, 10L budget"`
- Validation: 10–500 characters

#### `[x]` F2 · Intent Entity Extraction
- LLM-based extraction of structured fields from raw prompt
- Extract: `business_type`, `location`, `sector`, `scale`, `budget`
- Output validated JSON matching a Pydantic schema
- Missing fields → infer defaults or mark `"unspecified"`

#### `[x]` F3 · Location Parsing & Normalization
- Parse `"Andheri"`, `"near Bandra station"`, `"South Mumbai"`
- Normalize to `{area, city, state, country}`
- Handle colloquial/abbreviated names
- Default: `Mumbai, Maharashtra, India`

#### `[x]` F4 · Budget Parsing & Normalization
- Parse `"₹15L"`, `"15 lakhs"`, `"1.5 crore"`, `"50000"`
- Normalize to `{amount: int, currency: "INR"}`
- Infer scale: micro `<₹10L` · small `₹10L–50L` · medium `₹50L–2Cr` · large `>₹2Cr`

#### `[x]` F5 · Business Type Classification
- Classify into predefined sector taxonomy
- Derive `is_physical` and `requires_operations` flags
- Sectors: `food_and_beverage`, `retail`, `services`, `technology`, `education`, `healthcare`, `manufacturing`, `creative`

---

### CATEGORY B — LLM Provider Management

#### `[x]` F6 · Groq API Integration
- Connect to Groq free tier
- Llama 3.1 8B (fast/creative) and 70B (reasoning)
- Track 14,400 req/day rate limit
- Return responses with token usage metadata

#### `[x]` F7 · Google Gemini API Integration
- Gemini Flash free tier (model configurable via GEMINI_MODEL)
- Handle per-minute rate limit with request queuing
- Preferred for structured JSON extraction
- Track 1M tokens/day usage

#### `[x]` F8 · Ollama Local Fallback
- Llama 3.1 8B locally via Ollama container
- Zero rate limits, zero cost
- Auto-detect availability on startup
- Guarantees system never fails on API limits

#### `[x]` F9 · LLM Fallback Chain Logic
- Groq → Gemini → Ollama with exponential backoff
- Log serving provider per request (cost/latency analysis for paper)
- Transparent to callers — one interface for all providers

---

### CATEGORY C — Business Orchestrator

#### `[x]` F10 · Routing Rules Engine
- Read intent JSON → determine active departments
- Strategy, Finance, Branding, Marketing = always active
- Operations = active if `is_physical` or `requires_operations`
- Expandable to per-agent activation rules

#### `[x]` F11 · Execution DAG Construction
- Build a directed acyclic graph of execution order
- Strategy first (produces TAM + competitors)
- Finance ∥ Branding ∥ Marketing after Strategy
- Operations after Finance (needs cost data)

#### `[x]` F12 · Parallel Execution Manager
- Concurrent department execution via LangGraph parallel branches
- Track per-department completion status
- Barrier before output layer
- Emit progress events for frontend WebSocket

#### `[x]` F13 · Session & State Initialization
- Create session ID per request
- Initialize SharedBusinessState with intent pre-filled
- Persist session metadata to SQLite
- Hard timeout: 120 seconds per generation

---

### CATEGORY D — Shared Business State

#### `[x]` F14 · State Schema Definition
- Pydantic TypedDict with one section per department
- Fields: `intent`, `strategy`, `finance`, `branding`, `marketing`, `operations`, `metadata`
- All department sections Optional
- Strict typing blocks invalid agent writes

#### `[x]` F15 · Append-Only State Updates
- Agents append only to their own department section
- No cross-department overwrite or delete
- State flows through LangGraph state channels
- Enables Consistency Score computation

#### `[x]` F16 · State Validation & Completeness Check
- Post-run validation of expected field population
- Compute Plan Completeness Score
- Flag contradictions (budget exceeded, impossible margins)
- Store validated state as output source of truth

---

### CATEGORY E — Strategy Department

#### `[x]` F17 · Business Planning Agent
- Executive summary, vision, mission
- TAM / SAM / SOM with reasoning
- Business model type (B2C, B2B, marketplace, subscription)
- Output: 1-page business model canvas

#### `[x]` F18 · Risk Analysis Agent
- Top 5–10 risks specific to business type and location
- Categories: financial, operational, regulatory, market, competitive
- Severity (high/medium/low) × likelihood
- One mitigation strategy per risk

#### `[x]` F19 · Competitive Analysis Agent
- Google Places API → real nearby competitors
- Extract: name, rating, review count, price level, distance
- Identify market gaps
- Output: competitor table + positioning recommendation

#### `[x]` F20 · Market Research Agent
- Serper.dev → market size, trends, news
- Industry growth rates, consumer preferences, regulatory changes
- Scoped to specific location + sector
- Output: market overview + key statistics

#### `[x]` F21 · Location Intelligence Agent
- Foot traffic potential by location type
- Nearby complementary businesses (partnership candidates)
- Accessibility: metro, highways, parking
- Output: location score 1–10 with justification

---

### CATEGORY F — Finance Department

#### `[x]` F22 · Revenue Model Agent
- Primary and secondary revenue streams
- Pricing strategy informed by competitor data
- Monthly revenue projections for Years 1–3
- Seasonality adjustment where applicable

#### `[x]` F23 · Cost Structure Agent
- One-time setup costs (deposit, equipment, registration)
- Monthly recurring (rent, salaries, utilities, marketing)
- Enforce total setup cost ≤ stated budget
- Output: categorized cost breakdown table

#### `[x]` F24 · Funding Strategy Agent
- Recommend approach by budget and scale
- Options: bootstrapped, angel, MSME bank loan, grants
- Reference Indian schemes (Mudra Loan, Startup India)
- Output: funding recommendation with amounts + timeline

#### `[x]` F25 · P&L Forecast Agent
- 3-year P&L (monthly Y1, quarterly Y2–Y3)
- Gross margin, net margin, break-even month
- Compare margins against MSME benchmarks
- Output: P&L table + break-even analysis

---

### CATEGORY G — Branding Department

#### `[x]` F26 · Brand Naming Agent
- Generate 5–10 name candidates
- Avoid direct competitor collisions
- Rationale per name (meaning, pronunciation, memorability)
- Recommend top 3

#### `[x]` F27 · Brand Identity Agent
- Brand personality traits
- Color palette (primary/secondary/accent hex codes)
- Typography pairing (heading + body)
- Output: brand identity brief

#### `[x]` F28 · Brand Voice Agent
- Communication tone definition
- 3–5 sample taglines
- Sample social post in brand voice
- Output: voice guidelines

#### `[x]` F29 · Visual Design Direction Agent
- Logo style (wordmark, lettermark, icon, combination)
- Packaging/signage aesthetic for physical businesses
- Visual mood (minimalist, vibrant, rustic, tech-forward)
- Output: visual direction brief

---

### CATEGORY H — Marketing Department

#### `[x]` F30 · Digital Marketing Plan Agent
- Channel mix (Instagram, Google Ads, WhatsApp, YouTube)
- Budget % allocation per channel
- KPIs per channel
- Output: channel strategy table

#### `[x]` F31 · Buyer Persona Agent
- 2–3 detailed personas
- Demographics: age, gender, income, location, occupation
- Psychographics: values, pain points, triggers, objections
- Output: persona cards

#### `[x]` F32 · Campaign Plan Agent
- 90-day launch campaign timeline
- Phases: pre-launch, launch, post-launch
- Concrete campaign ideas per phase
- Output: campaign calendar with milestones

#### `[x]` F33 · SEO & Content Strategy Agent
- 10–15 target keywords
- Content topics for organic traffic
- Frequency + formats (blog, video, reels)
- Output: content calendar skeleton + keyword list

---

### CATEGORY I — Operations Department *(conditional)*

#### `[x]` F34 · Supply Chain Agent
- Raw material / inventory requirements
- Vendor categories (local, wholesale, online)
- Inventory approach (JIT, safety stock)
- Output: supply chain overview

#### `[x]` F35 · Staffing Plan Agent
- Roles and headcount for Year 1
- Salary ranges at Mumbai market rates
- Hiring sequence and timeline
- Output: org chart + hiring plan

#### `[x]` F36 · Technology Stack Recommendation Agent
- POS, accounting, communication tools
- Delivery/logistics integrations if applicable
- All recommendations free or low-cost
- Output: tech stack table

#### `[x]` F37 · Process Flow Agent
- Daily operational workflow (open → close)
- Key processes: fulfillment, service, quality check
- Inter-process dependencies
- Output: process flow description

---

### CATEGORY J — External Data & Grounding

#### `[x]` F38 · Google Places API — Competitor Discovery
- Search businesses by type within radius of location
- Extract name, address, rating, review count, price level
- Filter and rank by relevance
- Cache in ChromaDB to avoid repeat calls

#### `[x]` F39 · Serper.dev — Market Intelligence Search
- Search industry reports, news, government data
- Extract relevant snippets and statistics
- Summarize into structured market data
- Rate-limit aware (2,500/month budget)

#### `[x]` F40 · ChromaDB — Knowledge Caching
- Store generated plans as embeddings
- Retrieve similar past outputs for consistency
- Cache market research to avoid redundant API calls
- Collections: `plans`, `market_research`, `competitors`

#### `[x]` F41 · Data Freshness & Validity Tagging
- Tag external data with retrieval timestamp
- Mark >30 days old as potentially stale
- Prefer fresh data in agent prompts
- Include freshness in output metadata

---

### CATEGORY K — Output & Report Generation

#### `[x]` F42 · JSON Business Package Assembly
- Collect all department outputs from SharedBusinessState
- Structure into unified JSON document
- Metadata: generation time, agents used, providers used
- Validate completeness before formatting

#### `[x]` F43 · Structured Report Formatting (HTML)
- Convert JSON package into formatted HTML
- Sections: Exec Summary, Market, Financial, Brand, Marketing, Operations
- Tables, bullets, consistent headers
- Responsive layout

#### `[x]` F44 · PDF Export
- HTML → downloadable PDF
- Cover page with business name, date, brand colors
- Page numbers + table of contents
- Print-friendly

#### `[x]` F45 · Section-Level Access
- Request individual sections independently
- Partial re-generation (regenerate marketing only)
- Each section independently renderable

#### `[x]` F46 · Generation Metadata & Transparency
- Which model generated each section
- Which APIs were called and what was retrieved
- Total generation time and token usage
- Supports paper reproducibility

---

### CATEGORY L — Frontend & UX

#### `[x]` F47 · Single-Prompt Input Interface
- Minimal UI, one large text input
- Example placeholders
- Character counter
- Generate button with loading state

#### `[x]` F48 · Real-Time Agent Progress Display
- WebSocket live agent activity
- Active department + active agent
- Step indicator (`3/5 departments complete`)
- Estimated time remaining

#### `[x]` F49 · Report Viewer with Department Tabs
- Tabs: Strategy · Finance · Branding · Marketing · Operations
- Collapsible sections per tab
- Highlight key metrics (break-even, TAM, budget utilization)

#### `[x]` F50 · Report Download
- Download PDF
- Download raw JSON
- Copy section to clipboard

#### `[x]` F51 · History & Session Management
- List past generations with prompt preview
- Re-open any past report
- Delete sessions
- Backed by SQLite

#### `[x]` F52 · Error & Fallback UI
- Graceful mid-generation failure display
- Show partial results from completed departments
- Retry failed sections
- WebSocket connection status indicator

---

### CATEGORY M — Evaluation & Benchmarking

#### `[x]` F53 · Single-LLM Baseline Generator
- Same prompts → single Gemini Flash call → full plan
- Identical output format for fair comparison
- Stored alongside multi-agent outputs
- Control group for all metrics

#### `[x]` F54 · Financial Accuracy Score (MAPE)
- Projected margins vs MSME benchmarks (RBI/NKB data)
- MAPE per plan, averaged over 30+ prompts
- Report multi-agent MAPE vs baseline MAPE

#### `[x]` F55 · Competitor Coverage Rate
- Manual ground-truth competitor count per test location
- `found ÷ actual` coverage ratio
- Compare: multi-agent+API vs multi-agent−API vs baseline (RQ3)

#### `[x]` F56 · Plan Completeness Score
- Checklist of 20+ expected sections
- `substantive sections ÷ expected sections × 100`
- "Substantive" = >1 sentence and contains specific data
- Compare multi-agent vs baseline

#### `[x]` F57 · Consistency Score
- Strategy TAM ↔ Finance revenue cross-check
- Marketing budget ↔ Finance cost structure
- Staffing plan ↔ budget constraints
- `% of cross-references logically consistent`

#### `[x]` F58 · Dynamic Routing Efficiency Metric (RQ2)
- Tokens: all-5-departments vs dynamic routing
- Time: both approaches
- Quality delta must be ≈ 0
- Report token savings %, time savings %, quality delta

---

### CATEGORY N — Database & Persistence

#### `[x]` F59 · SQLite Session Storage
- Store `id`, `prompt`, `intent_json`, `status`, timestamps
- Store final business plan JSON
- Store generation metadata (models, APIs, token counts)
- Queries for history and analytics

#### `[x]` F60 · SQLite Evaluation Results Storage
- Metric scores per prompt per approach
- Aggregation queries (avg MAPE, avg completeness)
- CSV export for paper figures and tables

#### `[x]` F61 · ChromaDB Embedding Storage
- Plan embeddings for semantic similarity
- Market research snippets for reuse
- Competitor data cached by location

---

### CATEGORY O — Infrastructure & Deployment

#### `[x]` F62 · Docker Compose Multi-Service Setup
- Services: `backend`, `frontend`, `ollama`, `chromadb`
- Shared network, persistent volumes
- Single `docker compose up`
- API keys via environment variables

#### `[x]` F63 · Environment Configuration
- `.env` for all secrets
- `config.py` with defaults, validation, fallbacks
- Separate dev vs evaluation configs

#### `[x]` F64 · Health Check & Monitoring
- `/health` endpoint: LLMs reachable, DB connected, APIs available
- Log every LLM call: latency, tokens, provider
- Log every API call: response time
- Structured JSON logging

#### `[x]` F65 · Reproducibility Package
- `README.md` with exact setup steps
- Pinned dependency versions (no floating ranges)
- `.env.example`
- `evaluation/prompts.json` for paper reproduction

---

## FEATURE SUMMARY

| Category | Features | Count |
|----------|----------|-------|
| A. Input & Intent Processing | F1–F5 | 5 |
| B. LLM Provider Management | F6–F9 | 4 |
| C. Business Orchestrator | F10–F13 | 4 |
| D. Shared Business State | F14–F16 | 3 |
| E. Strategy Department | F17–F21 | 5 |
| F. Finance Department | F22–F25 | 4 |
| G. Branding Department | F26–F29 | 4 |
| H. Marketing Department | F30–F33 | 4 |
| I. Operations Department | F34–F37 | 4 |
| J. External Data & Grounding | F38–F41 | 4 |
| K. Output & Report Generation | F42–F46 | 5 |
| L. Frontend & UX | F47–F52 | 6 |
| M. Evaluation & Benchmarking | F53–F58 | 6 |
| N. Database & Persistence | F59–F61 | 3 |
| O. Infrastructure & Deployment | F62–F65 | 4 |
| **TOTAL** | | **65** |

---

## EXPANSION BACKLOG

Every feature above is intentionally minimal. Candidate expansions, each a separate
increment that the base feature works without:

| Base | Expansion |
|------|-----------|
| F1 | Image input — storefront photos, floor plans (multi-modal, RQ3) |
| F19 | Deeper competitive scraping — menus, pricing, social followers |
| F25 | Scenario modeling — best / base / worst case P&L |
| F30 | A/B testing plans — auto-generate ad variations |
| F44 | Investor pitch deck PDF generation |
| F48 | Agent chat — follow-up questions to specific agents |
| F49 | Interactive charts — revenue curves, cost pie charts |
| F51 | Plan versioning and diffing |
| F57 | LLM-as-judge qualitative scoring alongside quantitative |

---

## IMPLEMENTATION PHASES

| Phase | Scope | Features | Week |
|-------|-------|----------|------|
| 1 | Foundation & Architecture | F62, F63, F65 | 1 |
| 2 | Core Infrastructure | F6–F9, F14–F16, F59, F64 | 2 |
| 3 | Intent Classification | F1–F5 | 3 |
| 4 | Business Orchestrator | F10–F13 | 4 |
| 5 | Department Agents | F17–F37 | 5–7 |
| 6 | External API Integration | F38–F41 | 6 |
| 7 | Output Layer | F42–F46 | 8 |
| 8 | React Frontend | F47–F52 | 8–9 |
| 9 | Evaluation & Benchmarking | F53–F58, F60 | 9–10 |
| 10 | Research Paper | — | 10–11 |
