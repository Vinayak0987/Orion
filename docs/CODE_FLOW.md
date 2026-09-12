# Orion — Code Flow: File-by-File, Line-by-Line

**From the moment the user presses Enter to the final PDF download.**
Every file, every function, in exact execution order.

---

## COMPLETE EXECUTION FLOWCHART

```
USER TYPES: "Ice cream shop in Andheri West, budget Rs 15 lakh"
    │
    │ [Browser: localhost:5173]
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  frontend/src/components/PromptForm.jsx                          │
│  Line 42: onGenerate(prompt) called on Enter/button click        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  frontend/src/App.jsx                                            │
│  Line 95: generate(prompt) → calls streamGeneration()            │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  frontend/src/api.js                                             │
│  Line 78: new WebSocket(ws://localhost:8080/ws/generate)          │
│  Line 82: socket.send({ prompt, force_all_departments: false })  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ [WebSocket connection to backend]
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/main.py                                             │
│  Line 230: @app.websocket("/ws/generate")                        │
│  Line 235: payload = await websocket.receive_json()              │
│  Line 238: prompt = payload["prompt"]                            │
│  Line 245: calls orchestrate(prompt, ...)                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
════════════════════════════════════════════════════════════════════
 STAGE 1: INTENT CLASSIFICATION (~2 seconds)
════════════════════════════════════════════════════════════════════
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/orchestrator/runner.py                               │
│  Line 45: intent = await classify_intent(prompt)                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/intent/__init__.py                                   │
│  Line 8: from .classifier import classify_intent                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/intent/classifier.py                                │
│                                                                  │
│  Line 35: async def classify_intent(prompt: str):                │
│  Line 42:   response = await llm_client.complete(request)        │
│             → sends to Groq/Gemini/Ollama via fallback chain     │
│  Line 48:   raw_json = parse_json(response.text)                 │
│  Line 52:   intent = BusinessIntent(**raw_json)                  │
│             → Pydantic validates every field                     │
│  Line 58:   intent.budget = parse_budget(raw_json.budget_text)   │
│  Line 60:   intent.location = parse_location(raw_json)           │
│  Line 63:   return intent                                        │
│                                                                  │
│  THE LLM CALL:                                                   │
│  Prompt sent: "Extract structured business intent from:          │
│    'Ice cream shop in Andheri West, budget Rs 15 lakh'           │
│    Return JSON with: business_type, sector, location, budget..." │
│                                                                  │
│  LLM returns:                                                    │
│  {                                                               │
│    "business_type": "ice_cream_shop",                            │
│    "sector": "food_and_beverage",                                │
│    "area": "Andheri West",                                       │
│    "city": "Mumbai",                                             │
│    "budget_text": "Rs 15 lakh"                                   │
│  }                                                               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/intent/budget_parser.py                              │
│  Line 18: def parse_budget(text: str) -> Budget:                 │
│  Line 25:   "Rs 15 lakh" → amount=1500000, currency="INR"       │
│  Line 30:   scale = "small" (Rs 10L-50L range)                   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/intent/location_parser.py                            │
│  Line 15: def parse_location(data) -> Location:                  │
│  Line 22:   "Andheri West" → area="Andheri West", city="Mumbai"  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/intent/taxonomy.py                                   │
│  Line 8:  Sector.FOOD_AND_BEVERAGE → is_physical=True            │
│  Line 45: requires_operations=True (physical business)           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
    RESULT: BusinessIntent object ready                            
                                │
                                ▼
════════════════════════════════════════════════════════════════════
 STAGE 2: ROUTING DECISION (<100ms, no LLM call)
════════════════════════════════════════════════════════════════════
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/orchestrator/routing.py                              │
│                                                                  │
│  Line 20: def resolve_departments(intent: BusinessIntent):       │
│  Line 28:   active = [STRATEGY, FINANCE, BRANDING, MARKETING]    │
│  Line 32:   if intent.is_physical:                               │
│  Line 33:     active.append(OPERATIONS)    ← YES for ice cream   │
│  Line 38:   skipped = [] (nothing skipped for physical)          │
│  Line 42:   return RoutingDecision(active=active, skipped=[])    │
│                                                                  │
│  DECISION: Run all 5 departments (21 agents)                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/orchestrator/graph.py                                │
│                                                                  │
│  Line 15: def build_execution_graph(decision):                   │
│  Line 22:   Stage 1: [strategy]          ← runs first (alone)   │
│  Line 25:   Stage 2: [finance, branding, marketing] ← PARALLEL  │
│  Line 28:   Stage 3: [operations]        ← needs finance data   │
│  Line 35:   return LangGraph StateGraph with these stages        │
│                                                                  │
│  This is the LangGraph DAG:                                      │
│       strategy ──┬── finance ────┐                               │
│                  ├── branding    ├── operations                   │
│                  └── marketing ──┘                                │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
════════════════════════════════════════════════════════════════════
 STAGE 3: AGENT EXECUTION (40-70 seconds, 21 LLM calls)
════════════════════════════════════════════════════════════════════
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/orchestrator/runner.py                               │
│                                                                  │
│  Line 52: compiled_graph = graph.compile()                       │
│  Line 55: state = SharedBusinessState(intent=intent, ...)        │
│  Line 60: result = await compiled_graph.ainvoke(state)            │
│           → LangGraph runs each stage in order                   │
│           → emits WebSocket progress events at each step         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/agents/subgraph.py                                   │
│                                                                  │
│  Line 18: def build_department_subgraph(department, agents):     │
│  Line 25:   for agent in agents:                                 │
│  Line 28:     node = make_agent_node(agent)                      │
│  Line 32:     subgraph.add_node(agent.spec.agent_id, node)       │
│  Line 38:   return compiled subgraph                             │
│                                                                  │
│  Each department is itself a LangGraph sub-graph.                │
│  Agents within a department run sequentially (they depend on     │
│  each other's output within the same department).                │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/agents/base.py                                       │
│                                                                  │
│  Line 45: class BaseAgent:                                       │
│  Line 52:   async def run(self, state: SharedBusinessState):     │
│  Line 58:     prompt = self.build_prompt(state)                  │
│             → reads intent, previous dept outputs from state     │
│  Line 62:     response = await llm_client.complete(              │
│                 LLMRequest(prompt=prompt, ...))                   │
│  Line 68:     parsed = self.parse_response(response.text)        │
│             → extracts JSON from LLM response                    │
│  Line 72:     validated = self.schema.model_validate(parsed)     │
│             → Pydantic validates against agent's schema          │
│  Line 78:     state = apply_department_patch(state, validated)   │
│             → appends output to shared state (never overwrites)  │
│  Line 82:     return state                                       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
    FOR EACH OF THE 21 AGENTS:  │
                                ▼
```

---

## STAGE 3 DETAIL: Each Agent's Execution

### STRATEGY DEPARTMENT (runs first, alone)

```
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/agents/strategy.py                                   │
│                                                                  │
│  AGENT 1: Market Sizing                                          │
│  Line 35: reads: intent.sector, intent.location, intent.budget   │
│  Line 42: LLM prompt: "Calculate TAM SAM SOM for {sector}        │
│            in {location}. TAM = total market, SAM = segment       │
│            we can reach, SOM = what we can capture year 1."       │
│  Line 58: output → { tam_inr, sam_inr, som_inr, growth_rate }   │
│  Line 62: validated: som_inr <= sam_inr <= tam_inr (enforced)    │
│                                                                  │
│  AGENT 2: Competitor Analysis                                    │
│  Line 85: reads: intent.location, intent.sector                  │
│  Line 90: FIRST calls external API:                              │
│           → app/apis/places.py Line 45: search_nearby()          │
│           → Google Places API OR Overpass (OpenStreetMap)         │
│           → returns REAL businesses with ratings                  │
│  Line 98: LLM prompt: "Analyze these real competitors:           │
│            {api_results}. Identify gaps and opportunities."       │
│  Line 110: output → { competitors: [...], gap_analysis }         │
│                                                                  │
│  AGENT 3: Positioning                                            │
│  Line 130: reads: intent + market_size + competitors             │
│  Line 135: LLM prompt: "Given market of {som} and competitors    │
│             {names}, define unique positioning for this business" │
│  Line 145: output → { usp, target_segment, differentiation }    │
│                                                                  │
│  AGENT 4: SWOT Analysis                                          │
│  Line 165: reads: intent + market + competitors + positioning    │
│  Line 170: LLM prompt: "SWOT analysis for {business_type} in     │
│             {location} given {competitors} and {positioning}"    │
│  Line 182: output → { strengths, weaknesses, opportunities,     │
│                        threats } (each is a list of strings)     │
│                                                                  │
│  AGENT 5: Competitive Advantage                                  │
│  Line 200: reads: all above                                      │
│  Line 205: LLM prompt: "What is the defensible competitive       │
│             advantage given {positioning} and {swot}?"           │
│  Line 215: output → { competitive_advantage, barriers, kpis }   │
└─────────────────────────────────────────────────────────────────┘
```

### FINANCE DEPARTMENT (parallel with Branding + Marketing)

```
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/agents/finance.py                                    │
│                                                                  │
│  AGENT 6: Cost Structure                                         │
│  Line 40: reads: intent.budget, intent.location, intent.sector   │
│  Line 48: LLM prompt: "Break down setup and monthly costs for    │
│            {business_type} in {location}, budget {budget}"       │
│  Line 65: output → { total_setup_cost_inr, setup_costs: [...],  │
│                       total_monthly_cost_inr, monthly_costs }    │
│  Line 70: ENFORCED: total_setup_cost <= intent.budget            │
│           (code constraint, not LLM request)                     │
│                                                                  │
│  AGENT 7: Revenue Model                                          │
│  Line 95: reads: intent + strategy.som_inr + costs              │
│  Line 102: LLM prompt: "Revenue streams and pricing for          │
│             {business_type}. Year 1 revenue must not exceed      │
│             SOM of {som_inr}."                                   │
│  Line 118: output → { revenue_streams, projected_revenue_y1,    │
│                        pricing_strategy }                        │
│  Line 122: ENFORCED: revenue <= som_inr                          │
│                                                                  │
│  AGENT 8: P&L Forecast                                           │
│  Line 145: reads: costs + revenue                                │
│  Line 152: LLM prompt: "20-period P&L statement. Use these       │
│             costs: {monthly_costs}. Revenue ramps from 40%       │
│             to 100% over 6 months."                              │
│  Line 170: output → { pl_forecast: [{period, revenue, cogs,     │
│             opex, net_profit, net_margin_pct}, ...20 rows] }     │
│                                                                  │
│  AGENT 9: Funding & Break-even                                   │
│  Line 195: reads: costs + revenue + P&L                          │
│  Line 200: LLM prompt: "When does this business break even?      │
│             Setup={setup_cost}, monthly={monthly_cost},           │
│             revenue growth={from P&L}"                            │
│  Line 215: output → { break_even_month, total_funding_required } │
└─────────────────────────────────────────────────────────────────┘
```

### BRANDING DEPARTMENT (parallel with Finance + Marketing)

```
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/agents/branding.py                                   │
│                                                                  │
│  AGENT 10: Brand Identity                                        │
│  Line 30: reads: intent + strategy.positioning                   │
│  Line 38: LLM → { recommended_name, tagline, brand_values }     │
│                                                                  │
│  AGENT 11: Brand Voice                                           │
│  Line 65: reads: intent + brand_identity                         │
│  Line 72: LLM → { voice_tone, vocabulary_style, sample_post }   │
│                                                                  │
│  AGENT 12: Visual Direction                                      │
│  Line 95: reads: intent + identity + voice                       │
│  Line 102: LLM → { logo_style, color_palette, aesthetic_mood }  │
│                                                                  │
│  AGENT 13: Brand Story                                           │
│  Line 125: reads: all branding above                             │
│  Line 132: LLM → { brand_story, origin_narrative }              │
└─────────────────────────────────────────────────────────────────┘
```

### MARKETING DEPARTMENT (parallel with Finance + Branding)

```
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/agents/marketing.py                                  │
│                                                                  │
│  AGENT 14: Digital Marketing Plan                                │
│  Line 32: reads: intent + strategy.target_segment                │
│  Line 40: LLM → { channels: [{name, budget_share_pct, kpis}] }  │
│                                                                  │
│  AGENT 15: Buyer Persona                                         │
│  Line 68: reads: intent + strategy + digital_plan                │
│  Line 75: LLM → { personas: [{name, age, income, pain_points}] }│
│                                                                  │
│  AGENT 16: Campaign Plan                                         │
│  Line 100: reads: intent + personas + channels                   │
│  Line 108: LLM → { campaign_phases: [{phase, activities, kpis}] }│
│                                                                  │
│  AGENT 17: SEO & Content                                         │
│  Line 130: reads: intent + personas + channels                   │
│  Line 138: LLM → { keywords: [...], content_topics, calendar }  │
└─────────────────────────────────────────────────────────────────┘
```

### OPERATIONS DEPARTMENT (runs last, needs Finance data)

```
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/agents/operations.py                                 │
│                                                                  │
│  AGENT 18: Supply Chain                                          │
│  Line 28: reads: intent + finance.costs                          │
│  Line 35: LLM → { vendors, inventory_approach, raw_materials }  │
│                                                                  │
│  AGENT 19: Staffing Plan                                         │
│  Line 58: reads: intent + finance.monthly_cost                   │
│  Line 65: LLM → { roles: [{title, count, salary_range}] }       │
│  Line 72: ENFORCED: total_payroll <= finance.monthly_cost        │
│                                                                  │
│  AGENT 20: Technology Stack                                      │
│  Line 90: reads: intent + operations_type                        │
│  Line 97: LLM → { recommended_tools: [{name, purpose, cost}] }  │
│           (all free or low-cost recommendations)                 │
│                                                                  │
│  AGENT 21: Process Flow                                          │
│  Line 115: reads: intent + staffing + supply_chain               │
│  Line 122: LLM → { daily_workflow: [{step, time, owner_role}] }  │
└─────────────────────────────────────────────────────────────────┘
```

---

## THE LLM FALLBACK CHAIN (every agent call goes through this)

```
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/llm/chain.py                                         │
│                                                                  │
│  Line 30: class LLMClient:                                       │
│  Line 45:   async def complete(self, request: LLMRequest):       │
│  Line 50:     for provider in [self.groq, self.gemini, self.ollama]:
│  Line 52:       if await provider.is_available():                │
│  Line 55:         try:                                           │
│  Line 56:           response = await provider.complete(request)  │
│  Line 58:           return response  ← SUCCESS, return           │
│  Line 60:         except ProviderUnavailable:                    │
│  Line 61:           continue  ← TRY NEXT PROVIDER               │
│  Line 65:     raise AllProvidersExhausted(...)                   │
│                                                                  │
│  Order: Groq (fastest) → Gemini (best JSON) → Ollama (offline)  │
│  The user never sees which provider served which agent.          │
└─────────────────────────────────────────────────────────────────┘
                                │
    Providers:                  │
    ┌───────────────────────────┼───────────────────────────┐
    ▼                           ▼                           ▼
┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐
│ groq_provider│  │ gemini_provider  │  │ ollama_provider   │
│ .py          │  │ .py              │  │ .py               │
│              │  │                  │  │                   │
│ POST https://│  │ POST https://    │  │ POST http://      │
│ api.groq.com │  │ generativelang.. │  │ localhost:11434   │
│ /v1/chat/    │  │ /v1/models/      │  │ /api/generate     │
│ completions  │  │ gemini-flash:    │  │                   │
│              │  │ generateContent  │  │ (local, no net)   │
└──────────────┘  └──────────────────┘  └───────────────────┘
```

---

## STAGE 3 CONTINUED: External API Calls

```
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/apis/places.py                                       │
│                                                                  │
│  Called by: Strategy → Competitor Analysis Agent                  │
│                                                                  │
│  Line 45: async def search_nearby(location, business_type):      │
│  Line 52:   if google_places_key:                                │
│  Line 55:     POST https://places.googleapis.com/v1/places:      │
│               searchNearby                                        │
│               body: { location, radius: 2000, type: business }   │
│  Line 70:   elif enable_overpass:                                │
│  Line 73:     GET https://overpass-api.de/api/interpreter        │
│               query: [amenity={type}](around:2000,lat,lon)       │
│  Line 85:   return [{ name, rating, reviews, address, source }]  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/apis/serper.py                                       │
│                                                                  │
│  Called by: Strategy → Market Sizing Agent                        │
│                                                                  │
│  Line 20: async def search_market_data(query):                   │
│  Line 28:   POST https://google.serper.dev/search                │
│             body: { q: "{sector} market size {city} 2024" }      │
│  Line 35:   return [{ title, snippet, link }]                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/apis/cache.py                                        │
│                                                                  │
│  Line 15: def get_or_fetch(query, fetcher):                      │
│  Line 20:   cached = chromadb_collection.query(query)            │
│  Line 25:   if cached and not stale:                             │
│  Line 26:     return cached  ← NO API CALL, use cache           │
│  Line 30:   result = await fetcher()  ← actual API call          │
│  Line 35:   chromadb_collection.add(result)  ← save for next time│
│  Line 38:   return result                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## STAGE 4: OUTPUT ASSEMBLY (~3 seconds)

```
════════════════════════════════════════════════════════════════════
 STAGE 4: ASSEMBLE OUTPUT
════════════════════════════════════════════════════════════════════
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/orchestrator/runner.py                               │
│                                                                  │
│  Line 75: state = result  (SharedBusinessState with all data)    │
│  Line 78: metadata = build_metadata(state)                       │
│  Line 82: package = assemble_package(state)                      │
│  Line 85: persist_session(state)  → saves to SQLite              │
│  Line 88: send WebSocket "result" event to frontend              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/output/package.py                                    │
│                                                                  │
│  Line 95: def assemble_package(state) -> BusinessPackage:        │
│  Line 100:  sections = {}                                        │
│  Line 102:  for dept in active_departments:                      │
│  Line 105:    sections[dept] = state[dept]  (all agent outputs)  │
│  Line 110:  metadata = build_metadata(state)                     │
│             → agents used, models, tokens, latency, API calls    │
│  Line 115:  return BusinessPackage(                              │
│               session_id, prompt, intent, sections, metadata)    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/output/html.py                                       │
│                                                                  │
│  Line 20: def render_html(package: BusinessPackage) -> str:      │
│  Line 25:   template = jinja2.get_template("report.html.j2")    │
│  Line 30:   return template.render(                              │
│               sections=package.sections,                         │
│               metadata=package.metadata,                         │
│               brand_colors=package.sections.branding.colors)     │
│                                                                  │
│  Produces: standalone HTML report styled in the brand's palette  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/output/pdf.py                                        │
│                                                                  │
│  Line 15: def render_pdf(html: str) -> bytes:                    │
│  Line 20:   try: import weasyprint → better CSS support          │
│  Line 25:   except: from xhtml2pdf → pure Python fallback        │
│  Line 30:   return pdf_bytes                                     │
│                                                                  │
│  Produces: branded PDF with cover page, TOC, page numbers        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/db/sqlite.py                                         │
│                                                                  │
│  Line 45: def persist_session(state):                            │
│  Line 50:   INSERT INTO sessions (id, prompt, intent, plan,      │
│             status, metadata, ...)                                │
│  Line 55:   → saved to data/mabgp.db (SQLite, WAL mode)         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
════════════════════════════════════════════════════════════════════
 RESPONSE BACK TO FRONTEND
════════════════════════════════════════════════════════════════════
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/main.py                                              │
│                                                                  │
│  Line 255: await websocket.send_json({                           │
│              "event": "result",                                   │
│              "summary": {                                         │
│                "session_id": "...",                               │
│                "status": "completed",                             │
│                "plan": { strategy: {...}, finance: {...}, ... },  │
│                "intent": { business_type, location, budget },    │
│                "routing": { active: [...], skipped: [...] },     │
│                "completeness_score": 100.0,                      │
│                "total_duration_ms": 62000,                        │
│                "total_tokens": 8500                               │
│              }                                                    │
│            })                                                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ [WebSocket message to browser]
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  frontend/src/api.js                                              │
│                                                                  │
│  Line 88: if (payload.event === "result")                        │
│  Line 89:   onResult(payload.summary)  → triggers state update   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  frontend/src/App.jsx                                             │
│                                                                  │
│  Line 98: onResult: (result) => {                                │
│  Line 99:   setSummary(result)  → React re-renders               │
│  Line 100:  setRunning(false)   → hides progress bar             │
│  Line 101: }                                                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  frontend/src/components/ReportView.jsx                           │
│                                                                  │
│  Renders the complete plan:                                      │
│  • KPI cards (setup cost, break-even, margin, revenue)           │
│  • Department tabs (Strategy, Finance, Branding, etc.)           │
│  • Collapsible sections with all agent outputs                   │
│  • Download buttons (PDF, JSON, copy)                            │
│  • Pipeline view (Input → Processing → Output per agent)         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
           USER SEES THE COMPLETE BUSINESS PLAN
           Total time: 60-90 seconds
```

---

## QUALITY ENFORCEMENT (runs during Stage 3)

```
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/orchestrator/completeness.py                         │
│                                                                  │
│  Called AFTER all agents finish:                                  │
│                                                                  │
│  Line 20: def score_completeness(state, active_depts):           │
│  Line 25:   expected_fields = 26 (for 5 depts)                   │
│  Line 30:   present = count fields that are non-null             │
│  Line 35:   score = present / expected * 100                     │
│  Line 40:   return CompletenessReport(score, missing_fields)     │
│                                                                  │
│  Also checks:                                                    │
│  Line 50: revenue <= SOM (Strategy market size)                  │
│  Line 55: setup_cost <= budget                                   │
│  Line 60: payroll <= monthly_cost                                │
│  Line 65: net_margin <= gross_margin                             │
│  Line 70: P&L opex matches cost structure monthly total          │
│                                                                  │
│  Violations recorded as validation_warnings, not errors.         │
│  The plan still generates; warnings are shown to the user.       │
└─────────────────────────────────────────────────────────────────┘
```

---

## SHARED STATE CONTRACT

```
┌─────────────────────────────────────────────────────────────────┐
│  backend/app/models/state.py                                      │
│                                                                  │
│  The SharedBusinessState is a TypedDict that ALL agents share.   │
│  RULE: agents APPEND to it, never OVERWRITE another dept's data. │
│                                                                  │
│  {                                                               │
│    "session_id": "abc123",                                       │
│    "intent": { business_type, location, budget, sector },        │
│    "metadata": { status, duration, active_departments },         │
│    "strategy": { market_size, competitors, swot, ... },          │
│    "finance": { costs, revenue, pl_forecast, ... },              │
│    "branding": { name, tagline, colors, voice, ... },            │
│    "marketing": { channels, personas, campaigns, ... },          │
│    "operations": { supply_chain, staffing, tech, workflow },     │
│    "agent_traces": [ {agent_id, provider, tokens, latency} ],   │
│    "api_traces": [ {api, query, results, cached} ]               │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## COMPLETE TIMING BREAKDOWN

```
TOTAL: 60-90 seconds (with Groq/Gemini)
       ~120 seconds (with Ollama only)

  Intent Classification:     2s  (1 LLM call)
  Routing Decision:        <0.1s (no LLM, pure rules)
  Strategy (5 agents):      12s  (5 LLM calls + 1 API call)
  Finance (4 agents):       18s  (4 LLM calls) ─┐
  Branding (4 agents):      14s  (4 LLM calls)  ├─ PARALLEL
  Marketing (4 agents):     16s  (4 LLM calls) ─┘
  Operations (4 agents):    10s  (4 LLM calls, after Finance)
  Output Assembly:           3s  (no LLM, just formatting)
                           ────
  Total LLM calls:          22  (1 intent + 21 agents)
  Total API calls:         1-3  (Places + Serper, cached after)
  Total tokens:         6,000-10,000
```

---

*This document traces the exact path from user input to final output.*
*Every file and function mentioned is real and can be found at the stated location.*
*Line numbers are approximate — the logic is accurate.*
