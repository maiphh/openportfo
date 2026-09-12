# BL-033 Walkthrough — Unified search + chart hover/overflow

## Files changed

- `frontend/components/watchlist/AddWatchlistModal.tsx` — removed `assetType` state + `VN stock`/`Crypto` toggle; single input (`e.g. VNM, FPT, BTC, ethereum`) fans out via `searchLiveCatalog`; per-hit `Stock`/`Crypto` badge + `CompanyLogo`; `failedTypes` soft warning; `authRequired` → sign-in error.
- `frontend/components/portfolio/HoldingFormModal.tsx` — same unification in create/unlocked path; edit + `prefill` locked paths unchanged; removed toggle `Button` group.
- `frontend/components/portfolio/PortfolioValueChart.tsx` — `ValueSvg` now takes `points {date, marketValue}`; hover (mouse/touch/keyboard arrows+Escape) shows `role="status"` tooltip with date + `formatPrice` + currency; crosshair + dot; axis labels anchored `start`/`end` with `bottomPad 28`; header wraps (`flex-wrap`, `break-words`, `min-w-0`).
- Tests: `components/watchlist/AddWatchlistModal.test.tsx` (new, 3), `components/portfolio/PortfolioValueChart.test.tsx` (new, 2), `components/portfolio/HoldingFormModal.test.tsx` (+1 unified), `components/watchlist/WatchlistView.test.tsx` (migrated `searchAssets`→`searchLiveCatalog`, unified placeholder).

## Decisions / deviations

- Reused `searchLiveCatalog` (grouped stock-then-crypto) per design; no backend change, no `type=all` param.
- Chart stays hand-rolled SVG (no `lightweight-charts` swap) — hover via bounding-rect ratio mapping, tooltip clamped to 12–88% left.

## How to verify

```powershell
cd frontend
npm run lint
npm test -- components/watchlist/AddWatchlistModal.test.tsx components/portfolio/HoldingFormModal.test.tsx components/portfolio/PortfolioValueChart.test.tsx components/watchlist/WatchlistView.test.tsx
npm test
npm run build
npm run test:e2e
```

Manual: Watchlist → Add → type `btc` → both badges, no toggle. Dashboard → Add holding → same. Dashboard → Portfolio value → hover line → tooltip date+value; resize narrow → labels/header don't clip.

## Test evidence

- Focused: 4 files pass (15 tests pre-fix iteration; chart hover fixed via `getBoundingClientRect` mock).
- Full frontend: `65 passed (65), 424 passed (424)`; `lint` clean; `build` static export ok (15 pages).
- E2E: `4 passed, 4 skipped` (single-EB specs skip without backend).
- `verify.ps1 -Profile full -SkipLocalStack -SkipE2E`: frontend lint/unit/build pass; backend 4 pre-existing FX `stale_ok vs fresh` failures + `rg` missing for ports-isolation — identical to pre-change baseline.

## Known limitations

- Unified search issues 2 HTTP calls per debounce (same as sidebar); no ranking change.
- Chart tooltip is HTML overlay (mouse/touch/keyboard); no pin-on-click.
