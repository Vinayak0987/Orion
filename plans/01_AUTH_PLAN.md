# 01 — AUTH & USER IDENTITY PLAN

---

## What It Is and Why It Exists in the System

Auth is the foundation of the entire system. Before any agent runs, before any mission starts, before any tool is called — the system must know **who** is doing it.

Every agent, department, mission, tool, and API key in the system belongs to a specific user. Auth is what makes ownership possible. Without Auth, there is no concept of "your agents" vs "someone else's agents." The system would be a single shared pile of data with no isolation.

**Role in the whole system:** Auth provides `user_id` to every other plan. The agents table has `created_by = user_id`. The missions table has `created_by = user_id`. The API keys in Settings are tied to `user_id`. The departments, documents, memory entries — everything traces back to a user through this plan.

---

## How It Works

### Sign Up
```
User submits {full_name, email, password}
→ Validate: email format, password strength (8+ chars, upper, lower, digit)
→ Hash password with Argon2id
→ Store in MongoDB Atlas users collection
→ Mint JWT access token (15 min TTL, signed with JWT_SECRET)
→ Set httpOnly refresh cookie (30 day TTL)
→ Return {access_token, user: {id, email, full_name}}
```

### Login
```
User submits {email, password}
→ Find user by email in MongoDB
→ Verify password with Argon2id
→ Mint JWT access token
→ Set httpOnly refresh cookie
→ Return {access_token, user}
```

### Session Restore (App Load)
```
Browser sends refresh cookie automatically on POST /auth/refresh
→ Verify refresh token
→ Mint new access token
→ Return {access_token, user}
→ Frontend stores access token in memory (not localStorage — XSS safe)
```

### Logout
```
POST /auth/logout
→ Invalidate refresh token on server
→ Clear httpOnly cookie
→ Frontend clears access token from memory
```

### Authenticated Requests
```
Every protected endpoint expects: Authorization: Bearer {access_token}
→ Middleware verifies JWT signature and expiry
→ Extracts user_id → available to route handler
```

---

## Frontend Flow

```
App loads
  └─► IntroScreen (plays once per browser session)
        └─► Has user seen landing? No → LandingPage
              └─► User clicks "Get Started" → /signup
                    └─► SignUpForm → POST /auth/signup → success → /
            Yes or returning user → /login
              └─► restoreSession() → POST /auth/refresh
                    Success → PlatformApp (user logged in silently)
                    Fail → /login → SignInForm → POST /auth/login → /
```

**OAuth buttons (Google, GitHub):** Currently stubbed. Show the message "Google sign-in isn't available yet — use email for now." Do not attempt OAuth flow until explicitly implemented per provider.

---

## Database

**MongoDB Atlas (free M0 tier)**
Collection: `users`

```json
{
  "_id": "uuid4",
  "email": "user@example.com",
  "full_name": "Abhishek M",
  "password_hash": "$argon2id$...",
  "created_at": "2026-10-15T01:00:00Z",
  "updated_at": "2026-10-15T01:00:00Z"
}
```

**Why MongoDB and not SQLite?**
User/auth schema evolves independently from agent/mission data. MongoDB allows flexible schema changes to user profiles (adding preferences, billing info, team memberships later) without migrating the SQLite agent database.

---

## API Endpoints

```
POST /auth/signup
  body:    { full_name, email, password }
  returns: { access_token, user: {id, email, full_name} }
  errors:  422 email invalid | 409 email already registered

POST /auth/login
  body:    { email, password }
  returns: { access_token, user }
  errors:  401 invalid credentials

POST /auth/refresh
  cookie:  orion_refresh (httpOnly, sent automatically)
  returns: { access_token, user }
  errors:  401 invalid/expired refresh token

POST /auth/logout
  header:  Authorization: Bearer {token}
  returns: {}

GET  /auth/me
  header:  Authorization: Bearer {token}
  returns: { id, email, full_name, created_at }

PUT  /auth/me
  body:    { full_name?, email? }
  returns: updated user
```

---

## How Auth Connects to Every Other Plan

| Plan | How Auth feeds it |
|------|------------------|
| Settings | User profile data from `/auth/me`. API keys stored per `user_id`. |
| Mission Engine | Every mission has `created_by = user_id`. Mission list filtered by user. |
| Agents | Every agent has `created_by = user_id`. Agents scoped to user. |
| Departments | Every department has `created_by = user_id`. |
| Tools | Custom tools registered by `user_id`. API keys from Settings (tied to user). |
| Knowledge | Documents and memory entries scoped to `user_id` / `department_id`. |
| Approvals | Decisions resolved `by = user_id`. |
| Observability | Runs filtered by `user_id` so users only see their own traces. |
| Operations | Operations data filtered by `created_by = user_id`. |
| Notifications | Notifications sent to `user_id`. |

---

## What Is Not Built Yet

| Feature | Status |
|---------|--------|
| OAuth (Google, GitHub) | Stubbed. Needs per-provider implementation. |
| Password reset | Not implemented. `/auth/forgot-password` needed. |
| Email verification | Not implemented. |
| 2FA | Not implemented. |
| Team / workspace | Single user only. Multi-user is a future milestone. |

---

## Build Order

**Status: BUILT in `backend2/` + frontend complete.**

The auth system was originally built in the legacy backend and has now been
ported verbatim into the fresh `backend2/` mission-engine backend so one backend
serves both auth and missions:
- `backend2/app/auth/` — security.py, store.py, models.py, deps.py, router.py (ported)
- Config fields added to `backend2/app/config.py` (MONGODB_URI, JWT_SECRET, TTLs, cookie)
- Auth router registered in `backend2/app/main.py`; Mongo configured in lifespan
  (skipped if a test has already injected a mongomock client)
- `PUT /auth/me` added (profile edit) — the one endpoint the legacy lacked
- Frontend `authApi.js` now points at the v2 backend (port 8081)
- 10 offline auth tests pass via mongomock (`tests/test_auth.py`)
- Full backend2 suite: 26 passed

Remaining wiring (deferred to later phases, not blocking):
1. Wire `ViewSettingsProfile` → `GET/PUT /auth/me` (display + edit real user)
2. Remove hardcoded `"Abhishek"` from `Topbar.jsx` → read from auth user object
3. Remove hardcoded date from `Topbar.jsx` → use `new Date()`
4. Replace `'default-user'` in the mission engine with the real `user_id` from
   the JWT (connects auth ownership to missions — a small, well-scoped change)
