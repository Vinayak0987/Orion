# Orion — Input, Processing & Output Specification

**Project:** Orion (AI Business Operating System)
**Team:** Aditya Maskare (102), Vinayak Maurya (103), Abhishek Mishra (108)
**Division B, B.E. Computer Engineering, University of Mumbai**

---

## 1. INPUT — What the User Provides

### 1.1 User's Perspective (User ko kya dena hai?)

The user provides **exactly one thing**: a single sentence describing their business idea.

```
"Ice cream shop in Andheri West, budget ₹15 lakh"
```

That's it. No forms. No dropdowns. No multi-page questionnaires. One text field, one sentence.

### 1.2 What the System Extracts from That Sentence

The system's intent classifier reads the sentence and extracts:

| Field | Example | How it's used |
|-------|---------|---------------|
| **Business Type** | Ice cream shop | Determines which agents run and what they produce |
| **Location** | Andheri West, Mumbai | Finds real competitors, local market data, rental costs |
| **Budget** | ₹15,00,000 | Sets financial constraints for all departments |
| **Sector** | Food & Beverage | Loads sector benchmarks for margin validation |
| **Scale** | Small (₹10L–50L) | Adjusts staffing, operations complexity |
| **Is Physical?** | Yes | Decides if Operations department runs |

### 1.3 Input Requirements & Validation

| Requirement | Detail |
|-------------|--------|
| **Length** | 10–1000 characters |
| **Language** | English (supports Hindi-English mix: "chai tapri near Dadar") |
| **Format** | Free-form natural language — no structure required |
| **Required info** | Business type (mandatory); location, budget, scale (optional — system infers defaults) |
| **Defaults if missing** | Location → Mumbai, Maharashtra; Budget → unspecified; Scale → inferred from budget |

### 1.4 Example Inputs (Range of Complexity)

| # | User Input | What's extracted |
|---|-----------|-----------------|
| 1 | "bakery" | type=bakery, location=Mumbai (default), budget=unspecified |
| 2 | "dental clinic near Bandra, 50L" | type=dental_clinic, location=Bandra Mumbai, budget=₹50L, sector=healthcare |
| 3 | "SaaS platform for logistics companies, ₹2 crore funding" | type=saas_platform, location=n/a (digital), budget=₹2Cr, sector=technology, is_physical=false |
| 4 | "premium salon in South Mumbai targeting working women, budget around 25 lakh" | type=salon, location=South Mumbai, budget=₹25L, sector=services, scale=small |

### 1.5 What the User Does NOT Need to Provide

- ❌ Market research data
- ❌ Financial projections
- ❌ Competitor names
- ❌ Branding preferences
- ❌ Marketing channel knowledge
- ❌ Operations expertise
- ❌ Any form fields or structured input

The system produces ALL of the above autonomously from the one sentence.

---


## 2. PROCESSING — What Happens Inside (Detail)

### 2.1 Processing Pipeline Overview

```
USER INPUT (1 sentence)
    │
    ▼
┌──────────────────────────────────────────────┐
│  STAGE 1: Intent Classification              │
│  LLM extracts structured JSON from the text  │
│  Time: ~2 seconds                            │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  STAGE 2: Routing & DAG Construction         │
│  Decides which departments run, in what order│
│  Time: <100ms (rule-based, no LLM)           │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  STAGE 3: Department Execution (21 agents)   │
│  Strategy → (Finance ∥ Branding ∥ Marketing) │
│          → Operations (if physical)          │
│  Time: 40–70 seconds                         │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  STAGE 4: Output Assembly                    │
│  JSON → HTML Report → PDF                    │
│  Time: ~3 seconds                            │
└──────────────────────────────────────────────┘

Total: 60–90 seconds from prompt to complete plan.
```

### 2.2 Stage 1: Intent Classification (Detailed)

**What happens:** An LLM (Groq Llama 3.1 → Gemini → Ollama fallback) reads the user's sentence and outputs a structured JSON object.

**Example:**
```
Input:  "Ice cream shop in Andheri West, budget ₹15 lakh"

Output JSON:
{
  "business_type": "ice_cream_shop",
  "business_type_label": "Ice Cream Shop",
  "sector": "food_and_beverage",
  "location": {"area": "Andheri West", "city": "Mumbai"},
  "budget": {"amount": 1500000, "currency": "INR", "display": "₹15 lakh"},
  "scale": "small",
  "is_physical": true,
  "requires_operations": true
}
```

**Validation:** Every field is validated against a Pydantic schema. Invalid LLM output is rejected and retried.

### 2.3 Stage 2: Routing Decision

Based on the intent, the orchestrator decides:

| Condition | Result |
|-----------|--------|
| All prompts | Strategy + Finance + Branding + Marketing run |
| `is_physical = true` | Operations department also runs |
| `is_physical = false` (SaaS, app, etc.) | Operations skipped → 17.3% token saving |

**Execution order (DAG):**
```
        ┌─── Finance ───┐
Strategy┤               ├── Operations (if physical)
        ├─── Branding ──┤
        └─── Marketing ─┘
```

Strategy runs first because Finance needs market size, Branding needs positioning, and Marketing needs the target customer profile.

### 2.4 Stage 3: Department Execution — The 21 Agents

Each department is a sub-graph of specialized agents. Every agent:
1. Reads the shared state (what previous agents produced)
2. Calls an LLM with a domain-specific prompt
3. Validates the response against a Pydantic schema
4. Appends its output to the shared state

#### Strategy Department (5 agents)
| Agent | What it produces |
|-------|-----------------|
| Market Sizing | TAM, SAM, SOM in ₹ for the specific location + sector |
| Competitor Analysis | Real nearby businesses (from Google Places / OSM), their ratings, price level |
| Positioning | Unique selling proposition, differentiation strategy |
| SWOT Analysis | Strengths, Weaknesses, Opportunities, Threats |
| Competitive Advantage | What makes this business defensible |

#### Finance Department (4 agents)
| Agent | What it produces |
|-------|-----------------|
| Cost Structure | Setup costs, monthly costs, category-wise breakdown |
| Revenue Model | Revenue streams, pricing, unit economics |
| P&L Forecast | 20-period profit & loss projection with margins |
| Funding & Break-even | How long to break even, funding allocation |

#### Branding Department (4 agents)
| Agent | What it produces |
|-------|-----------------|
| Brand Identity | Name suggestions, tagline, brand values, personality |
| Brand Voice | Tone, vocabulary, communication style guidelines |
| Visual Direction | Logo style, colour palette, aesthetic mood |
| Brand Story | Origin narrative, customer-facing "why we exist" |

#### Marketing Department (4 agents)
| Agent | What it produces |
|-------|-----------------|
| Digital Marketing Plan | Channel mix, budget allocation, KPIs |
| Buyer Personas | 2–3 detailed customer profiles (demographics + psychographics) |
| Campaign Plan | 90-day launch timeline with phases and milestones |
| SEO & Content Strategy | Keywords, content topics, publishing calendar |

#### Operations Department (4 agents, runs only for physical businesses)
| Agent | What it produces |
|-------|-----------------|
| Supply Chain | Vendors, inventory approach, raw material needs |
| Staffing Plan | Roles, headcount, salary ranges at Mumbai market rates |
| Technology Stack | POS, accounting, delivery tools — all free/low-cost |
| Process Flow | Daily workflow from open to close |

### 2.5 External Data Grounding (Real-World APIs)

The agents don't just hallucinate — they fetch real data:

| API | What it provides | Example |
|-----|-----------------|---------|
| **Google Places / OpenStreetMap** | Real competitors within 2 km of the location | "Naturals Ice Cream (4.3★), Baskin Robbins (4.1★)" |
| **Serper.dev** | Market research, industry reports, government data | "MSME sector grew 12% in FY24" |
| **ChromaDB Cache** | Previously retrieved data (avoids redundant API calls) | Cached competitor lists for repeat locations |

### 2.6 Quality Controls During Processing

| Control | What it prevents |
|---------|-----------------|
| **Pydantic validation** | Malformed LLM output — every response is schema-validated |
| **Cross-department reconciliation** | Revenue exceeding market size, payroll exceeding budget |
| **Provider fallback** | Groq rate limit → automatic switch to Gemini → Ollama |
| **Append-only state** | No agent can overwrite another department's data |
| **Budget ceiling enforcement** | Setup costs cannot exceed the user's stated budget |

---


## 3. OUTPUT — What the System Delivers

### 3.1 Output Formats

| Format | Purpose | How delivered |
|--------|---------|--------------|
| **Interactive Web Report** | Primary viewing experience | Displayed in the browser with department tabs, collapsible sections, KPI highlights |
| **PDF Document** | Formal document for printing, sharing, investor meetings | Download button → branded multi-page PDF with cover, TOC, page numbers |
| **JSON Package** | Raw structured data for programmatic access | Download or API endpoint — complete machine-readable business plan |
| **Per-Section API** | Individual sections for integration | REST endpoint per section (strategy, finance, etc.) |

### 3.2 What's in the Output (Complete Plan Structure)

```
COMPLETE BUSINESS PLAN
├── Executive Summary
│   ├── Business type and concept
│   ├── Target market
│   ├── Budget and scale
│   └── Key financial highlights
│
├── Strategy
│   ├── Market Sizing (TAM / SAM / SOM in ₹)
│   ├── Competitor Analysis (real businesses with ratings)
│   ├── SWOT Analysis
│   ├── Competitive Positioning
│   └── Strategic Advantage
│
├── Finance
│   ├── Setup Costs (category-wise breakdown)
│   ├── Monthly Operating Costs
│   ├── Revenue Model & Pricing
│   ├── 20-Period P&L Forecast
│   ├── Gross & Net Margins
│   └── Break-even Timeline
│
├── Branding
│   ├── Brand Name Suggestions
│   ├── Tagline & Values
│   ├── Voice & Tone Guidelines
│   ├── Colour Palette (with hex codes)
│   └── Visual Direction
│
├── Marketing
│   ├── Buyer Personas (2–3 detailed profiles)
│   ├── Channel Strategy (with budget %)
│   ├── 90-Day Campaign Calendar
│   ├── SEO Keywords (10–15)
│   └── Content Strategy
│
├── Operations (physical businesses only)
│   ├── Supply Chain Overview
│   ├── Staffing Plan & Org Chart
│   ├── Daily Process Flow
│   └── Technology Recommendations
│
└── Metadata (transparency)
    ├── Which AI model generated each section
    ├── Which APIs were called
    ├── Total generation time & token usage
    └── Data freshness timestamps
```

### 3.3 Output Example — Key Numbers for "Ice cream shop in Andheri, ₹15L"

| Section | Key Output |
|---------|-----------|
| Market Size | TAM: ₹240 Cr (Mumbai ice cream), SAM: ₹18 Cr (Western suburbs), SOM: ₹72 L (year 1) |
| Competitors Found | Naturals (4.3★, 200+ reviews), Apsara (4.1★), Baskin Robbins (4.0★) — from Google Places |
| Setup Cost | ₹14.2L (equipment ₹5L, interiors ₹4L, deposit ₹3L, inventory ₹1.2L, licenses ₹1L) |
| Monthly Cost | ₹3.8L (rent ₹1.2L, staff ₹1.5L, raw materials ₹80K, marketing ₹30K) |
| Break-even | Month 8 at 65% capacity utilization |
| Brand | "Frost & Co." — modern, Instagram-friendly, millennial-targeting |
| Marketing | Instagram 40%, Google Ads 25%, WhatsApp 20%, Events 15% |
| Staff | 6 people: 1 manager, 3 scoopers, 1 kitchen helper, 1 delivery |

### 3.4 Who is the Output For? (Target Users)

| User Type | What they get from it | How they use it |
|-----------|----------------------|-----------------|
| **First-time Entrepreneur** | A complete business blueprint they can act on today | Walk into a bank with the PDF, start vendor conversations, hire staff |
| **Student / Researcher** | A structured case study with real market data | Include in a business plan course assignment, compare across sectors |
| **Small Business Owner (pivoting)** | Market validation for a new idea | Compare their idea's margins against sector benchmarks before committing capital |
| **Freelancer / Consultant** | A first draft they can refine for clients | Save 20–40 hours of research per client engagement |
| **Investor / Mentor** | Quick viability assessment of a pitch | Spot unrealistic assumptions in a founder's projections |

### 3.5 What Makes This Output Different from ChatGPT / Generic Tools

| Aspect | Generic LLM | Orion |
|--------|-------------|-------|
| **Structure** | Prose paragraphs, no standard format | 26-field rubric, consistent across every run |
| **Numbers** | Made up, no source | Validated against MSME sector benchmarks, real competitor data |
| **Competitors** | Hallucinated names | Real businesses from Google Places / OpenStreetMap with ratings |
| **Financial model** | Single revenue estimate | 20-period P&L with margins, break-even, sensitivity |
| **Consistency** | Revenue may exceed market size | Cross-department reconciliation enforced in code |
| **Transparency** | "Here's your plan" (no provenance) | Every section shows which model, which APIs, which data |
| **Reproducibility** | Different output every time | Same prompt → same structure, quantitatively evaluated |

---


## 4. OUTPUT DEMO — What the Screen Looks Like

### 4.1 Generation Layer UI (`#/generate`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Orion          [Generate] [Business] [Work] [Activity] [Loops]     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Describe your business idea:                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Ice cream shop in Andheri West, budget ₹15 lakh              │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  [Generate Business Plan]              42/1000 characters            │
│                                                                     │
│  Examples: [bakery near Dadar] [SaaS for HR] [dental clinic Bandra] │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  ▌ GENERATING...  38s elapsed                                       │
│  ████████████████████░░░░░░░░  4/5 departments complete             │
│                                                                     │
│  ✓ Strategy     done (12s)                                          │
│  ✓ Finance      done (18s)                                          │
│  ✓ Branding     done (14s)                                          │
│  ● Marketing    running...                                          │
│  ○ Operations   waiting                                             │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  REPORT: Ice Cream Shop — Andheri West                              │
│                                                                     │
│  ┌────────┐┌────────┐┌────────┐┌────────┐                          │
│  │100%    ││₹14.2L  ││Month 8 ││₹72L    │                          │
│  │Complete││Setup   ││B/E     ││Year 1  │                          │
│  └────────┘└────────┘└────────┘└────────┘                          │
│                                                                     │
│  [Strategy] [Finance] [Branding] [Marketing] [Operations]           │
│  ─────────────────────────────────────────────────                  │
│  ▼ Market Sizing                                                    │
│    TAM: ₹240 Crore (Mumbai ice cream market)                        │
│    SAM: ₹18 Crore (Western suburbs, premium segment)                │
│    SOM: ₹72 Lakh (year 1, 3% market penetration)                    │
│                                                                     │
│  ▼ Competitor Analysis                                              │
│    ┌──────────────────┬────────┬─────────┬────────────┐             │
│    │ Business         │ Rating │ Reviews │ Source     │             │
│    ├──────────────────┼────────┼─────────┼────────────┤             │
│    │ Naturals Ice Crm │ 4.3★   │ 247     │ Google Maps│             │
│    │ Apsara Ice Cream │ 4.1★   │ 189     │ Google Maps│             │
│    │ Baskin Robbins   │ 4.0★   │ 312     │ Google Maps│             │
│    └──────────────────┴────────┴─────────┴────────────┘             │
│                                                                     │
│  [⬇ Download PDF]  [⬇ Download JSON]  [📋 Copy Section]            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Operating Layer UI — Business View (`#/business`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Orion          [Generate] [Business] [Work] [Activity] [Loops]     │
├─────────────────────────────────────────────────────────────────────┤
│  Business View                                                      │
│  How is the company doing? Every number is computed from the        │
│  ledger — no agent can write one.                                   │
│                                                                     │
│  Company: [demo-icecream-andheri      ] [Load] [⏩ Manual Tick]     │
│                                                                     │
│  ─── MONEY ─────────────────────────────────────────────────────    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │🔒 Revenue│ │🔒 COGS   │ │🔒 Opex   │ │🔒 Cash   │               │
│  │₹4,80,000 │ │₹1,92,000 │ │₹3,60,000 │ │₹9,28,000 │               │
│  │from 90   │ │from 90   │ │from 90   │ │from 180  │               │
│  │entries   │ │entries   │ │entries   │ │entries   │               │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
│                                                                     │
│  ─── MARGINS ───────────────────────────────────────────────────    │
│  ┌─────────────────┐ ┌─────────────────┐                           │
│  │🔒 Gross Margin  │ │🔒 Net Margin    │                           │
│  │    60.00%       │ │    +2.50%       │                           │
│  │  from 180 ent.  │ │  from 360 ent.  │                           │
│  └─────────────────┘ └─────────────────┘                           │
│                                                                     │
│  ─── TREND ─────────────────────────────────────────────────────    │
│  net_margin_pct (anchor 🔒) vs customers_acquired (proxy)           │
│  ╭──────────────────────────────────────────╮                       │
│  │  ___                     ....---         │ ── anchor             │
│  │ /   \___           ...---                │ -- proxy              │
│  │         \____....--                      │                       │
│  ╰──────────────────────────────────────────╯                       │
│  [Data table ▸]                                                     │
│                                                                     │
│  ─── FINDINGS ──────────────────────────────────────────────────    │
│  ┌──────────┬───────────────────┬────────────┬────────────────┐     │
│  │ CRITICAL │ proxy_divergence  │ marketing  │ net_margin -1.5│     │
│  │ HIGH     │ dept_conflict     │ mkt + ops  │ net_margin -1.5│     │
│  └──────────┴───────────────────┴────────────┴────────────────┘     │
│                                                                     │
│  ─── DEPARTMENTS ───────────────────────────────────────────────    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │
│  │ Strategy │ │ Finance  │ │ Branding │ │Marketing │ │Operations│  │
│  │keep pos. │ │protect   │ │brand     │ │acquire   │ │deliver   │  │
│  │matched   │ │margin    │ │recognise │ │customers │ │reliably  │  │
│  │          │ │          │ │          │ │who stay  │ │          │  │
│  │proxy:    │ │proxy:    │ │proxy:    │ │proxy:    │ │proxy:    │  │
│  │comp.set  │ │cost redn │ │assets    │ │acquired  │ │tasks     │  │
│  │🔒anchor: │ │🔒anchor: │ │🔒anchor: │ │🔒anchor: │ │🔒anchor: │  │
│  │gross mgn │ │net mgn   │ │arpc      │ │net mgn   │ │breaches  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Loop Graph View (`#/loops`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Loop Graph                                                         │
│  Every cycle terminates at an anchor (🔒) or a human decision.      │
│                                                                     │
│                    ◆ anchors 🔒                                      │
│                  ╱   │   │   ╲                                      │
│        goodhart◯  conflict◯ drift◯  review◯                         │
│             │         │        │        │                           │
│             └─────────┴────────┴────────┘                           │
│                        │                                            │
│                   ■ human_review                                     │
│                  ╱  │   │  │  ╲                                     │
│          strategy○ finance○ branding○ marketing○ operations○        │
│               └──────┴───────┴─────────┴──────────┘                 │
│                              │                                      │
│                         ◆ anchors 🔒                                 │
│                                                                     │
│  Legend:  ○ Execution  ◯ Monitor  ◆ Anchor🔒  ■ Human               │
│           ── work flow  -- monitors                                 │
│                                                                     │
│  ✓ All cycles terminate at an anchor or human. Topology is valid.   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. SUMMARY — The Complete Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT                                    │
│                                                                  │
│   User types ONE sentence:                                       │
│   "Ice cream shop in Andheri West, budget ₹15 lakh"             │
│                                                                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PROCESSING                                  │
│                                                                  │
│   • Intent Classification (LLM → structured JSON)                │
│   • Routing Decision (which departments to activate)             │
│   • 21 Specialized AI Agents across 5 departments               │
│   • Real competitor data from Google Places / OSM                │
│   • Market research from Serper.dev                              │
│   • Cross-department validation and reconciliation               │
│   • Total time: 60–90 seconds                                    │
│                                                                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        OUTPUT                                    │
│                                                                  │
│   Complete business plan with:                                   │
│   • Market sizing (TAM/SAM/SOM with ₹ figures)                   │
│   • Real competitors (names, ratings, from Google Maps)          │
│   • Full financial model (setup + monthly + P&L + break-even)    │
│   • Brand identity (name, voice, colours, visual direction)      │
│   • Marketing plan (channels, personas, 90-day campaign)         │
│   • Operations playbook (staff, supply chain, processes)         │
│                                                                  │
│   Delivered as: Web report + PDF + JSON                          │
│   Target users: Entrepreneurs, students, consultants, investors  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*Document generated: 11 August 2026*
*For the latest system state, see `docs/HANDOVER.md` (989 tests, all passing)*
