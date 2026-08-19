# BL-003 — Session display currency (app-wide)

| Field | Value |
|-------|--------|
| **ID** | `BL-003` |
| **Title** | Session display currency + read-only FX visibility |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | PRD M10b, FR-FX*; sprint 06 FX; consumed by BL-001, BL-002 |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |
| **Implement when** | After additional backlog features are clarified (stakeholder hold) |

---

## 1. Problem / user value

Users want to view the whole app in one **display currency**. Choice must stick for the **session** (localStorage), and every money surface should follow it. Conversion uses **admin-stored FX rates** (not user-editable rates, not live provider calls from the browser).

---

## 2. User story

As an **authenticated investor**, I want to **pick VND, USD, or EUR in the header**, so that **portfolio, asset detail, markets, and holding forms all show amounts in that currency**, using the system’s last stored exchange rates.

---

## 3. Scope

### In scope

- **This BL owns** app-wide display currency; **BL-001 / BL-002 consume** the shared session context (do not invent separate switchers)
- Header **currency control** next to language (`LanguageSelect`-style)
- Supported codes: **`VND` | `USD` | `EUR`**
- Persist selection in **session/localStorage only** (not Cognito / profile in this BL)
- **Default:** `VND` when no stored session value
- Conversion source: **`GET /api/fx/rates`** stored rates (admin-refreshed elsewhere); APIs already accept `displayCurrency` / `currency`
- **UX extras:**
  - Show **current relevant rate + `asOf`** (tooltip or small label near switcher)
  - **Read-only rates panel** for authenticated users (view stored map + status/`asOf`; **no** user refresh)
- Shared FE **currency context/hook** so any money UI can subscribe
- Surfaces that **must** apply session currency:
  - Portfolio totals / PnL / pie (BL-001)
  - Asset detail price + chart (BL-002)
  - Markets quotes / heatmap **display values** (where amounts are shown)
  - Add/edit holding **cost input** label/units (BL-001 conversion-on-save rules unchanged)
  - Future money UI via the shared context

### Out of scope

- User-editable / custom FX rate overrides
- User-triggered provider refresh (remains **admin** `POST /api/admin/fx/refresh`)
- Persisting preferred currency to user profile
- Adding currencies beyond VND/USD/EUR in this BL
- Changing how admin seeds/refreshes the rate store (unless a missing EUR rate blocks display — then document dependency)

---

## 4. Behaviour

### Happy path

1. User opens app (authenticated where APIs require it).
2. Header shows currency control; default **VND** if first visit.
3. User selects **USD** or **EUR** → saved to localStorage → context updates.
4. Portfolio, asset detail, markets money figures re-request or re-format with the new currency.
5. User can open **read-only rates panel** to see stored pairs, status, `asOf`.
6. Hover/focus on switcher (or adjacent label) shows e.g. rate used for native→display + `asOf`.

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| FX store empty / rate missing for pair | Keep native amounts visible; display conversion null/omitted; show `fx.status` / “rate unavailable” — do not crash |
| Stale rates | Still convert using last good stored rates; show status/`asOf` so user knows freshness |
| Unauthenticated | Switcher may still set local preference for when they sign in; money APIs remain auth-gated as today |
| Invalid stored localStorage value | Fall back to **VND** |
| EUR (or other) not in stored map | Same missing-rate behaviour; rates panel shows what’s available |

### UX notes

- Placement: header, beside language
- Rates panel: modal, drawer, or simple `/settings`-adjacent panel — eng choice; must be **read-only**
- Do **not** duplicate a second currency dropdown on portfolio/detail once global exists

---

## 5. Acceptance criteria

- [ ] **AC1** Header currency control offers **VND, USD, EUR**.
- [ ] **AC2** Selection persists in **localStorage/session** and restores on reload.
- [ ] **AC3** Default currency is **VND** when no valid stored value.
- [ ] **AC4** Changing currency updates **portfolio** money displays (via shared context + API `displayCurrency`/`currency`).
- [ ] **AC5** Changing currency updates **asset detail** price/chart display currency.
- [ ] **AC6** Markets quotes/heatmap **amount displays** follow session currency where values are shown as money.
- [ ] **AC7** Add/edit holding cost field is labeled in the **session currency** (storage remains native per BL-001).
- [ ] **AC8** Shared currency context/hook exists for future screens.
- [ ] **AC9** UI shows **rate + asOf** for the active conversion context (tooltip or small label).
- [ ] **AC10** Authenticated user can open a **read-only rates panel** fed by `GET /api/fx/rates` (no refresh button for normal users).
- [ ] **AC11** Missing/stale FX does not break pages; degraded native/partial display + visible status.
- [ ] **AC12** Admin FX refresh is **not** part of this BL’s user UI.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Rate source of truth | Dynamo/stored FX via `GET /api/fx/rates` |
| Who refreshes rates | Admin only (existing); out of this BL’s UI |
| Session store | localStorage key (e.g. `artryx.displayCurrency`) |
| Profile persist | No |
| Consumer APIs | Portfolio `displayCurrency`; asset detail/history `currency`; holdings cost conversion uses stored FX on write (BL-001) |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | Header currency select; currency context/provider; rates panel; wire BL-001/002/markets |
| Backend | Existing FX read/convert; no new provider calls from user path |
| Docs | Cross-link BL-001 / BL-002 to consume BL-003 |

---

## 8. Dependencies & risks

- **Depends on:** Admin having refreshed rates at least once for needed pairs (esp. EUR)
- **Risks:** EUR absent from store; markets heatmap may be %-based — only money amounts must convert; clarify % tiles stay %

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Meaning of “select exchange rate” | resolved | Display currency; rates from admin store |
| 2 | Ownership vs BL-001 | resolved | BL-003 owns app-wide; BL-001 consumes |
| 3 | Placement | resolved | Header next to language |
| 4 | Default | resolved | VND |
| 5 | Extra FX UX | resolved | Rate+asOf label + read-only rates panel (no user refresh) |
| 6 | Surfaces | resolved | Portfolio, detail, markets money, holding cost, shared context |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Intake | User selects exchange/display currency; store in session; whole app applies |
| 2026-08-19 | Meaning | Display currency VND/USD/EUR; convert with stored admin FX |
| 2026-08-19 | Ownership | BL-003 owns global session currency; BL-001/002 consume |
| 2026-08-19 | UI | Header switcher; default VND; rate+asOf; read-only rates panel |
| 2026-08-19 | Surfaces | Portfolio, detail, markets amounts, holding cost, future via context |
| 2026-08-19 | Ready | Spec finalized; batch implement later |

---

## 11. Implementation notes (Eng fills after start)

- Approach: FE `CurrencyProvider` + `useDisplayCurrency` (localStorage `artryx.displayCurrency`, default VND). Header `CurrencySelect` next to language with rate/asOf label + read-only `FxRatesPanel` via `GET /api/fx/rates` (optional Bearer from `artryx.accessToken`). Markets quotes convert client-side with stored rates; heatmap stays %-only. Portfolio/asset detail/holding forms not in this tree yet — helpers (`displayCurrencyQuery`, `holdingCostLabel`) ready for BL-001/002.
- PR / branch: `execute-plan/6cc30007-pr-1-bl-003-session-currency`
- Verification: `cd frontend && npm test` (currency/fx/provider unit tests)
