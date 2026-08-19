# BL-008 — Admin FX refresh control

| Field | Value |
|-------|--------|
| **ID** | `BL-008` |
| **Title** | Admin “Refresh rates” on the FX panel |
| **Priority** | `P1` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | BL-003 read-only rates panel; `POST /api/admin/fx/refresh` |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |

---

## 1. Problem / user value

BL-003 shows stored FX rates but cannot trigger a provider fetch. Admins must hit the API manually. The panel should expose **Refresh rates** for **admin** users only.

---

## 2. User story

As an **admin**, I want to **refresh stored FX rates from the header rates panel**, so that **display currency conversion stays current**.

---

## 3. Scope

### In scope

- `FxRatesPanel`: **Refresh rates** button visible iff `GET /api/auth/me` `role === "admin"`
- Call `POST /api/admin/fx/refresh` with Bearer
- Success: replace panel data with returned rates; non-admin viewers still only GET
- Failure (502): keep previous rates; show `detail` / `lastRefreshError`
- Loading state on the button
- Non-admin / unauthenticated: no button (read-only as today)
- Unit tests: button gated on role; POST called; 502 keeps prior rates

### Out of scope

- Promoting users to admin in production UI (local debug `POST /api/debug/auth/make-admin` stays local-only)
- Changing FX provider
- Scheduling

---

## 4. Behaviour

### Happy path

1. Admin opens currency → rates panel.
2. Sees **Refresh rates**.
3. Click → provider fetch → table updates `asOf` / pairs.

### Edge cases

| Case | Behaviour |
|------|-----------|
| 403 | Hide button or show “admin only”; do not toast stack |
| 502 | Previous table remains; error text |
| Non-admin | No refresh control |

---

## 5. Acceptance criteria

- [ ] **AC1** Admin sees and can trigger `POST /api/admin/fx/refresh`.
- [ ] **AC2** Non-admin never sees the control.
- [ ] **AC3** Success updates the panel from the response.
- [ ] **AC4** Failure keeps last good rates + error.
- [ ] **AC5** Tests cover role gate + POST.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| APIs | `GET /api/auth/me`, `POST /api/admin/fx/refresh` |
| Auth | Admin role |

---

## 7. Affected surfaces

| Layer | Paths |
|-------|--------|
| Frontend | `FxRatesPanel.tsx`, `lib/fx.ts`, CurrencyProvider optional, tests |
| Backend | None required |

---

## 8. Dependencies & risks

- Depends on: BL-003 panel; profile `role`
- Local admin: existing debug promote endpoint

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Who can refresh | resolved | `role=admin` only |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Complements BL-003 | Admin button on same panel |

---

## 11. Implementation notes

- Approach: Client `FxRatesPanel` loads `GET /api/auth/me` after open and shows **Refresh rates** only when `role === "admin"`. Click POSTs `/api/admin/fx/refresh` with Bearer (`lib/fx.ts` `refreshFxRates`). Success replaces session rates via `CurrencyProvider.replaceRates` (panel table + conversions). 502 keeps the previous table and shows `detail` / `lastRefreshError`. 403 hides the button (inline “Admin only”, no toast). Non-admin / unauthenticated stay read-only. Rate cells still use shared `formatPrice` (BL-012).
- PR / branch: `feat/BL-008-admin-fx-refresh`
- Verification: `cd frontend; npx vitest run lib/fx.test.ts components/currency` — 15 passed (role gate, POST + replace, 502 keeps prior rates).
