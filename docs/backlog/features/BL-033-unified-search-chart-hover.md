# BL-033 — Unified asset search + portfolio value chart hover/overflow

| Field | Value |
|-------|--------|
| **ID** | `BL-033` |
| **Title** | Unified asset search + portfolio chart hover/overflow |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (BA)** | Eng |
| **Owner (Eng)** | Eng |
| **Requested by** | User 2026-09-12 |
| **Related PRD / sprint** | FR-S1/S2, FR-W2, FR-H2, FR-P (portfolio chart BL-014) |
| **Created** | 2026-09-12 |
| **Ready date** | 2026-09-12 |
| **Done date** | |

---

## 1. Problem / user value

Two search UXs exist: sidebar `SearchDialog` searches both stock+crypto in parallel, while `AddWatchlistModal` and `HoldingFormModal` force the user to pre-pick `stock|crypto` with toggle buttons. Users must know the asset class before searching, which is friction and inconsistent.

Portfolio value chart (`PortfolioValueChart`) is a static SVG with no hover value inspection, and axis/header text overflows/clips under the component (middle-anchored edge labels exceed the 640 viewBox; header value+delta can overflow on narrow cards).

## 2. User story

As an **investor**, I want **one search box that finds both VN stocks and crypto**, so that **I don't have to pick a type first**.
As an **investor**, I want to **hover the portfolio value chart to see date+value**, with **no clipped text**, so that **history is readable**.

---

## 3. Scope

### In scope

- `AddWatchlistModal`: remove stock/crypto toggle, search both via `searchLiveCatalog`, show type badge per hit.
- `HoldingFormModal` create mode: same unification; edit/prefill locked paths unchanged.
- `PortfolioValueChart`: hover tooltip (date + value), crosshair/dot, fix axis-label overflow (start/end anchors), fix header wrap.
- Focused Vitest coverage updates.

### Out of scope

- Backend `/api/assets/search` change (still `type=stock|crypto` per call; frontend fans out in parallel).
- New chart library, SSR, API Gateway, market-provider changes.

---

## 4. Behaviour

### Happy path

1. Open Watchlist → Add → type `btc` → see both `BTC Crypto` and any stock matches in one list with `Crypto`/`Stock` badges; pick one → Add.
2. Dashboard → Add holding → type `VNM` → see unified hits with badges; pick → qty/cost → submit.
3. Dashboard → Portfolio value chart → hover/touch line → tooltip shows date + formatted value; axis labels fully visible, header wraps.

### Edge cases / errors

- One search type fails → show soft warning, keep other type hits (parity with SearchDialog).
- Both fail → error copy, no crash.
- 401 → auth error path preserved.
- Chart <2 points → existing empty copy; hover disabled.
- Narrow viewport → tooltip clamps inside card, labels don't clip.

### UX notes

- Screens: `/watchlist`, dashboard (`/`), asset detail prefill unchanged.
- Placeholder: `e.g. VNM, FPT, BTC, ethereum`.
- Chart tooltip: `role="status"` live region, keyboard focusable dots via arrow keys (nice-to-have: mouse+touch minimum).

---

## 5. Acceptance criteria

- [ ] AC1: AddWatchlistModal has no stock/crypto type toggle; single query searches both types.
- [ ] AC2: HoldingFormModal create mode has no type toggle; single query searches both types with badge.
- [ ] AC3: Unified hits show `Stock`/`Crypto` badge + logo + symbol + name (parity with SearchDialog).
- [ ] AC4: Partial failure keeps other type + soft warning; total failure shows error.
- [ ] AC5: PortfolioValueChart hover (mouse/touch) shows date + value tooltip; moves with pointer.
- [ ] AC6: No text overflow/clip under chart: axis labels fully visible, header wraps on narrow widths.
- [ ] AC7: Focused Vitest + lint pass; `npm run build` passes; no new arch violation (browser still only calls FastAPI).

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | Existing `GET /api/assets/search?q&type=` ×2 via `searchLiveCatalog` |
| New / changed APIs | None |
| Auth required? | Yes (Bearer; existing `readAuthToken` path) |
| Caching / freshness | None (live search) |
| Jobs / schedules | None |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `components/watchlist/AddWatchlistModal.tsx`, `components/portfolio/HoldingFormModal.tsx`, `components/portfolio/PortfolioValueChart.tsx`, `lib/asset-search.ts` (reuse), tests |
| Backend API | None |
| Domain / services | None |
| Adapters | None |
| Infra / jobs | None |
| Docs / tests | This file, design, walkthrough, review |

---

## 8. Dependencies & risks

- Depends on: existing `searchLiveCatalog` contract (BL-009).
- Risks: test mocks target `searchAssets` single-type; must migrate to `searchLiveCatalog`. Chart SVG mouse mapping must handle responsive scaling (use bounding-rect ratio, not pixel constants).

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Sort unified hits (interleave vs grouped)? | resolved | Grouped stock-then-crypto (existing `searchLiveCatalog` order); no new ranking. |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-09-12 | Baseline quick: 4 pre-existing backend FX `stale_ok vs fresh` failures; ports-isolation gate fails on missing `rg`; frontend lint+unit green | Recorded; not caused by this change |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach: reused `searchLiveCatalog` in both modals (no backend change); chart hover via SVG pointer mapping + clamped HTML tooltip; axis start/end anchors + header wrap.
- PR / branch: `main` working tree (no commit per instructions; unrelated BL-032 edits preserved).
- Verification: `npm run lint` clean; `npm test` 65 files/424 tests pass; `npm run build` ok; `npm run test:e2e` 4 passed/4 skipped; `verify.ps1 full -SkipLocalStack -SkipE2E` frontend gates pass, backend 4 pre-existing FX failures + missing `rg` unchanged from baseline. Review `approve` in `docs/orchestration/reviews/BL-033-review.md`.
