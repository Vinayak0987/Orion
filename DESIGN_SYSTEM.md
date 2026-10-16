# Orion Frontend — Design System Reference

> Durable reference. Every new tab/page/feature in the platform MUST follow
> this so the whole app stays visually consistent. When you build Agents,
> Tools, Knowledge, Operations, Observability, Command Center, Missions, etc.,
> reuse these exact primitives and classes.

---

## The look: Neumorphic (soft UI)

Base surface tone **`#eef1f6`**, light shadow `#ffffff`, dark shadow `#d4d9e4`.
Accent = indigo `#4f46e5`. Text inks: title `#334155`, body `#5b6678`,
muted `#8792a6`, faint `#9aa6b8`. Danger `#e11d48`, success `#16a34a`.

Every page wrapper uses the neu surface so shadows read.

---

## Where things live

- **Global CSS classes:** `frontend/src/index.css` (search "Neumorphic")
- **React primitives:** `frontend/src/components/views/settings/SettingsShared.jsx`
- **Toasts:** `frontend/src/components/ui/Toast.jsx` — `useToast()` → `toast.success/error/info`
- **Modal:** `frontend/src/components/ui/Modal.jsx` — reusable, plain dark backdrop (NO blur, NO glow/nebula)

---

## CSS classes (index.css)

| Class | Use |
|-------|-----|
| `neu-surface` | page/panel background (#eef1f6) |
| `neu-card` | raised panel (radius 22) |
| `neu-raised` | smaller raised block |
| `neu-card-hover` | raised card that lifts on hover (clickable cards) |
| `neu-inset` | pressed-in well (info blocks, sub-navs) |
| `neu-input` | inset input field (+ indigo focus ring) |
| `neu-btn` / `neu-btn-ghost` | raised neutral button, presses in on click |
| `neu-btn-primary` | **indigo gradient** button w/ colored glow + inset press |
| `neu-btn-danger` / `neu-btn-danger-solid` | destructive buttons |
| `neu-circle` | raised circular control (icons, FABs) |
| `neu-avatar-well` | inset ring framing a photo |
| `neu-toggle` (+`neu-toggle-on`, `neu-toggle-knob`) | switch |
| `neu-seg` (+`neu-seg-item`, `neu-seg-item-active`) | segmented control |
| `neu-chip` | soft raised pill |
| `neu-nav` (+`neu-nav-active`) | sidebar/nav items (hover-raise, inset active) |

Keyframes available: `toastIn`, `modalPop`.

---

## React primitives (SettingsShared.jsx)

Flat set (for white-card contexts): `SettingsCard`, `Row`, `Field`, `Select`,
`SegmentedControl`, `Toggle`, `Chip`, `IconTile`, `PrimaryButton`,
`OutlineButton`, `GhostButton`, `DangerButton`, `SettingsHeader`, `Tabs`.

**Neumorphic set (preferred, use these going forward):**
`neuShellCls`, `NeuSectionTitle`, `NeuField`, `neuInput`, `neuSelect`,
`NeuPrimaryButton`, `NeuGhostButton`, `NeuDangerButton`, `NeuIconButton`,
`NeuToggle`, `NeuSegmented`, `NeuChip`, `NeuRow`.

---

## Patterns to copy for every new page

```jsx
import { neuShellCls, SettingsHeader, NeuSectionTitle, NeuPrimaryButton,
         NeuField, neuInput, NeuRow, NeuChip } from "...settings/SettingsShared.jsx";
import { useToast } from "...ui/Toast.jsx";
import { Modal } from "...ui/Modal.jsx";

<div className={neuShellCls}>
  <div className="max-w-[940px]">
    <SettingsHeader title="X" subtitle="…" action={<NeuPrimaryButton>Save</NeuPrimaryButton>} />
    <div className="neu-card p-7"> …NeuRow / NeuField… </div>
  </div>
</div>
```

### Rules
1. **Page bg** = `neu-surface` (or `neuShellCls`).
2. **Cards** = `.neu-card` (raised). Info blocks inside = `.neu-inset`.
3. **Primary actions** (Save, Create, Submit) = `NeuPrimaryButton` (indigo gradient, presses in).
4. **Icons in rows**: plain icon next to label (gap-2.5), NOT a separate raised circle — keep icon+text as one unit. Standalone action icons = `neu-circle`.
5. **Every create/update/delete** fires a `toast` (success/error). No inline green/red banners.
6. **Redirects → modals.** Use the reusable `Modal` (dark backdrop, no blur, no glow).
7. **Honest states**: unbuilt features show `NeuChip` "Coming soon", never fake data.
8. Type scale: page title 23px semibold, section 15px semibold, body 13.5–14px.
9. Toggles = `NeuToggle`, segmented (theme-like) = `NeuSegmented`, dropdowns = `neuSelect`.

---

## Current status of Settings (reference implementation)

All 8 Settings tabs + the main sidebar + Topbar user dropdown are fully
neumorphic and wired to the backend. Use any Settings tab as a working template
when building new sections.

- Profile, Workspace → neu form + preview cards, avatar/logo wells
- API Access → neu provider rows, inset masked keys
- Security → neu rows + neu modal (password change)
- Preferences → neu segmented theme, neu selects, neu toggles
- Billing, Help (FAQ accordion + modals), Logout → all neu
- Sidebar → neu nav (icon+text unified, inset active)
- Topbar → user dropdown (Profile / Settings / Logout), real user, live date

---

## Backend reminders (so UI wiring stays consistent)

- Backend v2: `backend2/` on port **8081**. Run tests: `..\.venv\Scripts\python.exe -m pytest -q` from `backend2`.
- Frontend talks to it via `missionApi.js` (missions, settings keys) and `auth/authApi.js` (auth, profile, avatar, workspace).
- Data split: MongoDB Atlas (users, workspaces, members) · SQLite (missions, tasks, traces, agents, api keys) · ChromaDB (vectors) · Cloudinary (images/docs).
- API keys currently SQLite under `default-user`; preferences in localStorage. (Deferred: move to real user_id.)
