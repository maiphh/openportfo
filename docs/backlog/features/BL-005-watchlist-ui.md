# BL-005 — Watchlist CRUD UI

| Field | Value |
|-------|--------|
| **ID** | `BL-005` |
| **Title** | Watchlist page + add/remove (existing APIs) |
| **Priority** | `P1` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | Deferred from BL-001; sprint-03 watchlist APIs |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |

---

## 1. Problem / user value

Backend already has watchlist CRUD + cache-first quotes. Artryx has no UI, so users cannot save tickers to glance at without adding a holding.

---

## 2. User story

As an **authenticated investor**, I want **a watchlist of stocks and crypto I can add and remove**, so that **I can track names I do not (yet) hold**.

---

## 3. Scope

### In scope

- Route **`/watchlist`** + **Watchlist** nav item
- List items from `GET /api/watchlist` (price, currency, stale)
- **Add**: search via existing `GET /api/assets/search` (same pattern as holdings modal) → `POST /api/watchlist` `{ assetType, symbol, assetId }`
- **Remove**: `DELETE /api/watchlist/{assetType}/{symbol}`
- Session display currency for price (convert like markets quotes)
- `AssetLink` on symbol
- Empty, loading skeleton, error + retry
- Auth gate consistent with `/portfolio` (after BL-006: Hosted UI; until then existing token gate)
- Optional: **Watch** / **Unwatch** on asset detail if cheap (same APIs)

### Out of scope

- New backend endpoints
- Alerts / price thresholds
- Ordering / folders
- Public watchlists

---

## 4. Behaviour

### Happy path

1. Sign in → Watchlist in nav → `/watchlist`.
2. Empty: CTA **Add to watchlist**.
3. Search valid stock/crypto → add → row with quote.
4. Click symbol → asset detail.
5. Remove → row gone.

### Edge cases

| Case | Behaviour |
|------|-----------|
| Unauthenticated | Sign-in CTA; no data fetch |
| Duplicate add | 409 inline error |
| Missing quote | Show symbol; price `—`; stale/missing badge |
| Invalid asset | BE 400; show error |

---

## 5. Acceptance criteria

- [ ] **AC1** Authenticated user can open `/watchlist` and see their items.
- [ ] **AC2** Unauthenticated user cannot read/write watchlist data.
- [ ] **AC3** Add only search-resolved stock or crypto.
- [ ] **AC4** Duplicate add shows conflict error; list unchanged.
- [ ] **AC5** Remove deletes the row after 204.
- [ ] **AC6** Symbols use `AssetLink`.
- [ ] **AC7** Nav includes Watchlist.
- [ ] **AC8** Unit tests for API client + add/remove happy/409 paths.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| APIs | `GET/POST /api/watchlist`, `DELETE /api/watchlist/{type}/{symbol}`, `GET /api/assets/search` |
| Auth | Bearer required |
| Cache | Cache-first quotes (existing) |

---

## 7. Affected surfaces

| Layer | Paths |
|-------|--------|
| Frontend | `app/watchlist/page.tsx`, nav, watchlist components, `lib/watchlist.ts`, tests |
| Backend | None required |
| Static export | Add `app/watchlist/page.tsx` (static) |

---

## 8. Dependencies & risks

- Depends on: BL-001 search/auth patterns; BL-006 will replace token paste
- Do not block on BL-006 — reuse current auth helper

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | New APIs? | resolved | No |
| 2 | Detail Watch button | resolved | Optional if low cost |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Deferred from BL-001 | FE-only on existing watchlist APIs |

---

## 11. Implementation notes

- Branch: `feat/BL-005-watchlist-ui`
