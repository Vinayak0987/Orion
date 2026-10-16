# 02 — SETTINGS & API KEYS PLAN

---

## What It Is and Why It Exists in the System

Settings is where the user configures the system to work **for them specifically**.

The most critical function: **API Keys**. Without the user's API keys, every LLM call and tool call falls back to system defaults (shared Ollama, limited free tier). With the user's own Groq/Gemini/Serper keys, agents run against the user's personal quota — faster, more capable, not rate-limited by other users.

**Role in the whole system:** Settings is a configuration provider. It feeds into every plan that makes LLM calls (Mission Engine, Agents) and every plan that calls external APIs (Tools). It is not an operational plan — it does not do work. It makes everything else work better.

---

## The 8 Sub-Sections — Priority and Purpose

### 1. Profile (HIGH PRIORITY — wire first)
- Shows: name, email, avatar (initials)
- Reads from: `GET /auth/me`
- Writes to: `PUT /auth/me`
- Connects to: Auth Plan (profile data), Topbar (display name)

### 2. API Access / API Keys (HIGHEST PRIORITY)
This is the single most impactful settings screen.

**LLM Keys:**
- `GROQ_API_KEY` — fast, free tier (14,400 req/day). Primary LLM.
- `GEMINI_API_KEY` — fallback LLM.
- `OPENAI_API_KEY` — optional premium LLM.

**Tool Keys:**
- `SERPER_API_KEY` — powers `web_search` tool (2,500 free searches/month)
- `GOOGLE_PLACES_API_KEY` — powers `maps_api` tool ($200 free credit/month)

**How these keys flow:** User saves Groq key → stored encrypted in MongoDB → when Mission runs, executor loads user's keys → LLM chain uses `user.groq_api_key` first → fallback to Gemini → fallback to Ollama.

**Display rule:** After storage, show only last 4 chars (e.g., `sk_...4821`). Never return full key in API response.

### 3. Security (MEDIUM PRIORITY)
- Password change: `PUT /auth/password` with `{current_password, new_password}`
- Active sessions list: show devices with last active time
- Revoke a session: `DELETE /auth/sessions/{session_id}`

### 4. Preferences (LOW PRIORITY)
- UI theme (light/dark), language, date format, notification toggles
- Stored in MongoDB user profile

### 5. Workspace Settings (DEFER)
- Team members, roles, permissions
- Requires multi-user architecture. Single-user system for now. Show as "Coming Soon."

### 6. Billing (DEFER — DO NOT BUILD)
- System is free tier only. No payment processor.
- Show "Free Plan" with a note "Bring your own API keys."

### 7. Help & Support (LOW PRIORITY)
- Static links to docs, GitHub, support email
- No API needed. Pure static content.

### 8. Logout (DONE)
- Already calls `onLogout` prop which calls `doLogout()` → `POST /auth/logout`

---

## How API Keys Flow Through the System

```
User stores keys in Settings
         │
         ▼ stored encrypted in MongoDB user.api_keys
         │
    Mission starts
         │
         ▼ Executor loads user.api_keys from MongoDB
         │
    ┌────┴────────────────────────────────┐
    │                                     │
    ▼                                     ▼
LLM Chain                          Tool Calls
Groq key → fast model              Serper key → web_search
Gemini key → fallback              Google Places → maps_api
Ollama → last fallback             (uses key or falls back to OSM)
```

---

## Database

**MongoDB Atlas, `users` collection, `api_keys` subdocument:**

```json
{
  "api_keys": {
    "groq_api_key": "enc:AES256:...",
    "gemini_api_key": "enc:AES256:...",
    "openai_api_key": "enc:AES256:...",
    "serper_api_key": "enc:AES256:...",
    "google_places_api_key": "enc:AES256:..."
  }
}
```

Keys encrypted at rest using Fernet symmetric encryption (key stored as env var `ENCRYPTION_KEY`). Never stored in plaintext. Never returned in plaintext after initial submission.

---

## API Endpoints

```
GET  /settings/api-keys
  returns: { groq: "sk_...4821", gemini: "AI...f3c2", serper: null, ... }
  (masked — last 4 chars only, null if not set)

PUT  /settings/api-keys
  body:    { groq_api_key?, gemini_api_key?, openai_api_key?, serper_api_key?, google_places_api_key? }
  returns: { updated: true }

DELETE /settings/api-keys/{provider}
  removes that specific key
  returns: { deleted: "groq" }

PUT  /auth/password
  body:    { current_password, new_password }
  returns: { updated: true }
  errors:  401 wrong current password | 422 new password too weak
```

---

## How Settings Connects to Every Other Plan

| Plan | How Settings feeds it |
|------|-----------------------|
| Auth | Profile section extends `/auth/me` |
| Mission Engine | Executor reads `user.api_keys` before every run to get LLM keys |
| Agents | Agent's `model` field overrides the user's default LLM (uses same key) |
| Tools | `serper_api_key` → `web_search` tool. `google_places_api_key` → `maps_api` tool |
| Observability | LLM Usage tab shows which providers were used (affected by which keys are set) |
| Notifications | Preferences sub-section controls which notification types the user receives |

---

## Build Order

**Phase 1 (alongside Mission Engine):**
- `GET /settings/api-keys` + `PUT /settings/api-keys` endpoints
- Wire `ViewApiAccess` to these endpoints
- Executor updated to load user API keys before LLM calls

**Phase 3 (Polish):**
- Wire `ViewSettingsProfile` to `GET/PUT /auth/me`
- `PUT /auth/password` + wire Security view
- Fix `Topbar.jsx` hardcoded name → read from auth user
- Fix `Topbar.jsx` hardcoded date → `new Date().toLocaleDateString()`
