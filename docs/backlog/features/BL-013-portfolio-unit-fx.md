# BL-013 — Portfolio AVG COST and PRICE in session currency

| Field | Value |
|-------|--------|
| **ID** | `BL-013` |
| **Title** | Holdings table Avg cost & Price follow chosen display currency |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | BL-001 dashboard; BL-003 session currency |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |

---

## Review findings

On `/portfolio`, **Market value** and **PnL** already convert via `marketValueDisplay` / `pnlDisplay` + session `displayCurrency`. **Avg cost** and **Price** do not:

```tsx
// HoldingsTable.tsx
{avg == null ? "—" : `${formatPrice(avg)} ${line.currency}`}
{price == null ? "—" : `${formatPrice(price)} ${line.currency}`}
```

`line.avgCost` / `line.price` are **native** (stock VND, crypto USD). Domain `apply_fx` sets `market_value_display`, `cost_basis_display`, `pnl_display` but **never** `avg_cost_display` / `price_display`. `PortfolioLine` has no those fields.

Edit-holding modal already converts avg cost into session currency for the form (`convertToDisplay`) — table display was left native.

---

## 1. Problem / user value

Users pick VND / USD / EUR in the header and expect **every money column** on the holdings table to match. Native-only Avg cost / Price makes mixed stock+crypto portfolios unreadable.

---

## 2. User story

As an **authenticated investor**, I want **Avg cost and Price in my chosen display currency**, so that **I can compare positions without mental FX**.

---

## 3. Scope

### In scope

- Holdings table **Avg cost** and **Price** columns show converted amounts in session currency (same as Market value / PnL)
- Prefer **API fields** so other clients stay consistent:
  - add `avgCostDisplay` and `priceDisplay` on portfolio line DTO
  - `apply_fx` fills them with the same rate used for market value
- FE: consume display fields; if missing, fall back to `convertToDisplay(avgCost|price, line.currency)`
- Suffix/label uses **display currency** when conversion succeeded; otherwise native + existing “rate unavailable” pattern
- Unit tests: domain `apply_fx` sets the new fields; FE table uses display currency

### Out of scope

- Changing how cost is **stored** (still native VND/USD)
- Changing the add/edit form (already session-currency)
- Totals cards (already display currency)
- Watchlist

---

## 4. Behaviour

### Happy path

1. User has VNM (VND) and BTC (USD). Session currency = EUR.
2. Table Avg cost / Price / Market value / PnL all show EUR amounts.
3. Switching header currency re-fetches `/api/portfolio?displayCurrency=` and columns update.

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| FX missing | Show native `avgCost`/`price` + native currency; do not invent a rate |
| Missing price | Price column `—`; avg cost still converts if FX allows |
| Same native as display | Identity conversion; still 2-decimal format (BL-012) |

### UX notes

- Route: `/portfolio` holdings table
- Column headers stay “Avg cost” / “Price” (currency is on the value, not a second header switcher)

---

## 5. Acceptance criteria

- [ ] **AC1** When FX can convert the line, Avg cost is shown in session `displayCurrency`, not `line.currency`.
- [ ] **AC2** When FX can convert and a quote exists, Price is shown in session `displayCurrency`.
- [ ] **AC3** Market value / PnL behaviour from BL-001 is unchanged.
- [ ] **AC4** API line includes `avgCostDisplay` and `priceDisplay` (string Decimals or null) after `apply_fx`.
- [ ] **AC5** FX missing → native amounts + native currency code; no crash.
- [ ] **AC6** Unit tests cover apply_fx new fields and table/helper conversion.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source | Existing portfolio GET + stored FX |
| API change | Additive fields on line DTO |
| Auth | Cognito (existing) |
| Caching | Unchanged |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `HoldingsTable.tsx`, `lib/portfolio.ts` types, tests |
| Backend | `domain/models.py` (`PortfolioLine`), `domain/fx_math.py` (`apply_fx`), `api/portfolio.py` `_line_to_dict`, domain tests |

---

## 8. Dependencies & risks

- Depends on: BL-003 rates; BL-001 table
- Overlap: BL-012 formatters, BL-014 dashboard layout — keep this BL to **columns + DTO fields**
- Risk: qty × converted price may differ from converted market value by 1 ulp — display-only; do not recompute PnL from converted unit prices

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | FE-only vs API fields | resolved | Additive API fields + FE fallback |
| 2 | Form already converts? | resolved | Yes; this BL is table display |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Avg cost / Price ignore session currency | Convert like MV/PnL; add display fields |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach: Additive `avg_cost_display` / `price_display` on `PortfolioLine`; `apply_fx` fills them with the same SRC→DST rate as market value (qty not re-valued; PnL still MV−cost). API `_line_to_dict` emits `avgCostDisplay` / `priceDisplay`. Holdings table prefers those fields + session `displayCurrency`; if absent, `convertToDisplay` fallback; FX missing stays native + `line.currency`.
- PR / branch: `feat/BL-013-portfolio-unit-fx`
- Verification: `python -m pytest tests/unit/domain/test_fx_math.py tests/unit/domain/test_portfolio_math.py tests/unit/api/test_portfolio.py -q` (from `backend/`); `npm test` in `frontend/` (`unitPriceInDisplay` + `HoldingsTable`).
