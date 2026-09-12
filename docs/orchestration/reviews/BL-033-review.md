# BL-033 Review — Unified search + chart hover/overflow

**Verdict:** `approve`

## AC check (evidence = file:line)

- [x] AC1 — No toggle in `AddWatchlistModal`; single query fans out. `AddWatchlistModal.tsx` has no `VN stock`/`Crypto` toggle buttons, calls `searchLiveCatalog({q, signal})`; `AddWatchlistModal.test.tsx:27-33` asserts absence + unified placeholder.
- [x] AC2 — Same for `HoldingFormModal` create. `HoldingFormModal.tsx` create branch has no toggle; `HoldingFormModal.test.tsx` unified test asserts placeholder + no toggle + both hits.
- [x] AC3 — Badges parity. Both modals render `Stock`/`Crypto` pill + `CompanyLogo`; tests assert `Stock`+`Crypto` text.
- [x] AC4 — Partial/total failure. Both modals handle `failedTypes==1` soft warning, `==2` error, `authRequired` sign-in error; covered by `AddWatchlistModal.test.tsx` partial-failure test + `asset-search.test.ts` contract.
- [x] AC5 — Hover tooltip. `PortfolioValueChart.tsx` `ValueSvg` pointer/touch/keyboard handlers + `role="status"` tooltip with `hovered.date` + `formatPrice`; `PortfolioValueChart.test.tsx` hover test passes.
- [x] AC6 — No overflow. Axis `textAnchor start/end` at `padX`/`width-padX`, `bottomPad 28`, header `flex-wrap break-words min-w-0`; axis-anchor test passes; `build` + e2e smoke clean.
- [x] AC7 — Gates. `lint` clean, `424/424` unit pass, `build` ok, `test:e2e 4 passed/4 skipped`; no backend change.

## Architecture / constraints

- [x] No `boto3`/`httpx`/`requests` added (frontend-only diff; backend untouched).
- [x] Static export intact (`build` 15 pages, no SSR/server actions).
- [x] Browser → FastAPI only (`searchLiveCatalog` → `/api/assets/search`, performance endpoint); no direct CoinGecko/vnstock/FX.
- [x] Auth preserved (`readAuthToken` fallback; 401 → sign-in copy).

## Tests

Meaningful (unified placeholder/toggle absence, dual-hit badges, partial failure, hover date+value, axis anchors) and green. `WatchlistView` migration keeps 409/remove/retry coverage.

## Residual risk

Backend `verify` failures are pre-existing (FX `stale_ok` ×4, missing `rg`) and unrelated. Tooltip clamping is heuristic (12–88%); extreme values still readable but not pixel-centered.
