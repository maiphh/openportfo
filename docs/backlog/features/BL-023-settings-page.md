# BL-023 — Settings page with sub-tabs (General + Avatar)

| Field | Value |
|-------|--------|
| **ID** | `BL-023` |
| **Title** | `/settings` page, Open WebUI-style sub-tab layout; General + Avatar tabs |
| **Priority** | `P0` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Luna implementer |
| **Requested by** | Product |
| **Related PRD / sprint** | sprint-06; depends on BL-020 (sidebar nav entry), BL-022 (DiceBear lib) |
| **Created** | 2026-08-23 |
| **Ready date** | 2026-08-23 |
| **Done date** | 2026-08-23 |

---

## 1. Problem / user value

No settings page exists. Product wants a dedicated **`/settings` page with a sub-tab for each settings group** (layout reference: **Open WebUI** settings — vertical tab rail on the left, content pane on the right). Tabs in scope across the batch: **General (system/user settings)**, **FX rates** (BL-026), **Chatbot** (BL-025), **Avatar** (this item).

---

## 2. User story

As a **user**, I want **a settings page with one tab per concern**, so that **I can find and change any preference in a predictable place**.

---

## 3. Scope

### In scope

- New route `/settings` (static-export safe), **tab shell** styled after Open WebUI: left vertical tab list (icon + label), right content pane, deep-linkable via `?tab=` query param (default `general`).
- **General tab** — per-user settings persisted via existing `PUT /api/settings`: preferred currency, email opt-in, news keywords (chips/list editor). Server-side so they follow the account.
- **Avatar tab** — DiceBear avatar control: style picker (curated set of DiceBear styles), background color, seed (regenerate/randomize + custom text), live preview using the avatar lib from BL-022. Persist per-user **server-side** (extend `UserProfile` + `PUT /api/settings` — SA to define exact fields, e.g. `avatarStyle`, `avatarSeed`, `avatarColor`) with localStorage-free behavior; default = deterministic seed from userId/email when unset.
- Tab visibility rules: General + Avatar visible to all signed-in users; FX + Chatbot tabs per BL-025/026 (admin-gated where the API is admin-only). Signed-out users see a sign-in prompt.
- Sidebar gets a "Settings" entry (icon) linking `/settings` (wired in BL-020's sidebar; if BL-020 not yet merged, add entry as part of integration).

### Out of scope

- Chatbot tab (BL-025), FX tab (BL-026), admin page (BL-024), uploaded photos.

---

## 4. Behaviour

### Happy path

1. Navigate to `/settings` → General tab active, loads current profile settings.
2. Change currency/email opt-in/keywords → save via API, success feedback.
3. Avatar tab → pick style/color/seed → live preview updates → save → avatar everywhere (sidebar, chat) updates.

### Edge cases / errors

- API error → inline error, keep dirty form state.
- Unsigned → sign-in prompt instead of forms.
- Invalid tab in `?tab=` → fall back to `general`.

---

## 5. Acceptance criteria

- [x] `/settings` renders tab shell; tabs switch content; `?tab=` deep links work.
- [x] General tab round-trips preferredCurrency/emailOptIn/newsKeywords via `/api/settings`.
- [x] Avatar tab previews and persists style/seed/color; other surfaces render the saved avatar.
- [x] Unit tests: tab switching + deep link, General form save/error paths, avatar preview + save.
- [x] Suite green.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | `UserProfile` (extended) via `/api/settings` |
| New / changed APIs | extend `PUT /api/settings` + `GET /api/auth/me` with avatar fields (backend change, see BL-024/025 batch) |
| Auth required? | yes for edits |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | new `app/settings/page.tsx`, `components/settings/*` (SettingsShell, GeneralTab, AvatarTab), sidebar entry |
| Backend API | `PUT /api/settings`, `GET /api/auth/me` avatar fields; `UserProfile` + repos (both adapters) |
| Docs / tests | FE tab/form tests; BE settings/profile tests |

---

## 8. Dependencies & risks

- Depends on: BL-022 (avatar lib with style/color params), BL-020 (sidebar entry point).
- Risks: repo field additions must hit BOTH Dynamo and in-memory adapters + profile serialization.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Avatar field names + DiceBear style shortlist | resolved | Nullable `avatarStyle` / `avatarSeed` / `avatarColor`; use the existing eight-style allowlist in `lib/avatar.ts`. Exact validation is in the sprint-06 architect handoff. |
| 2 | Should quick-prefs modal (BL-021) link to this page? | resolved | Yes. Retain quick theme/language/currency access, remove nested FX, and link to `/settings` and `/settings?tab=fx`; signed-in currency also persists to the profile. |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-23 | Batch created | — |
| 2026-08-23 | Solution architecture resolution | Static `useSearchParams` subtree is Suspense-wrapped; raw avatar fields are nullable/server-backed; one shared auth profile propagates saves; quick settings links to the page. See sprint-06 `ARCHITECT_HANDOFF.md`. |
| 2026-08-23 | Implementation and acceptance | Implemented by Luna; all automated gates passed and final Solution Architect review approved BL-023. |
