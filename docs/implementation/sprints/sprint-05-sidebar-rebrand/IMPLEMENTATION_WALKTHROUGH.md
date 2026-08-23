# Sprint 05 batch 1 implementation walkthrough

**Scope:** BL-019, BL-020, BL-021, and BL-022 only  
**Branch:** `feat/s05b1-sidebar-rebrand`  
**Review status:** implementation complete and Solution Architect approved (2026-08-23)

Backlog statuses are `done`. No BL-023 through BL-026 behavior was added.

## Post-approval pre-release simplification (authoritative current state)

Product confirmed that no build using the former product name was released to
users and requested removal of the startup bootstrap for simplicity. The final
pre-release state therefore:

- removes `public/openportfo-bootstrap.js`, `scripts/verify-static-bootstrap.mjs`,
  `lib/storage-migration.ts`, and their migration/parity tests;
- removes the bootstrap tag and hydration suppression from the root layout;
- uses only canonical `openportfo.*` keys in auth, PKCE, currency, and market
  cache code;
- keeps bearer tokens tab-scoped and rejects/removes a canonical token found in
  localStorage; and
- applies stored theme and language through React provider effects after
  hydration, accepting a possible brief default dark/English shell on reload.

Post-removal verification: `npm test` passed **44 files / 317 tests**,
`npx tsc --noEmit` passed, and `npm run build` generated all **42/42** static
routes and completed **2/2** exports. Active frontend source contains no
bootstrap or former-name compatibility references.

The bootstrap and migration sections below are retained as the architecture and
review trail for the earlier implementation; they no longer describe the
runtime shipped from this branch.

## Files changed and deleted

### Storage, bootstrap, and rebrand

- Added `frontend/lib/storage-migration.ts` and its migration, storage-failure, inline-bootstrap, and public-asset parity tests.
- Updated `frontend/lib/auth.ts`, `frontend/lib/cognito.ts`, `frontend/lib/currency.ts`, and `frontend/lib/markets-cache.ts` to use the `openportfo.*` namespace with one-release `artryx.*` compatibility reads.
- Added `frontend/public/openportfo-bootstrap.js` and `frontend/scripts/verify-static-bootstrap.mjs`; added the `verify:static-bootstrap` package script.
- Updated `frontend/app/layout.tsx` with the parser-blocking bootstrap asset and retained `suppressHydrationWarning`.
- Updated `frontend/app/page.tsx` to use a client-side static redirect so `out/index.html` includes the root layout and bootstrap.
- Updated `frontend/components/Providers.tsx`, `BrandLogo`, package metadata, README text, auth-gate copy, search/chat copy, chart labels, and shell comments.
- Annotated the existing BL-001, BL-003, BL-006, BL-009, and BL-011 history sections without rewriting their historical references.
- Deleted obsolete `Header`, `NavItems`, `UserMenu`, `CurrencySelect`, `LanguageSelect`, and their obsolete tests. Removed `NAV_ITEMS` and `MOCK_USER` from `frontend/lib/mock-data.ts`.

### Avatar and identity

- Added `frontend/lib/avatar.ts`, `avatar.test.ts`, `components/UserAvatar.tsx`, and `UserAvatar.test.tsx`.
- Updated `frontend/components/ui/avatar.tsx` so its fallback is a plain wrapper compatible with the explicit image-error state.
- `UserAvatar` accepts the approved `avatarStyle`, `avatarSeed`, and `avatarColor` props, while retaining the shorter historical aliases.

### Theme, language, settings, and overlays

- Added `frontend/lib/theme.ts`, `theme.test.ts`, `ThemeProvider.tsx`, `i18n.ts`, `i18n.test.ts`, and `LanguageProvider.tsx`.
- Added `frontend/components/UserSettingsModal.tsx` and its behavior tests.
- Updated `SearchDialog.tsx` and `UserSettingsModal.tsx` with explicit successor-aware focus restoration contracts.
- Updated `FxRatesPanel.tsx` for shared auth state, nested-dialog inertness, and Tab/Shift+Tab containment.
- Updated `frontend/app/globals.css` with the light/dark semantic palettes and chat error colors.

### Shell, sidebar, auth, and chat

- Added `frontend/components/AppShell.tsx` and `AppShell.test.tsx`.
- Added `frontend/components/sidebar/Sidebar.tsx`, `SidebarNav.tsx`, `SidebarUserChip.tsx`, `MobileTopbar.tsx`, and dedicated sidebar/mobile tests.
- Added `frontend/lib/use-auth-profile.ts` and its abort/auth-change/storage/focus/sign-in/sign-out tests.
- Updated `ChatWidget.tsx`, `ChatLauncher.tsx`, `ChatPanel.tsx`, `ChatComposer.tsx`, and `ChatWidget.test.tsx` for shell insets, re-clamping, auth-key compatibility, and light-theme error contrast.
- Updated existing market/dashboard/chart/asset/watchlist components and tests for the new shell, palette, and canonical keys.

## Behavior walkthrough

1. **Pre-paint bootstrap and auth migration.** The root layout emits a literal, blocking `<script id="openportfo-bootstrap" src="/openportfo-bootstrap.js"></script>` in the document head. It is not a `next/script` Flight queue entry: the static asset executes during HTML parsing before the body app markup and before the no-module client runtime fallback. It migrates storage before React hydration, then applies the persisted theme and language. Auth precedence is session canonical, session legacy, local canonical, local legacy. A local bearer is removed even when promotion to session storage fails. Generic PKCE, currency, and market-cache migrations preserve their storage location, prefer canonical values, and are idempotent.

2. **Brand and chrome.** The visible product name is OpenPortfo and all user-facing chrome uses the new copy. Legacy names remain only in deliberate compatibility code, its tests, and the static bootstrap's compatibility branch.

3. **Identity and avatars.** `UserAvatar` chooses `userId` before email, uses an allowlisted DiceBear style (default `notionists`), and generates deterministic initials. Before an image error, the image is mounted and the fallback is absent. On error the image is removed and initials/guest fallback is mounted. A changed URL clears the previous error state and attempts the new image. Signed-out users never request an image and receive the labelled guest fallback.

4. **Theme, language, and currency.** Dark remains the default. Theme and language changes apply immediately, persist under `openportfo.*`, and update the document class/lang. English and Vietnamese translations cover shell/settings chrome. The settings modal exposes Appearance, Language, and Currency sections and opens the real FX rates panel.

5. **Desktop shell.** At `sm` and above, `AppShell` owns a fixed 240px sidebar or persisted 64px rail. The expanded market group is a disclosure button; the rail exposes Stock and Crypto links. The account chip opens settings, while sign-in/sign-out remains owned by the shared auth controller.

6. **Mobile shell and overlays.** Below 640px, `MobileTopbar` controls a conditionally mounted drawer. `AppShell` owns drawer/search/settings state, mutual overlay transitions, body-scroll locking, Escape/backdrop/path/media handling, and focus return. Drawer opener focus is restored only after a genuine standalone close; successor Search/Settings focus wins during drawer transitions. Settings -> Search preserves the original avatar as Search's eventual return target, suppresses Settings restoration, and keeps body lock active through replacement. Search -> Settings applies the symmetric rule. Settings has one Escape owner. While FX is open, the settings surface is `inert` and `aria-hidden`, and FX traps Tab/Shift+Tab. AppShell restores the exact prior body overflow on final close or unmount. Cmd/Ctrl+K opens search.

7. **Chat inset and errors.** `ChatWidget` receives 240px expanded, 64px rail, or 0px mobile inset. Launcher and panel positions are clamped against that inset and panel width shrinks against the available viewport. Light-theme chat errors use a dark red token (`red-400`) while dark mode retains the pale token; the regression test computes WCAG AA contrast against the tinted surface.

## Remediation decisions (R1-R5)

- **R1:** `next/script` with `beforeInteractive` was evaluated, but static export serializes it as a Flight queue entry rather than a directly executable script. The supported equivalent used here is a normal blocking external script in the root layout head. The production asset is self-contained, and `verify-static-bootstrap.mjs` checks the generated `out/index.html` for the direct tag, rejects a Flight-only occurrence, checks ordering before `<main>` and `noModule`, and executes the exact asset with JSDOM before app effects.
- **R2:** The explicit plain `<img>` state machine is retained, but the Radix fallback was replaced with a plain wrapper and is conditionally mounted only for no-URL/error states. Tests cover pre-error, error, URL reset, approved prop aliases, and signed-out guest behavior.
- **R3:** Overlay opener refs and drawer transition refs are captured synchronously. Explicit `restoreFocusOnClose` contracts suppress outgoing dialog restoration during Settings <-> Search replacement; AppShell carries the original avatar ref to the successor. Initial render does not steal focus; successor overlays own their first focus. Settings has one Escape handler, the FX surface traps both Tab directions, settings is inert while FX is open, and body-lock cleanup restores the saved inline value on unmount.
- **R4:** Light chat error copy now uses `text-red-400` with a dark-mode override, and a semantic palette test asserts the WCAG AA ratio on the actual tinted background.
- **R5:** Added behavior-focused coverage for the storage/script matrix and failures, auth key predicates/clear/read, AppShell media/focus/body lock/overlay transitions, ChatWidget insets/re-clamping/storage events, `useAuthProfile`, mobile/account controls, settings/FX focus, and avatar fallback/reset behavior. The test suite now asserts trimmed byte parity between `public/openportfo-bootstrap.js` and canonical `CLIENT_BOOTSTRAP_SCRIPT`, so the full migration matrix covers the actual production asset.

## Key implementation decisions

- Authentication migration remains separate from the generic same-storage migration loop because its security precedence and fail-closed behavior differ.
- The static bootstrap is maintained from the canonical `CLIENT_BOOTSTRAP_SCRIPT` contract: the public asset is the actual parser-time production path, and a parity test fails if it diverges from the fully tested helper string.
- No runtime dependency was introduced. The avatar uses a plain static-export-safe image wrapper so DiceBear failures deterministically reach the fallback.
- `AppShell` is the single owner for cross-overlay state and body locking; `useAuthProfile` is the single owner for profile loading and auth transitions.
- `UserSettingsModal` receives the shared auth controller and real FX panel rather than issuing a duplicate profile request.
- Obsolete header ownership was deleted rather than retained as compatibility wrappers, as required by the handoff.

## Deviations from the approved architecture

The only implementation-level deviations are the R1 static-export mechanism and the R2 image wrapper. R1 uses a blocking public script because the tested `next/script` static output was escaped Flight data rather than executable pre-hydration HTML. R2 uses a plain fallback wrapper because the explicit image error state cannot update Radix's image-loading context. The public behavior and approved contracts remain unchanged. The root page uses a client redirect rather than a server `redirect()` so the static root document contains the bootstrap; navigation still lands at `/markets/stock` after hydration. Its comment now accurately records that JavaScript-disabled visitors remain on the static shell rather than claiming a redirect without JavaScript.

## Verification and search results

- `npm test` — **pass**, **45 test files / 337 tests passed**.
- `npx tsc --noEmit` — **pass**.
- `npm run build` — **pass**. Next 15.5.23 generated **42/42** static routes and exported **2/2** pages. The only build warning is the supplied pre-existing `PortfolioDashboard.tsx` `useMemo` dependency warning.
- `npm run verify:static-bootstrap` — **pass**: `static bootstrap: direct tag, ordering, migration, theme, and language verified`.
- Generated `frontend/out/index.html` contains the direct bootstrap tag in `<head>`, before `<body>`, `<main>`, and the `noModule` runtime fallback; the verifier also confirms session legacy promotion, local bearer removal, currency migration, light class, and `lang="vi"` by executing the asset in JSDOM.
- Bootstrap parity — **pass**: `storage-migration.test.ts` reads `public/openportfo-bootstrap.js` and asserts trimmed byte equality with `CLIENT_BOOTSTRAP_SCRIPT` before running the full precedence/failure matrix.
- `git diff --check` — no whitespace errors (Git reports only existing LF/CRLF normalization warnings).
- Lockfile audit — `frontend/package-lock.json` changes are limited to the two expected root package-name fields (`artryx` -> `openportfo`).
- Legacy search — production compatibility literals are limited to `frontend/lib/storage-migration.ts` and `frontend/public/openportfo-bootstrap.js`; intentional legacy fixtures also appear in the migration/static-verifier/auth/chat regression tests. No unrelated legacy implementation was found.
- Stale-copy search for `account menu in the header`, `header switcher`, and `Header live search` — no matches.

## Browser smoke and known limitations

An interactive browser smoke was attempted with the installed local tooling only. `npm ls playwright puppeteer @playwright/test --depth=0` reported `(empty)`, and `Get-Command playwright,chromium,chrome,msedge,google-chrome` found no executable. No dependency was added. The static-export/JSDOM verifier is the replacement automated DOM check and directly proves the parser-time migration/theme/language behavior. The remaining limitation is that a real browser/deployed-network smoke should still confirm visual DiceBear success/failure, CSP behavior, both theme surfaces, all requested routes, and touch/keyboard behavior.

Other known warnings:

- Vitest prints the existing Vite native-config warning at startup.
- One AppShell jsdom test prints the expected `Not implemented: navigation to another Document` informational message when exercising a mocked link; the suite remains green.
- DiceBear is an external image service; deterministic initials/guest fallback covers unavailable or failed image requests.

## Reviewer focus areas

- Inspect `out/index.html` and `public/openportfo-bootstrap.js` together; confirm the direct parser-blocking tag is the production path and the helper remains parity-tested.
- Exercise four-way auth precedence, storage failures, and cleanup of both prefixes.
- Verify drawer -> Search, drawer -> Settings, Settings -> FX -> Settings, final close, backdrop, route, and media transitions with focus and body overflow.
- Check 240px/64px/0px shell-chat insets and ChatWidget re-clamping.
- Exercise both themes across markets, portfolio, watchlist, asset, and chat when a browser is available, including DiceBear success/failure and light chat-error contrast.
