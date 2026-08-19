# BL-012 — Configurable 2-decimal number formatting (app-wide)

| Field | Value |
|-------|--------|
| **ID** | `BL-012` |
| **Title** | Normalize displayed numbers to 2 decimal places, configurable |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | BL-001..004 money UI; `frontend/lib/utils.ts` formatters |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |

---

## Review findings

`frontend/lib/utils.ts` already formats money, but **not** to a fixed 2 decimals:

- `formatPrice` uses `fractionDigits()`: `< 0.01` → 6 places, `< 1` → 4 places, else 2
- `formatSigned` uses the same variable scale
- `formatPct` is already 2 decimals
- Quantity (`line.qty`) is dumped raw
- Backend `_dec_str` emits full Decimal strings (`format(d, "f")`) — FE then re-formats some fields and not others

Stakeholder asked: **whole system, 2 digits after the decimal, and make the digit count configurable.**

---

## 1. Problem / user value

Numbers jump between 2 / 4 / 6 fraction digits depending on magnitude, which looks inconsistent on markets, portfolio, and asset detail. One configurable default (2) should apply everywhere money and signed amounts are shown.

---

## 2. User story

As an **investor**, I want **prices, PnL, and other money amounts to always show 2 decimal places**, so that **tables and charts are easy to scan**. I want the digit count **configurable** so we can change it later without hunting call sites.

---

## 3. Scope

### In scope

- Single source of truth for display fraction digits:
  - Constant default **`2`**
  - Override via `NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS` (integer 0–8, invalid → 2)
- All **user-visible money / signed / percent** formatting goes through this config (`formatPrice`, `formatSigned`, `formatPct`, and any new helpers)
- Apply to: markets quotes, portfolio table/cards/pie labels, asset detail price, FX readouts, sparklines tooltips if they format numbers
- Keep thousands separators (`en-US` locale) unless a call site already uses another locale
- Unit tests: default 2; env override; invalid env → 2; 0 digits; percent still appends `%`

### Out of scope

- Changing **stored** precision (holdings qty / avgCost stay Decimal strings)
- Rounding in domain math / Dynamo
- Per-currency digit tables (VND = 0) — one global config only
- Compact notation (`1.2M`) — not requested
- Backend JSON still may be full-precision strings; **display** is FE’s job

---

## 4. Behaviour

### Happy path

1. Default config = 2.
2. `formatPrice(1234.5)` → `1,234.50`
3. `formatPrice(0.000012)` → `0.00` (no longer 6 digits)
4. `formatSigned(-12.3)` → `-12.30`
5. `formatPct(1.234)` → `+1.23%` (or equivalent existing sign rules, but 2 digits)
6. Setting `NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS=0` shows `1,235` (rounded).

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| `NaN` / non-finite | Existing behaviour (do not crash); prefer `—` only if a call site already does |
| Null API fields | Still `—` |
| Qty | Format with the same digit config **unless** it is a count that already displays as integer-only; if qty has fractions, 2 decimals |
| Invalid env | Fall back to 2; do not throw at import |

### UX notes

- No new UI control in this BL (config is env/constant, not a header switcher)
- Visual change: small-cap crypto prices will look flatter (`0.00`) — accepted

---

## 5. Acceptance criteria

- [ ] **AC1** Default fraction digits are **2** for `formatPrice` / `formatSigned` / `formatPct`.
- [ ] **AC2** Digit count is read from one helper/module, overridable by `NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS`.
- [ ] **AC3** Markets quotes, portfolio money columns/cards, and asset detail price use the shared formatters (no ad-hoc `toFixed` / `toLocaleString` for money).
- [ ] **AC4** Existing tests updated; new tests cover default, override, invalid env.
- [ ] **AC5** Domain/API payloads remain full precision; only display rounding changes.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | FE formatter module + env |
| New APIs | None |
| Auth | n/a |
| Caching | n/a |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `lib/utils.ts` (or new `lib/number-format.ts` consumed by utils), call sites that format money, `*.test.ts` |
| Backend | None required |
| Docs | This file; optional README env note |

---

## 8. Dependencies & risks

- Depends on: none
- Risk: overlap with BL-013 (portfolio table) — both touch `HoldingsTable`; merge `formatPrice` first or keep this BL to the formatter module only and let other BLs consume it
- **Merge hint:** land formatter module with stable exports `formatPrice` / `formatSigned` / `formatPct` so other branches keep compiling

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Default digits | resolved | 2 |
| 2 | Config mechanism | resolved | `NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS` + default 2 |
| 3 | Per-currency (VND 0) | resolved | Out of scope |
| 4 | Round vs truncate | resolved | Standard half-up via `toLocaleString` / `toFixed` |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | 2 decimals whole system, configurable | Default 2; env override |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach:
- PR / branch: `feat/BL-012-number-format`
- Verification:
