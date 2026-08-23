# BL-026 — FX rates Settings tab (view + admin refresh)

| Field | Value |
|-------|--------|
| **ID** | `BL-026` |
| **Title** | FX rates tab in Settings: view stored rates, admin on-demand refresh |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Luna implementer |
| **Requested by** | Product |
| **Related PRD / sprint** | sprint-06 |
| **Created** | 2026-08-23 |
| **Ready date** | 2026-08-23 |
| **Done date** | 2026-08-23 |

---

## 1. Problem / user value

FX rates currently live in a header-adjacent modal (`FxRatesPanel`) with admin refresh — reached from the `CurrencySelect` dropdown that the sidebar redesign removes. Product wants FX as a **Settings tab**: view rates, allow refresh (admin).

---

## 2. User story

As a **user/admin**, I want **to see current FX rates and (as admin) trigger a refresh from Settings**, so that **I can trust displayed conversions**.

---

## 3. Scope

### In scope

- **FX tab** in `/settings` (visible to all signed-in users; refresh button admin-only): rate table (from existing `GET /api/fx/rates`), stale indicator, last-updated time, admin Refresh calling existing `POST /api/admin/fx/refresh` with result/error surfacing (502 handling shows previous rates + error).
- Reuse logic from `FxRatesPanel` (fetch, refresh, admin detection); retire `FxRatesPanel` + its header entry point once parity is reached (SA confirms fate).
- Default display currency control (admin, system-level) may surface here as a select if SA deems fit (it exists in `/api/admin/settings.defaultDisplayCurrency`).

### Out of scope

- New FX APIs; scheduled refresh changes; rate history.

---

## 4. Behaviour

### Happy path

1. Open Settings → FX tab → rates table renders with updated timestamp.
2. Admin clicks Refresh → success updates table (or failure keeps old rates + shows error detail).

### Edge cases / errors

- Non-admin sees no refresh control; API 403 never triggered from UI.
- Provider failure → 502 body's previous rates shown with error message.

---

## 5. Acceptance criteria

- [x] FX tab lists stored rates + freshness/updated time.
- [x] Admin refresh works and errors surface; non-admins get no refresh control.
- [x] `FxRatesPanel` retired or reduced to shared logic without dead code.
- [x] Unit tests: tab render (user vs admin), refresh success/failure paths; suite green.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | existing `/api/fx/rates`, `/api/admin/fx/refresh` |
| New / changed APIs | none |
| Auth required? | signed-in (refresh: admin) |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `components/settings/FxTab.tsx`, retire/absorb `components/currency/FxRatesPanel.tsx` |
| Backend API | none |
| Docs / tests | vitest FX tab tests; FxRatesPanel tests updated |

---

## 8. Dependencies & risks

- Depends on: BL-023 (tab shell).
- Risks: none significant — APIs exist.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Show admin defaultDisplayCurrency here or in Chatbot/System tab? | resolved | Neither in this batch. Keep the existing system field/API for compatibility; per-user preferred currency belongs General/quick settings. |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-23 | Batch created | — |
| 2026-08-23 | Solution architecture resolution | Build an in-page FX tab over shared CurrencyProvider state; admin-only refresh preserves previous rates on 502; delete `FxRatesPanel` and its nested quick-modal entry after parity. |
| 2026-08-23 | Implementation and acceptance | Implemented by Luna; freshness, retained-data errors, transport cleanup, and old-panel removal passed final Solution Architect review. |
