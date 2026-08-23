# Sprint 05 batch 1 — Final architecture acceptance review

**Branch reviewed:** `feat/s05b1-sidebar-rebrand`  
**Scope:** BL-019, BL-020, BL-021, BL-022  
**Final review date:** 2026-08-23  
**Verdict:** **APPROVED**

> **Post-review product decision (2026-08-23):** product confirmed there were
> no users or releases under the former name and explicitly requested removal
> of the bootstrap and compatibility layer. Bootstrap-specific acceptance
> evidence below is retained as review history, not as the current runtime.

All required findings from the first and second architecture reviews are closed. The implementation satisfies the repository-defined code, security, accessibility, static-export, and regression-test gates for BL-019..022. The backlog items are authorized to move from `in_progress` to `done`; this review does not itself edit backlog status.

## Final focused re-review

### R3-S2 — successor-overlay focus ownership — Closed

The actual implementation now has an explicit transition contract rather than relying on `document.activeElement` after an outgoing dialog unmounts:

- `AppShell.openSearch()` detects an open Settings modal, copies `settingsReturnFocusRef.current` to Search, and disables Settings close-time restoration before replacing it.
- `AppShell.openSettings()` applies the symmetric Search → Settings behavior.
- `SearchDialog` and `UserSettingsModal` accept `restoreFocusOnClose`; their effects restore only for a genuine final close.
- The successor retains the original avatar/menu opener rather than a soon-to-be-disconnected control inside the outgoing dialog.
- AppShell's union scroll lock sees `overlayOpen === true` throughout a batched replacement, so it does not restore body overflow between overlays.
- The focused AppShell regressions prove:
  - Settings → Search gives focus to the Search input, keeps overflow locked, closes to the original avatar, then restores overflow;
  - Search → Settings suppresses Search restoration, gives focus to Settings, closes to the original avatar, and preserves lock continuity;
  - drawer successor paths and standalone close behavior remain intact.

No behind-overlay restoration or invalid final return target remains in the inspected transition paths.

### R5-S2 — production bootstrap parity and ordering — Closed

- `storage-migration.test.ts` reads `public/openportfo-bootstrap.js` and asserts trimmed byte equality with canonical `CLIENT_BOOTSTRAP_SCRIPT`.
- The complete canonical precedence, coexistence, storage-failure, throwing-access, same-store migration, theme, and language matrix therefore covers the production parser-time asset. A one-sided edit now fails the suite.
- `verify-static-bootstrap.mjs` directly asserts `bootstrapIndex < bodyIndex`, in addition to checking the direct tag, ordering before app markup and the `noModule` fallback, and rejection of a Flight-only occurrence.
- The rebuilt `out/index.html` contains the direct blocking bootstrap in `<head>` before `<body>`. The verifier executes the production asset with JSDOM and confirms session promotion, persistent bearer removal, currency migration, light theme, and Vietnamese language.

## Independent verification

- `npm test`: **passed — 45 test files / 337 tests**.
- Focused `AppShell.test.tsx` and `storage-migration.test.ts`: **passed — 2 files / 32 tests**.
- `npx tsc --noEmit`: **passed**.
- `npm run build`: **passed — 42/42 static routes generated, 2/2 exported**.
- `npm run verify:static-bootstrap`: **passed** after the final rebuild.
- `git diff --check`: no whitespace errors; only working-tree line-ending notices.
- Lockfile: only the two expected root package-name fields change from `artryx` to `openportfo`.
- Legacy/stale-copy audit: active legacy literals are limited to intentional compatibility implementation/assets and test fixtures; no stale active header copy remains.
- The only build warning is the supplied pre-existing `PortfolioDashboard.tsx` `useMemo` dependency warning.

## Complete finding disposition

| Finding | Final disposition |
|---|---|
| R1 — executable pre-paint bootstrap | **Closed** |
| R2 — deterministic avatar image/fallback state and aliases | **Closed** |
| R3 — overlay focus, Escape, inertness, Tab containment, and body cleanup | **Closed** |
| R3-S2 — Settings/Search successor focus ownership | **Closed** |
| R4 — light-theme chat error contrast | **Closed** |
| R5 — acceptance-critical regression coverage | **Closed** |
| R5-S2 — production bootstrap parity/order gate | **Closed** |

## Acceptance mapping and authorization

| Backlog | Final result |
|---|---|
| BL-019 | **Accepted:** rebrand and storage migration preserve session-only bearer security, compatibility, cleanup, startup ordering, and static export. |
| BL-020 | **Accepted:** desktop rail/mobile drawer, navigation, persistence, keyboard/focus ownership, and ChatWidget inset contracts are implemented and covered. |
| BL-021 | **Accepted:** theme, language, currency, Settings/FX behavior, overlay accessibility, pre-paint preferences, and light contrast meet the approved contract. |
| BL-022 | **Accepted:** deterministic DiceBear identity/configuration and image-error/signed-out fallbacks meet the approved contract. |

**Authorization:** BL-019, BL-020, BL-021, and BL-022 may now be marked `done` by the owning orchestrator/implementer.

## Non-blocking release follow-up

No browser executable or Playwright/Puppeteer installation is available in this workspace. This is **not a code-acceptance blocker** because the relevant state, focus, storage, contrast, static-HTML, and JSDOM contracts are directly covered and the production build is green.

Before or immediately after deployment, run a real-browser smoke for both themes across markets, portfolio, watchlist, asset, and chat; `<sm` touch/drawer behavior; keyboard overlay transitions; DiceBear network success/failure; and deployed CSP/static-asset delivery. Any environment-specific issue found there should be handled as a release defect rather than reopening this review without evidence.
