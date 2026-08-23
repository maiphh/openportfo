# Sprint 05 batch 1 — Architect handoff

**Scope:** BL-019, BL-020, BL-021, BL-022 only  
**Verdict:** **Approved after corrections in this handoff and `PLAN.md`**  
**Implementation authority:** where this handoff differs from an older statement in `PLAN.md`, this handoff wins.  
**Backlog status:** leave all four items `ready` until implementation begins.

> **Superseded pre-release decision (2026-08-23):** product confirmed that no
> former-name build reached users. The bootstrap and all legacy-key migration
> requirements in this handoff were removed after approval. This document is
> retained as the original implementation brief; the current-state decision is
> recorded in `IMPLEMENTATION_WALKTHROUGH.md` and BL-019.

## 1. Repository facts the implementation must preserve

- Frontend is Next `15.5.23`, React `19.1.0`, Tailwind `4`, TypeScript strict, Vitest/jsdom, and production `output: "export"`.
- No dependency is required. Existing Radix Avatar and lucide-react cover the design.
- Current auth intentionally migrates a same-key token from localStorage to sessionStorage. The prefix rename must preserve that security boundary.
- The FX overlay is `frontend/components/currency/FxRatesPanel.tsx`.
- Baseline supplied by verification: 35 test files / 274 tests and `npm run build` pass. The existing `PortfolioDashboard.tsx` `useMemo` hook warning is not introduced by this batch.

## 2. Non-negotiable architecture decisions

### 2.1 Storage bootstrap is pre-React and render-pure

Do not call `runStorageMigration()` in `Providers`, a component body, a state initializer, or `useMemo`. React render can be restarted or abandoned; mutating browser storage there violates render purity.

Create `lib/storage-migration.ts` with:

```ts
export const STORAGE_PREFIX = "openportfo.";
export const LEGACY_STORAGE_PREFIX = "artryx.";

export type MigrationWindow = {
  localStorage?: Pick<Storage, "getItem" | "setItem" | "removeItem"> | null;
  sessionStorage?: Pick<Storage, "getItem" | "setItem" | "removeItem"> | null;
};

export function legacyKeyFor(key: string): string;
export function readMigrated(
  storage: Pick<Storage, "getItem"> | null | undefined,
  key: string,
): string | null;
export function runStorageMigration(target?: MigrationWindow): string[];
export const CLIENT_BOOTSTRAP_SCRIPT: string;
```

`app/layout.tsx` must emit `CLIENT_BOOTSTRAP_SCRIPT` in a raw `<script>` as the first child of `<body>`, before `<Providers>`. It performs storage migration, then applies the stored theme and language. This is static-export safe and runs before consumer hydration/effects. Keep `<html lang="en" className="dark" suppressHydrationWarning>`.

`Providers.tsx` remains a pure provider composition:

```tsx
<ThemeProvider>
  <LanguageProvider>
    <CurrencyProvider>{children}</CurrencyProvider>
  </LanguageProvider>
</ThemeProvider>
```

The script and exported migration helper may share generated constants, or may be separately written, but a test must execute the actual script against fake storage and assert the same final states as the helper. This prevents an untested inline path.

### 2.2 Exact auth migration algorithm

Auth is not part of a generic per-storage copy loop. Use this winner order:

| Priority | Candidate |
|---:|---|
| 1 | `sessionStorage[openportfo.accessToken]` |
| 2 | `sessionStorage[artryx.accessToken]` |
| 3 | `localStorage[openportfo.accessToken]` |
| 4 | `localStorage[artryx.accessToken]` |

Trim candidates and treat an empty string as absent. The final canonical location is only `sessionStorage[openportfo.accessToken]`.

1. If session-new already exists, it wins. Remove session-old and both local token keys.
2. If session-old wins, try to write its cleaned value to session-new. On success, remove session-old and both local keys. If the write fails, retain session-old for the compatibility read, but still remove both persistent local copies.
3. If either local candidate wins, try to write it to session-new, then remove both local keys regardless of write success. If the write fails, return no token (fail closed); never preserve a bearer token persistently merely because migration failed.
4. A new-prefix token found in localStorage is also migrated/removed. This handles current same-key test patterns and protects against any partial rollout.
5. Storage property access and each method call are individually best-effort/guarded. The guarantee applies whenever the browser permits removal.

`readAuthToken()` repeats this browser-default behavior as defense in depth. Its explicitly injected `storage` overload remains deterministic: read new, then legacy, in only that supplied store; it must not infer another store.

On successful `writeAuthToken()`, write session-new and remove session-old plus both local token keys. `clearAuthToken()` removes both prefixes from both stores. `isAuthTokenStorageKey(key: string | null)` returns true for the new and legacy names and is used by both `CurrencyProvider` and `ChatWidget` storage listeners. Same-document updates continue to use `openportfo:auth-change`.

Other migrations are location-preserving:

- `artryx.pkce` → `openportfo.pkce` in sessionStorage only. PKCE clear removes both names during compatibility.
- `artryx.displayCurrency` → `openportfo.displayCurrency` in localStorage only.
- Four `artryx.markets.{heatmap|quotes}.{stock|crypto}` entries → new prefix in sessionStorage only.
- For these same-storage keys, new wins when both exist. Remove legacy after a successful copy, or immediately when new already exists.

### 2.3 Responsive shell follows the backlog breakpoint

BL-020 says mobile is below `sm`; use that contract:

- `<640px`: sticky mobile top bar and conditionally mounted overlay drawer.
- `sm+`: fixed sidebar; 240px expanded and 64px collapsed.
- Content padding uses `sm:pl-60` / `sm:pl-16`.
- Do not substitute `lg` without stakeholder approval.

The desktop collapse state belongs to `AppShell`, not `Sidebar`. Initialize expanded for SSR, read `openportfo.sidebar.collapsed` in an effect, and persist only in the toggle handler. `Sidebar` is controlled.

### 2.4 Overlay and focus ownership

`AppShell` owns `drawerOpen`, `searchOpen`, and `settingsOpen`. Opening one closes the other shell overlays. One AppShell effect owns body scroll lock for their union; individual dialogs must not compete by restoring `body.style.overflow` independently.

- Drawer: `role="dialog"`, labelled, close button focused on open, Tab wraps, Escape/backdrop/link navigation closes, focus returns to hamburger. Close on pathname change and when the media query transitions to `sm+`.
- SearchDialog: preserve input autofocus; add final focus return to the opener.
- Settings: visible title via `aria-labelledby`, focus close button, Tab wraps, Escape/backdrop closes, focus returns to avatar.
- FX: remains at z-100. While it is open, suspend the underlying settings Escape handler and make the settings panel non-interactive/hidden from assistive technology. FX focuses its close button and restores focus to the FX trigger. One Escape closes FX only; a second closes settings.

Z-order: sidebar/top bar 40, chat 50/51, drawer 60/61, search/settings 80, FX 100.

### 2.5 Chat must respect the sidebar

BL-020 explicitly says ChatWidget must not overlap the sidebar. Add an optional `leftInset?: number` prop (default `0`) to ChatWidget and include it in launcher and panel clamping:

- `sm+` expanded: 240px.
- `sm+` collapsed: 64px.
- Below `sm`: 0px.

Re-clamp a stored/live position when the inset changes. The desktop panel width must also shrink to available space (`viewport width - inset - margins`) near the 640px boundary. Preserve all existing drag/session behavior.

## 3. Implementer-ready component contracts

Use a single `useAuthProfile()` instance in `AppShell` and pass its controller to shell consumers; otherwise the always-mounted sidebar and settings modal duplicate `/api/auth/me` requests.

```ts
export type AuthProfileController = {
  hydrated: boolean;
  token: string | null;
  profile: AuthProfile | null;
  loading: boolean;
  error: string | null;
  cognitoConfigured: boolean;
  refresh: () => void;
  signIn: (next?: string) => Promise<void>;
  signOut: () => void;
};
export function useAuthProfile(): AuthProfileController;
```

The hook listens to `AUTH_CHANGE_EVENT`, matching storage events, and focus; aborts stale profile requests; clears invalid auth on 401/403; and owns sign-in errors. Sign-out clears local state immediately and navigates to Cognito logout when configured.

```ts
type AppShellProps = { children: ReactNode };

type SidebarProps = {
  collapsed: boolean;
  auth: AuthProfileController;
  onToggleCollapsed: () => void;
  onSearch: () => void;
  onOpenSettings: () => void;
};

type SidebarNavProps = {
  collapsed: boolean;
  onSearch: () => void;
  onNavigate?: () => void;
};

type SidebarUserChipProps = {
  collapsed: boolean;
  auth: AuthProfileController;
  onOpenSettings: () => void;
};

type MobileTopbarProps = {
  menuOpen: boolean;
  menuButtonRef?: Ref<HTMLButtonElement>;
  profile: AuthProfile | null;
  onMenu: () => void;
  onOpenSettings: () => void;
};

type UserSettingsModalProps = {
  open: boolean;
  auth: AuthProfileController;
  onClose: () => void;
};
```

`MobileTopbar` hamburger uses `aria-expanded={menuOpen}` and `aria-controls="mobile-sidebar-drawer"`. Rail buttons retain `aria-label` and `title`. The expanded Market group uses a real button with `aria-expanded`; rail mode renders Stock and Crypto as direct links.

Keep nav configuration declarative and translated, but remove the now-unused `NAV_ITEMS` and `MOCK_USER` exports from `lib/mock-data.ts` after deleting their consumers.

## 4. Avatar contract

Use the BL-022 v9 URL contract without a runtime helper fetch:

```ts
export const AVATAR_STYLES = [
  "notionists", "notionists-neutral", "adventurer-neutral", "big-smile",
  "lorelei", "bottts", "thumbs", "shapes",
] as const;
export type AvatarStyle = (typeof AVATAR_STYLES)[number];

export type AvatarOptions = {
  seed: string;
  style?: AvatarStyle;
  backgroundColor?: string | null;
  size?: number;
};
```

- Default style is `notionists`; do not interpolate an arbitrary string into the URL path.
- Trim seed; stable identity is trimmed `userId`, then trimmed email, else null.
- Use `URL`/`URLSearchParams`; tests inspect decoded params rather than requiring `%20` versus `+`.
- Accept `#RGB`, `RGB`, `#RRGGBB`, `RRGGBB`; remove `#`; omit invalid color. Emit size only for a positive integer.
- Signed out renders no image and a labelled guest icon. Image failure shows up to two uppercase initials. Test the actual error transition; use explicit error state only if Radix/jsdom loading state is not reliable, and reset it on URL change.

## 5. Theme, language, and settings

- Default theme remains dark; no system-theme branch.
- Keep Tailwind `@theme`; add unlayered complete `:root` light and `.dark` dark overrides after it, plus `@custom-variant dark`.
- Every variable overridden in light must be explicitly restored in `.dark`. Use the palette table in `PLAN.md` and perform the listed chart/heatmap/pie/chat hardcoded-color pass.
- `CLIENT_BOOTSTRAP_SCRIPT` applies the `dark` class and valid `en`/`vi` lang before hydration. Providers read storage in mount effects and apply changes immediately thereafter.
- Chrome-only i18n remains the boundary. Render currency rows from `DISPLAY_CURRENCIES`; keep formatted page data wired through the existing `CurrencyProvider`.
- The FX button opens the existing `components/currency/FxRatesPanel.tsx`.

## 6. Implementation slices and gates

1. **BL-019 storage/rebrand.** Write migration/auth matrix tests first; implement bootstrap and fallback reads; rename keys/copy/brand/package; remove stale legacy names. Gate: focused tests, full suite, build.
2. **BL-022 avatar.** Pure URL/identity helpers, then `UserAvatar`; no UI wiring yet. Gate: helper and fallback tests.
3. **BL-021 infrastructure.** Dual palette, bootstrap theme/lang fragment, ThemeProvider, i18n/LanguageProvider. Gate: provider tests, build, manual class toggle.
4. **BL-021 modal.** Settings sections, shared auth controller prop, currency/FX, focus/Escape contract; SearchDialog focus/i18n. Gate: modal/nested FX tests.
5. **BL-020 shell.** AppShell/sidebar/mobile drawer, shared auth hook, `sm` breakpoint, layout rewiring, ChatWidget inset, deletions/stale copy. Gate: shell + chat tests, full suite.
6. **Polish/close-out.** Light-mode audit, README/history notes, static export and manual route smoke. Only after verification should backlog status move to done.

Each slice ends with:

```powershell
Set-Location frontend
npm test
npm run build
```

Do not accept a reduced test count caused by accidental test deletion; intentional deletion of `NavItems.test.tsx` and `UserMenu.test.tsx` must be offset by replacement shell/auth coverage.

## 7. Required test gates

### Storage/auth

- All four auth locations and precedence combinations.
- New/local and old/local migrate to new/session and are removed locally.
- Session write failure behavior: retain old/session fallback; delete local-only bearer token and return null.
- Both auth names cleared from both storages.
- PKCE/cache location remains session; currency remains local.
- Both-present new-wins, idempotence, storage getter/method throws.
- Execute actual `CLIENT_BOOTSTRAP_SCRIPT` in a controlled fake DOM/window and assert final storage, theme class, and lang.

### Shell/accessibility

- Collapse persistence is tested in `AppShell`; `Sidebar` tests controlled rendering/callback only.
- Hamburger expanded/control attributes, drawer close on link/path/Escape/backdrop/media transition, focus wrap/return.
- Cmd/Ctrl+K and sidebar Search open SearchDialog; overlay mutual exclusion.
- Avatar opens Settings in desktop and mobile shell.
- Nested FX consumes first Escape and restores to trigger; Settings consumes second and restores to avatar.
- Body overflow returns to its exact prior inline value after the final overlay closes.
- Chat launcher/panel clamp at 240, 64, and 0 insets and re-clamp on collapse change.

### Theme/avatar

- Theme persistence and DOM class; language persistence and `<html lang>`; EN/VI dictionary completeness.
- Currency selection changes provider formatting; actual FX component opens.
- Avatar URL path/params/determinism, invalid input omission, stable seed order, signed-out and image-error fallbacks.
- Manual contrast smoke: markets stock/crypto, portfolio, watchlist, asset, chat in both themes.

### Close-out searches

```powershell
rg -n -i "artryx" frontend `
  -g "!node_modules/**" -g "!.next/**" -g "!out/**" -g "!package-lock.json"

rg -n "account menu in the header|header switcher|Header live search" frontend `
  -g "!node_modules/**" -g "!.next/**" -g "!out/**"
```

The first search may return only intentional `LEGACY_*` compatibility constants/tests. Update the lockfile root package name with `npm install --package-lock-only` and verify its diff is limited to expected metadata.

## 8. Deletion/replacement map

Delete:

- `components/Header.tsx`
- `components/NavItems.tsx` and `components/NavItems.test.tsx`
- `components/UserMenu.tsx` and `components/UserMenu.test.tsx`
- `components/CurrencySelect.tsx`
- `components/LanguageSelect.tsx`

Replace their responsibilities before deletion:

- global search shortcut/trigger → AppShell/SidebarNav
- nav active/Market behavior → SidebarNav
- auth profile/sign-in/out → `useAuthProfile` + SidebarUserChip/Settings
- currency/language controls → UserSettingsModal
- FX access → UserSettingsModal using `components/currency/FxRatesPanel.tsx`
- mobile navigation → MobileTopbar + drawer
- brand → Sidebar/MobileTopbar

Also remove unused `NAV_ITEMS`/`MOCK_USER`, `.header`/`.header-wrapper`/`.search-text`, and replace stale header wording in `ChatPanel`, `PortfolioDashboard`, `frontend/README.md`, and `lib/asset-search.ts`.

## 9. Acceptance mapping

| Backlog | Evidence required |
|---|---|
| BL-019 | brand/copy grep; exact migration matrix; no persistent access token; test/build gates |
| BL-020 | desktop sidebar/avatar; persisted rail; `<sm` drawer; keyboard/focus behavior; Cmd/Ctrl+K; ChatWidget inset tests |
| BL-021 | three settings sections; pre-paint theme; persisted language/html lang; currency re-render; actual FX panel; two-theme manual smoke |
| BL-022 | stable userId→email avatar; allowlisted deterministic URL; signed-out/error fallback tests |

## 10. Risks and blockers

- Highest risk is auth persistence regression; do not generalize its migration.
- At exactly 640px the available chat panel width is smaller; calculate it from viewport minus sidebar inset rather than retaining a fixed desktop width.
- Nested overlay listeners and independent scroll locks cause double-close/focus loss; use the ownership rules above.
- Static HTML cannot know localStorage. The inline bootstrap prevents theme flash while React provider state hydrates safely.
- External DiceBear availability is inherently best-effort; fallback is part of normal behavior, not an exceptional UI.

No unresolved product or technical blocker remains for BL-019..022. No external research is required to implement the repository-defined contract.
