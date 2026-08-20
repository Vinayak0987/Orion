# Orion Agent Flow - Detailed Explanation

How a single sentence from a user becomes a complete business plan through 21
specialised agents, and what each one reads, does, and produces.

---

## 1. The Initial Input

**What the user provides:** one sentence.

```
"Open an ice cream shop in Andheri West with a budget of 15 lakhs"
```

That is it. No template, no form, no structured input. Everything else is
extracted or generated.

---

## 2. Intent Classification (before any agent runs)

The sentence first passes through a **hybrid classifier** that splits work between
an LLM and deterministic code:

| Extracted by | Fields | Why separated |
|---|---|---|
| **LLM** | business_type, sector, location hints, confidence | semantic understanding |
| **Regex + gazetteer** | budget amount and scale, location normalisation, routing flags | so budget parsing never varies between providers and financial projections stay anchored |

**Output: `BusinessIntent`**

```json
{
  "business_type": "ice_cream_shop",
  "business_type_label": "Ice Cream Shop",
  "sector": "food_and_beverage",
  "location": {"city": "Mumbai", "area": "Andheri West", "state": "Maharashtra"},
  "budget": {"amount_inr": 1500000, "scale": "small"},
  "scale": "small",
  "is_physical": true,
  "requires_operations": true,
  "confidence": 0.92,
  "raw_prompt": "Open an ice cream shop in Andheri West with a budget of 15 lakhs"
}
```

**Why the split matters:** every financial projection is anchored to the budget. If
budget parsing varied between providers, the variance in financial accuracy would
not be attributable to the agents. Similarly, routing must be deterministic so both
arms of the RQ2 experiment are comparable.

---

## 3. Routing Decision

The orchestrator examines the intent and decides which departments run:

- `is_physical = true` and `requires_operations = true` -> **all 5 departments active**
- If digital / no premises -> Operations is skipped (the RQ2 manipulation)

**Execution DAG compiled:**

```
START -> Strategy -> [Finance | Branding | Marketing] -> Operations -> END
              stage 1            stage 2 (concurrent)       stage 3
```

Stage 2 departments run in **parallel** (same LangGraph superstep). Operations
cannot start until all three complete because it costs against Finance's budget and
assigns workflows to Marketing's personas.

---

## 4. Department Execution - Agent by Agent

Every agent follows the same lifecycle:

1. Receive the `SharedBusinessState` (read-only access to other departments' sections)
2. Build a prompt from the intent + what earlier agents in its department wrote
3. Call the LLM through the fallback chain (Groq -> Gemini -> Ollama)
4. Validate the JSON response with Pydantic
5. Coerce common type errors (nested lists, nulls, currency strings)
6. Write ONLY to its own department's section via `apply_department_patch`

---

### STRATEGY DEPARTMENT (5 agents)

#### Stage 1 (concurrent - all three run at once)

**1. MarketResearchAgent** (`market_research`)

| | Detail |
|---|---|
| **Reads** | intent (business_type, sector, location, budget) |
| **Function** | Estimates the total addressable market, serviceable market and obtainable market for this business type in this location. Identifies industry growth rate. |
| **LLM Prompt** | "You are a market research analyst. For a {business_type} in {location} with {budget}, estimate the market size..." |
| **Output fields** | `market_size` (TAM/SAM/SOM in INR), `market_overview`, `market_statistics`, `industry_growth_rate_pct` |
| **Grounding** | Can use Serper web search for market statistics if enabled |

**2. CompetitiveAnalysisAgent** (`competitive_analysis`)

| | Detail |
|---|---|
| **Reads** | intent (business_type, location) |
| **Function** | Finds real nearby competitors, analyses their strengths, weaknesses, pricing. Identifies market gaps the new business can exploit. |
| **LLM Prompt** | "You are a competitive intelligence analyst. For a {business_type} in {area}, identify competitors..." |
| **Output fields** | `competitors` (list of {name, type, distance_km, strengths, weaknesses, price_range, source}), `market_gaps`, `positioning` |
| **Grounding** | Calls **OpenStreetMap Overpass** for real businesses within 2 km. Each competitor carries a `source` label (openstreetmap / llm_inferred). |

**3. LocationIntelligenceAgent** (`location_intelligence`)

| | Detail |
|---|---|
| **Reads** | intent (location) |
| **Function** | Assesses the location's viability: footfall, accessibility, complementary businesses nearby, parking, transit access. |
| **Output fields** | `location_score` (0-10), `location_rationale`, `footfall_assessment`, `complementary_businesses`, `accessibility_notes` |

#### Stage 2 (concurrent - both run after stage 1 completes)

**4. BusinessPlanningAgent** (`business_planning`)

| | Detail |
|---|---|
| **Reads** | intent + stage 1 output (market_size, competitors, location_score) |
| **Function** | Synthesises everything into the executive summary, vision, mission, business model type and value proposition. Uses the competitor set to position against. |
| **Output fields** | `executive_summary`, `vision`, `mission`, `business_model_type`, `value_proposition` |
| **Dependency** | Reads the market size that market_research already wrote, and the competitor set that competitive_analysis already wrote. That is why it is stage 2. |

**5. RiskAnalysisAgent** (`risk_analysis`)

| | Detail |
|---|---|
| **Reads** | intent + all of stage 1 (competitors, market conditions, location) |
| **Function** | Identifies business risks: competition risk, market risk, operational risk, financial risk, regulatory risk. Assigns likelihood and impact. |
| **Output fields** | `risks` (list of {category, description, likelihood, impact, mitigation}) |

---

### FINANCE DEPARTMENT (4 agents)

#### Stage 1 (concurrent)

**6. RevenueModelAgent** (`revenue_model`)

| | Detail |
|---|---|
| **Reads** | intent (budget, sector), strategy output (market_size.obtainable_market) |
| **Function** | Designs revenue streams, pricing strategy, average ticket size. Projects revenue for years 1-3. Revenue is CAPPED at min(obtainable_market, 10x budget) ? this is one of the 5 deterministic reconciliations. |
| **Output fields** | `revenue_streams`, `pricing_strategy`, `avg_ticket_size_inr`, `projected_revenue_y1/y2/y3_inr`, `seasonality_notes` |
| **Hard constraint** | Year 1 revenue CANNOT exceed the obtainable market. The cap is arithmetic on a user-supplied figure, so it holds regardless of what the model claims. |

**7. CostStructureAgent** (`cost_structure`)

| | Detail |
|---|---|
| **Reads** | intent (budget, is_physical) |
| **Function** | Itemises all setup costs (one-time) and recurring costs (monthly). Computes total setup cost and monthly cost. Checks budget utilisation. |
| **Output fields** | `setup_costs` (list of {item, amount_inr, category}), `recurring_costs` (list of {item, amount_inr, frequency}), `total_setup_cost_inr`, `total_monthly_cost_inr`, `budget_utilization_pct`, `within_budget` |
| **Hard constraint** | `total_setup_cost_inr` is SUMMED from the itemised list, not asserted. The model provides line items; Python sums them. |

#### Stage 2 (concurrent)

**8. FundingStrategyAgent** (`funding_strategy`)

| | Detail |
|---|---|
| **Reads** | intent (budget, location), cost_structure output (total_setup_cost) |
| **Function** | Recommends funding approach (self-funded, loan, angel, government scheme), identifies applicable Indian government schemes (MUDRA, Stand-Up India, PMEGP, etc). |
| **Output fields** | `funding_approach`, `funding_amount_inr`, `funding_schemes` (names of real Indian MSME schemes), `funding_timeline` |

**9. PLForecastAgent** (`pl_forecast`)

| | Detail |
|---|---|
| **Reads** | revenue_model output (y1 revenue), cost_structure output (monthly costs) |
| **Function** | Produces a 20-period P&L forecast. The agent provides 6 DRIVERS: opening revenue, exit revenue, COGS%, fixed opex, and two growth rates. ALL 20 periods, both margins and the break-even month are then COMPUTED IN PYTHON. |
| **Output fields** | `pl_forecast` (20 periods of {revenue, cogs, opex, net_profit, margin_pct}), `gross_margin_pct`, `net_margin_pct`, `steady_state_net_margin_pct`, `break_even_month`, `benchmark_margin_pct` |
| **Reconciliation** | The P&L opex is reconciled against the cost agent's summed total. The year-2 projection grows from month-12 exit revenue, not from the year-1 total. Revenue is bounded by the obtainable market. These are the deterministic fixes that reduced MAPE from ~450 to ~130. |

---

### BRANDING DEPARTMENT (4 agents)

#### Stage 1

**10. BrandNamingAgent** (`brand_naming`)

| | Detail |
|---|---|
| **Reads** | intent (business_type, location), strategy output (positioning) |
| **Function** | Generates 3-5 brand name candidates with rationale, linguistic analysis, and domain/trademark availability assessment. Recommends one. |
| **Output fields** | `name_candidates` (list of {name, rationale, availability}), `recommended_name` |

#### Stage 2 (concurrent - all three reference the chosen name)

**11. BrandIdentityAgent** (`brand_identity`)

| | Detail |
|---|---|
| **Reads** | recommended_name, positioning |
| **Function** | Defines visual identity: colour palette (primary, secondary, accent with hex codes), fonts, logo style direction. |
| **Output fields** | `personality_traits`, `color_palette` ({primary, secondary, accent} with hex), `heading_font`, `body_font`, `logo_style`, `visual_mood` |

**12. BrandVoiceAgent** (`brand_voice`)

| | Detail |
|---|---|
| **Reads** | recommended_name, personality_traits |
| **Function** | Establishes the communication tone, voice dos and donts, sample taglines and a sample social media post. |
| **Output fields** | `tone`, `taglines`, `sample_social_post`, `voice_dos`, `voice_donts` |

**13. VisualDesignAgent** (`visual_design`)

| | Detail |
|---|---|
| **Reads** | recommended_name, color_palette, personality_traits, is_physical |
| **Function** | Provides signage direction and visual mood guidelines for physical spaces (if applicable). |
| **Output fields** | `signage_direction`, `visual_mood` |

---

### MARKETING DEPARTMENT (4 agents)

#### Stage 1

**14. BuyerPersonaAgent** (`buyer_persona`)

| | Detail |
|---|---|
| **Reads** | intent (business_type, location, sector), strategy output (positioning) |
| **Function** | Creates 2-3 detailed buyer personas: demographics, psychographics, pain points, decision triggers, preferred channels. |
| **Output fields** | `personas` (list of {name, age_range, income, pain_points, channels, decision_triggers}) |

#### Stage 2 (concurrent)

**15. DigitalPlanAgent** (`digital_plan`)

| | Detail |
|---|---|
| **Reads** | personas, intent (budget) |
| **Function** | Allocates the marketing budget across channels (social, search, local, influencer, etc). Calculates per-channel spend. |
| **Output fields** | `channels` (list of {name, budget_pct, monthly_spend_inr, tactics}), `total_marketing_budget_inr`, `channel_strategy_summary` |
| **Hard constraint** | Channel budget percentages MUST sum to 100%. Enforced by normalisation after generation. |

**16. CampaignPlanAgent** (`campaign_plan`)

| | Detail |
|---|---|
| **Reads** | personas, channels, recommended_name |
| **Function** | Designs the launch campaign in phases: pre-launch, launch week, sustain. Each phase has activities, timeline and KPIs. |
| **Output fields** | `campaign_phases` (list of {name, duration, activities, kpis}), `launch_hook` |

**17. SEOContentAgent** (`seo_content`)

| | Detail |
|---|---|
| **Reads** | personas, positioning, location |
| **Function** | Identifies target keywords, content topics, formats and publishing frequency for organic growth. |
| **Output fields** | `target_keywords`, `content_topics`, `content_frequency`, `content_formats` |

---

### OPERATIONS DEPARTMENT (4 agents)

*Only runs when `requires_operations = true` (physical businesses).*

#### Stage 1 (concurrent)

**18. SupplyChainAgent** (`supply_chain`)

| | Detail |
|---|---|
| **Reads** | intent (business_type), finance output (cost breakdown) |
| **Function** | Identifies inventory requirements, vendors, and inventory management approach. |
| **Output fields** | `inventory_requirements`, `vendors` (list of {name, category, cost_range}), `inventory_approach` |

**19. StaffingPlanAgent** (`staffing_plan`)

| | Detail |
|---|---|
| **Reads** | intent (business_type, budget), finance output (monthly_cost) |
| **Function** | Defines roles, salaries, and headcount for year 1. |
| **Output fields** | `roles` (list of {title, count, monthly_salary_inr, responsibilities}), `total_headcount_y1`, `total_monthly_payroll_inr` |

**20. TechStackAgent** (`tech_stack`)

| | Detail |
|---|---|
| **Reads** | intent (business_type, is_physical) |
| **Function** | Recommends software tools for POS, accounting, CRM, social media management. |
| **Output fields** | `tools` (list of {name, purpose, monthly_cost_inr}), `total_tool_cost_monthly_inr` |

#### Stage 2

**21. ProcessFlowAgent** (`process_flow`)

| | Detail |
|---|---|
| **Reads** | All of stage 1 (roles, inventory, tools) |
| **Function** | Designs the daily workflow: opening to closing sequence, each step assigned to a REAL role from the staffing plan. This assignment is checkable ? the consistency metric verifies every workflow owner is a role that was actually hired. |
| **Output fields** | `daily_workflow` (list of {step, time, owner, description}), `key_processes`, `quality_checkpoints` |
| **Dependency** | This is why Operations is stage 3 in the global DAG: it assigns steps to roles that StaffingPlan created, costs them against budget Finance computed, and references tools TechStack chose. |

---

## 5. What Happens After All Agents Complete

1. **Deterministic reconciliation** ? 5 specific cross-agent conflicts are resolved in code:
   - P&L opex reconciled against cost_structure's summed total
   - Revenue capped at min(obtainable_market, 10x budget)
   - Year-2 revenue grown from month-12 exit, not year-1 total
   - Channel budget percentages normalised to 100%
   - Setup costs re-summed from line items

2. **Completeness check** ? are all 26 expected fields substantively filled?

3. **Consistency check** ? 9 cross-department assertions:
   - Revenue within obtainable market
   - Setup cost within budget
   - Marketing spend within the cost base
   - Net margin below gross margin
   - Channel shares sum to 100%
   - Every workflow owner is a hired role
   - And 3 more

4. **Output generation** ? the SharedBusinessState is rendered into JSON, HTML report and PDF.

---

## 6. Complete Example

### Input

```
"Open an ice cream shop in Andheri West with a budget of 15 lakhs"
```

### After Intent Classification

```
business_type: ice_cream_shop
sector: food_and_beverage
location: Andheri West, Mumbai, Maharashtra
budget: Rs 15,00,000 (small)
is_physical: true
requires_operations: true
routing: all 5 departments active
```

### After Strategy (stage 1+2)

```
Market size: TAM Rs 3.2 Cr, SAM Rs 85 L, SOM Rs 24 L
Competitors found: Naturals (0.8 km, source: openstreetmap),
                   Baskin Robbins (1.2 km, source: openstreetmap),
                   Cold Stone (1.9 km, source: llm_inferred)
Location score: 7.8/10 (high footfall, metro adjacent)
Positioning: premium artisanal gelato, local flavours
Risks: 4 identified (competition HIGH, seasonal demand MEDIUM, ...)
```

### After Finance (stage 1+2)

```
Revenue streams: walk-in (65%), delivery (25%), catering (10%)
Pricing: avg ticket Rs 180
Year 1 revenue: Rs 28 L (bounded by min(SOM, 10x budget) = Rs 24 L -> capped)
Setup costs: Rs 12.4 L (summed from 14 line items, within the Rs 15 L budget)
Monthly costs: Rs 2.8 L
Break-even: month 7
Steady-state net margin: 14.2%
Benchmark: 9.5% (food & beverage sector)
```

### After Branding (stage 1+2)

```
Name: "Scoop Story" (recommended from 4 candidates)
Palette: primary #2E4057, secondary #F4845F, accent #F7E733
Tone: playful, warm, community-rooted
Tagline: "Every flavour tells a tale"
```

### After Marketing (stage 1+2)

```
Personas: "College Cravings" (18-24, Rs 15K), "Family Treats" (30-45, Rs 60K)
Channels: Instagram 30%, Google Local 25%, Zomato/Swiggy 20%,
          WhatsApp Community 15%, Influencers 10%
Total budget: Rs 45,000/month
Launch: "Free scoop on your birthday" + local influencer tasting
```

### After Operations (stage 1+2)

```
Roles: store manager (1, Rs 30K), scoop artists (2, Rs 15K each),
       delivery handler (1, Rs 12K), cleaner (1, Rs 10K)
Total payroll: Rs 82,000/month
Tools: Vend POS (Rs 2,500/mo), Khatabook (free), Petpooja (Rs 1,200/mo)
Workflow: 9 steps from opening (8:30 AM) to closing (10:30 PM)
  - each step assigned to a real role from the staffing plan above
```

### Final Output

A JSON package, an HTML report, and a PDF ? all generated from the same
SharedBusinessState. The consistency metric checks that Marketing's spend fits
Finance's budget, that Operations' payroll matches the monthly cost line, and that
every process_flow step names someone who was actually hired.

---

## 7. Data Flow Summary

```
User prompt (1 sentence)
    |
    v
Intent Classifier (LLM + regex)
    |
    v
BusinessIntent (structured, validated)
    |
    v
Routing Decision (deterministic)
    |
    v
Strategy [market_research | competitive_analysis | location_intelligence]
         [business_planning | risk_analysis]
    |
    v
Finance  [revenue_model | cost_structure]
Branding [brand_naming]                         <- these 3 run CONCURRENTLY
Marketing[buyer_persona]
    |
    v
Finance  [funding_strategy | pl_forecast]
Branding [brand_identity | brand_voice | visual_design]
Marketing[digital_plan | campaign_plan | seo_content]
    |
    v
Operations [supply_chain | staffing_plan | tech_stack]
           [process_flow]
    |
    v
Deterministic Reconciliation (5 fixes in code)
    |
    v
Completeness + Consistency Check (26 fields, 9 cross-checks)
    |
    v
Output: JSON + HTML + PDF
```

---

## 8. Key Architectural Rules

1. **No agent reads another department's section directly during its own execution.**
   It reads only its own department's state (what earlier agents in the same dept
   wrote) and the intent. Cross-department data flows through the DAG staging: if
   Finance needs Strategy's market size, Finance runs AFTER Strategy.

2. **An agent may write ONLY to its own department's section.** A cross-department
   write raises `StateContractViolation`. This is what makes the consistency metric
   meaningful: disagreements between departments are real disagreements, not
   write-ordering artefacts.

3. **Derived figures override asserted ones.** Where two agents assert the same
   quantity, the computed value wins. Totals are summed from line items, never
   accepted as stated.

4. **All LLM output is validated with Pydantic.** A missing or malformed field is
   coerced where possible (nested list flattened, null replaced with empty string,
   currency string parsed to int) and flagged where not.

5. **Provider chain, not a single model.** Every call walks
   Groq -> Gemini -> Ollama. If a hosted tier is exhausted mid-run, the next agent
   uses the fallback. This is why the multi-agent arm completed 100% of runs while
   the pinned baseline completed only 60%.
