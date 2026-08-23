# BL-009 — Live SearchDialog (`/api/assets/search`)

| Field | Value |
|-------|--------|
| **ID** | `BL-009` |
| **Title** | Header search uses live asset search, not mock universe |
| **Priority** | `P1` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | BL-002 click-through; holdings search already live |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |

---

## 1. Problem / user value

Header `SearchDialog` filters `SEARCH_UNIVERSE` (US/demo names). Holdings add-modal already calls `GET /api/assets/search`. Global search must use the same live catalog.

---

## 2. User story

As an **authenticated investor**, I want **header search to find real VN stocks and CoinGecko crypto**, so that **I can open the same assets I can add to the portfolio**.

---

## 3. Scope

### In scope

- Debounced `GET /api/assets/search?q=&type=` (existing, auth required)
- Search **both** `stock` and `crypto` (two parallel requests; API requires `type`)
- Empty query: prompt “Type to search” — **do not** dump mock universe
- Results: symbol, name, type; `AssetLink`; optional price only if already on the payload (search DTO may lack quotes — omit value/chg% rather than mock)
- Unauthenticated: Sign in empty state (no mock)
- Loading / no matches / error
- Remove `SEARCH_UNIVERSE` usage from SearchDialog; delete export if unused
- Reuse `searchAssets` in `lib/portfolio.ts` or extract shared helper
- Unit tests: debounce/query building, empty q does not fetch, 401 path

### Out of scope

- New `type=all` backend param (optional additive OK but not required)
- Public unauthenticated search
- Changing holdings modal (already live)

---

## 4. Behaviour

### Happy path

1. Signed-in user opens Search.
2. Types `VNM` / `btc`.
3. Debounced dual search → results with type label → click opens detail.

### Edge cases

| Case | Behaviour |
|------|-----------|
| q blank | No request; helper copy |
| 401 | Sign in CTA |
| One type fails | Show the other + soft error |
| No matches | “No matches” (not “No mock matches”) |

---

## 5. Acceptance criteria

- [x] **AC1** SearchDialog does not read `SEARCH_UNIVERSE`.
- [x] **AC2** Queries hit `/api/assets/search` for stock and crypto.
- [x] **AC3** Empty query does not fetch.
- [x] **AC4** Unauthenticated: no mock list.
- [x] **AC5** Results use `AssetLink` with correct `assetType`.
- [x] **AC6** Tests cover client behaviour.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| API | `GET /api/assets/search?q&type` |
| Auth | Required |
| Debounce | ~250ms |

---

## 7. Affected surfaces

| Layer | Paths |
|-------|--------|
| Frontend | `SearchDialog.tsx`, `lib/portfolio.ts` or `lib/asset-search.ts`, `mock-data.ts`, tests |
| Backend | None required |

---

## 8. Dependencies & risks

- Overlap with BL-006 auth CTA
- Holdings modal already has a search implementation — **reuse**, do not fork

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Dual type | resolved | Parallel stock + crypto |
| 2 | Quotes in results | resolved | Optional; no mock prices |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Mock universe | Replace with live search |

---

## 11. Implementation notes

- Approach: FE-only. Header `SearchDialog` no longer reads `SEARCH_UNIVERSE` (export removed). After mount it reads `artryx.accessToken`, debounces ~250ms, aborts in-flight, and calls `searchLiveCatalog` — two parallel `searchAssets` GETs (`/api/assets/search?q&type=stock|crypto`). Empty `q` skips fetch and shows “Type to search”. Unauthenticated / 401 shows Sign in empty state (token paste CTA, no mock list). Results: symbol, name, type via `AssetLink` (`assetId` or symbol); price/chg% only if already on the payload. One type failing keeps the other + soft error. Holdings modal unchanged.
- PR / branch: `feat/BL-009-live-search-dialog`
- Verification: `cd frontend; npx vitest run lib/asset-search.test.ts lib/portfolio.test.ts components/SearchDialog.test.tsx` (empty q no fetch, `assetSearchQuery` / dual type, 401 sign-in). Full `npx vitest run` in `frontend/`.
### Current implementation note (Sprint 05)

The app now reads the canonical `openportfo.accessToken`; historical
`artryx.*` references below describe the pre-rebrand shell.
