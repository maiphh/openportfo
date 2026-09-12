# BL-033 Design — Unified search + chart hover/overflow

## Context & constraints

- Locked: Next.js static CSR, browser → FastAPI only (`lib/*` clients), no browser-direct market APIs, Cognito/fake-token auth preserved, ports/adapters untouched.
- Sidebar `SearchDialog` is the reference unified UX: `searchLiveCatalog({q, token, signal})` fans out to `searchAssets({q, type: stock})` + `searchAssets({q, type: crypto})` in parallel, merges hits, surfaces `failedTypes`, `authRequired`.
- Legacy: `AddWatchlistModal` + `HoldingFormModal` each hold `assetType` state + toggle buttons + single `searchAssets` call.
- Chart: `PortfolioValueChart > ValueSvg` static path, `viewBox 0 0 640 (height+22)`, axis `<text textAnchor=middle>` at `x=padX` / `x=width-padX` → half-glyph clips outside viewBox (SVG overflow hidden). Header `<p text-2xl>` inline spans don't wrap gracefully.

## Affected surfaces

| Surface | File | Change |
|---------|------|--------|
| Watchlist modal | `frontend/components/watchlist/AddWatchlistModal.tsx` | Remove toggle, use `searchLiveCatalog`, badge UI |
| Holding modal | `frontend/components/portfolio/HoldingFormModal.tsx` | Remove toggle in create/unlocked path, use `searchLiveCatalog` |
| Chart | `frontend/components/portfolio/PortfolioValueChart.tsx` | Hover tooltip + overflow fix |
| Lib (reuse) | `frontend/lib/asset-search.ts` | No change (reuse `searchLiveCatalog`, `ASSET_SEARCH_DEBOUNCE_MS`, `liveSearchQuery`) |
| Tests | `WatchlistView.test.tsx`, new `AddWatchlistModal.test.tsx` / `HoldingFormModal` search test, `PortfolioValueChart.test.tsx` | Migrate mocks |

## API / data deltas

None. Backend `/api/assets/search?q&type=stock|crypto` unchanged. Chart `GET /api/portfolio/performance` unchanged.

## Sequence — unified modal search

```
input(q) --debounce 250ms--> searchLiveCatalog({q, signal})
  ├─ GET /api/assets/search?q&type=stock ─┐
  └─ GET /api/assets/search?q&type=crypto ─┴─> merge hits (stock, crypto)
       ├─ 401 → authRequired → error copy
       ├─ 1 failed → hits(other) + soft warning
       └─ 2 failed → error copy
pick hit → selected(hit) → submit(hit.assetType/symbol/assetId)
```

## Decisions (ADR-style)

1. Reuse `searchLiveCatalog`, don't add `type=all` backend param. Context: backend validates `type` strictly; adding a param is cross-stack scope. Decision: fan out in frontend (parity with sidebar). Consequence: 2 HTTP calls per keystroke-debounce; same as today.
2. Grouped order (stock hits then crypto), no ranking. Context: avoids new sort semantics. Consequence: predictable, matches SearchDialog.
3. Badge UI copies SearchDialog: `Stock`/`Crypto` uppercase pill + `CompanyLogo`. Consequence: visual parity, minimal CSS.
4. Chart hover = custom SVG overlay (no new dep). Context: `lightweight-charts` exists in package.json but PortfolioValueChart is hand SVG; swapping libs is scope creep. Decision: pointer-mapped tooltip + crosshair in existing SVG. Consequence: no bundle change, responsive-safe via bounding-rect ratio.
5. Overflow fix: edge anchors `start`/`end` + bottom pad 28 + header `flex-wrap`/`break-words`. Context: middle anchor at edges is the clip root cause. Consequence: labels fully inside viewBox.

## TDD order

1. `AddWatchlistModal` unified: single input searches both (mock `searchLiveCatalog`), no toggle buttons, badge shown.
2. `HoldingFormModal` create unified: same; edit/prefill locked unchanged.
3. `PortfolioValueChart`: hover tooltip shows date+value; axis anchors don't clip (assert `textAnchor` start/end + tooltip role).
4. Regression: `WatchlistView`, `SearchDialog`, `asset-search` suites stay green.

## Handoff to Implementor

- Remove `assetType` state + toggle `Button` group from both modals; delete `searchAssets` import, add `searchLiveCatalog` + `liveSearchQuery` + `ASSET_SEARCH_DEBOUNCE_MS`.
- Keep abort + debounce pattern; guard `if (q.length<1 || selected)`.
- Key hits by `${assetType}:${assetId}`; slice 12; badge `<span>Stock|Crypto</span>`.
- Chart: `ValueSvg` takes `points: ValuedPoint[]` (date+value), internal `hoverIndex` state, `onMouseMove/Leave`, `onTouch`, overlay `<rect fill=transparent>` capturing events, tooltip as HTML absolute div (clamped), crosshair `<line>` + `<circle>`, axis texts anchored start/end, container `relative`, header `flex flex-wrap items-baseline gap-x-2 break-words`.
- Out of scope: backend, sorting, new deps, SSR.

## AC checklist (copy)

- [ ] AC1-AC4 unified search + badges + failure paths
- [ ] AC5 hover tooltip date+value
- [ ] AC6 no overflow (labels + header)
- [ ] AC7 lint/unit/build green, no arch violation
