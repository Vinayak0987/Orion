# 13 — LLM PROVIDER PLAN

---

## What It Is and Why It Exists in the System

The LLM Provider Layer is the **nervous system** of Orion. Every agent run, every planner call, every memory extraction, every classification — all go through this single layer.

Plans 02, 04, and 05 all say "call LLM via Groq→Gemini→Ollama chain" but none define *how* this chain actually works. This plan fills that gap completely.

**The core problem:** Free-tier LLMs have rate limits. Groq: 14,400 requests/day. Gemini: 15 requests/minute. A mission with 5 tasks and 3 tool calls each = 15+ LLM calls. Multiple users = the system hits limits fast. The LLM Provider Layer manages fallback, tracks usage per provider, and ensures no mission fails just because one provider is temporarily rate-limited.

**Rule:** Nothing in the codebase calls an LLM provider directly. Every LLM call goes through `llm_client`. This is a hard architectural constraint (already enforced in the existing backend).

---

## The Three Providers

### Groq (Primary — FAST)
- Free tier: 14,400 requests/day, 6,000 tokens/minute
- FAST model: `llama-3.1-8b-instant` — used for planner, classifier, memory extraction
- REASONING model: `llama-3.3-70b-versatile` — used for main agent execution
- Fails with: HTTP 429 (rate limit), HTTP 503 (down), timeout (>30s)

### Gemini (First Fallback)
- Free tier: 15 RPM, 1M tokens/day
- FAST model: `gemini-2.0-flash-lite`
- REASONING model: `gemini-2.0-flash`
- Fails with: HTTP 429, quota exhausted, API key invalid

### Ollama (Last Resort)
- Local, no cost, no rate limits — but slow (120–150s for full pipeline on CPU)
- Model: `llama3.1:8b` (pulled once via `ollama pull llama3.1:8b`)
- Fails with: connection refused (Ollama not running)

---

## The Two Call Tiers

Every call specifies a tier. The tier determines which model is used:

| Tier | Used By | Why |
|------|---------|-----|
| `fast` | Planner (task decomposition), memory extraction, ops classifier, agent test calls | Speed > quality. Output is structured JSON. Small context window sufficient. |
| `reasoning` | Main agent execution — research, analysis, writing tasks | Quality > speed. Output is rich text/analysis. Large context needed. |

---

## The Fallback Chain

```
User makes a mission call
         │
         ▼
_build_provider_list(tier, user_id)
         │
         ├─ 1. User's Groq key (from MongoDB, if set)
         ├─ 2. User's Gemini key (from MongoDB, if set)
         ├─ 3. User's OpenAI key (from MongoDB, if set)
         ├─ 4. System Groq key (from .env, if set)
         ├─ 5. System Gemini key (from .env, if set)
         └─ 6. Ollama (always last, always available if running)
         │
         ▼
For each provider in list:
  ├─ Is it currently rate-limited? → skip, try next
  ├─ Call provider
  ├─ Success → record usage, return result
  ├─ HTTP 429 → mark rate-limited, try next
  ├─ HTTP 503/timeout → mark failed, try next
  └─ All failed → raise AllProvidersFailedError
```

**User keys take priority.** If a user provides their own Groq key, their missions run on their personal quota, not the system shared quota. This prevents one heavy user from exhausting the system keys for everyone else.

---

## Rate Limit Tracking (In-Memory)

Rate limits reset on schedule — tracked in memory, not DB:

```python
class RateLimitTracker:
    # Groq: 14,400 requests/day
    groq_requests_today: int = 0
    groq_daily_reset: datetime          # tomorrow midnight UTC

    # Gemini: 15 RPM, 1M tokens/day
    gemini_requests_this_minute: int = 0
    gemini_minute_reset: datetime       # next minute
    gemini_tokens_today: int = 0
    gemini_daily_token_reset: datetime  # tomorrow midnight UTC

    def is_rate_limited(self, provider: str) -> bool:
        now = datetime.utcnow()
        if provider == "groq":
            if now > self.groq_daily_reset:
                self.groq_requests_today = 0          # reset
                self.groq_daily_reset = tomorrow()
            return self.groq_requests_today >= 14_400
        if provider == "gemini":
            if now > self.gemini_minute_reset:
                self.gemini_requests_this_minute = 0  # reset
                self.gemini_minute_reset = next_minute()
            if now > self.gemini_daily_token_reset:
                self.gemini_tokens_today = 0          # reset
            return (self.gemini_requests_this_minute >= 15 or
                    self.gemini_tokens_today >= 1_000_000)
        return False  # Ollama: never rate limited

    def record_call(self, provider: str, tokens: int):
        if provider == "groq":
            self.groq_requests_today += 1
        if provider == "gemini":
            self.gemini_requests_this_minute += 1
            self.gemini_tokens_today += tokens
```

---

## Cost Calculation

Stored in `execution_traces.cost_usd` per call:

```python
COST_PER_1K_TOKENS = {
    "groq/llama-3.1-8b-instant":    {"in": 0.00005,  "out": 0.00008},
    "groq/llama-3.3-70b-versatile": {"in": 0.00059,  "out": 0.00079},
    "gemini/gemini-2.0-flash-lite":  {"in": 0.000075, "out": 0.0003},
    "gemini/gemini-2.0-flash":       {"in": 0.0001,   "out": 0.0004},
    "openai/gpt-4o-mini":           {"in": 0.00015,  "out": 0.0006},
    "ollama/llama3.1:8b":           {"in": 0.0,      "out": 0.0},
}

def calculate_cost(provider, model, input_tokens, output_tokens) -> float:
    rates = COST_PER_1K_TOKENS.get(f"{provider}/{model}", {"in": 0.0, "out": 0.0})
    return (input_tokens * rates["in"] + output_tokens * rates["out"]) / 1000
```

---

## JSON Repair

The Planner and classifier call `call_structured()` which expects JSON back. LLMs sometimes wrap JSON in markdown. The repair pipeline:

```
LLM response received
       │
       ├─ Try json.loads() directly → success → return
       │
       ├─ Extract from ```json ... ``` code block → try json.loads() → success → return
       │
       ├─ Retry with repair prompt: "Fix this malformed JSON and return ONLY valid JSON: {response}"
       │    → Try json.loads() on repair response → success → return
       │
       └─ All attempts failed → raise JSONParseError → Error Handling Plan takes over
```

---

## Health Check Contribution

The `GET /health` endpoint shows live provider status:

```json
"llm_providers": {
  "groq":   { "available": true,  "latency_ms": 312, "requests_today": 1240, "limit": 14400 },
  "gemini": { "available": true,  "latency_ms": 890, "rpm_used": 3, "rpm_limit": 15 },
  "ollama": { "available": false, "error": "connection refused — Ollama not running" }
},
"any_llm_available": true
```

This is used by:
- The Settings page to show which providers are active
- The Mission Engine to decide if a mission can even start (if `any_llm_available = false` → reject immediately)
- Observability LLM Usage tab

---

## Database

No new tables. All data written to existing `execution_traces`:
- `provider` — which provider handled the call
- `model` — which model was used
- `input_tokens`, `output_tokens`
- `cost_usd` — calculated by `calculate_cost()`
- `latency_ms`

Observability's LLM Usage tab aggregates this table by provider.

---

## API Endpoints

No public endpoints. Internal service only. Exposed only through:
- `GET /health` → shows provider availability + rate limit state
- Observability endpoints → read from `execution_traces`

---

## How LLM Provider Plan Connects to Every Other Plan

| Plan | Connection |
|------|-----------|
| Settings | User API keys loaded from MongoDB → inserted at front of provider list |
| Mission Engine | Planner calls `call_structured(fast)`. Executor calls `call(reasoning)` per agent. |
| Agents | `agent.model` field maps to a provider/model string → Executor uses this for that agent |
| Knowledge | Memory extraction calls `call_structured(fast)` after each task |
| Operations | Post-mission classifier calls `call_structured(fast)` |
| Observability | Every call → `execution_traces` row → LLM Usage & Costs tab |
| Error Handling | `AllProvidersFailedError` → Error Handling Plan catches and decides mission fate |

---

## Build Order

**Phase 1 (before anything else — Mission Engine depends on it):**
1. `LLMClient` class with provider list builder
2. Groq provider implementation
3. Gemini provider implementation
4. Ollama provider implementation
5. Fallback chain (loop + skip rate-limited)
6. `RateLimitTracker` in-memory
7. Cost calculation
8. JSON repair (`call_structured`)
9. Health check probe per provider

**Phase 4 (when user API keys flow from Settings):**
10. Load user keys from MongoDB before each call
11. User providers inserted at index 0 of list
