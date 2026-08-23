# Sprint 05 (batch 1) — Rebrand + Sidebar shell + Settings modal + DiceBear avatars

| | |
|--|--|
| **ID** | S05B1 (backlog BL-019, BL-020, BL-021, BL-022) |
| **Depends on** | existing frontend shell (Header/NavItems/UserMenu), CurrencyProvider, auth lib |
| **Unblocks** | batch 2 (BL-023 settings page, BL-024 admin, BL-025 chatbot, BL-026 FX tab) |
| **PRD** | sprint-05 backlog feature docs `docs/backlog/features/BL-019..022` |
| **Status** | implemented and architecture-approved (2026-08-23) |

> **Post-approval product decision (2026-08-23):** no build using the former
> product name was ever released. The storage bootstrap, legacy-key reads, and
> migration tests described below were therefore removed before first release.
> Canonical `openportfo.*` storage remains; theme and language now apply from
> React provider effects after hydration. The migration sections below are
> retained only as the original architecture record.

---

## 1. Objective

Ship four related shell changes in one coherent batch:

1. **BL-019** rename Artryx → **OpenPortfo** everywhere in `frontend/`, with one-time localStorage/sessionStorage key migration.
2. **BL-022** deterministic **DiceBear** avatars (`lib/avatar.ts` + `UserAvatar`), initials fallback.
3. **BL-021** real **light/dark theming** (Tailwind v4 variable override), **EN/VI chrome i18n**, and a **user settings modal** (theme / language / currency) opened from the avatar.
4. **BL-020** replace the top header with a **collapsible left sidebar** (icon rail, mobile drawer, avatar pinned bottom-left).

All under static export (`output: "export"`), no new dependencies.

---

## 2. Ground rules / constraints

- **Static export only** — no server components with request data, no middleware, no `next/image`. Plain `<img>` for DiceBear (Radix `AvatarImage` is a plain img).
- **No new deps.** No next-themes, no i18n lib, no Radix Dialog. Hand-rolled modals matching `SearchDialog` / `FxRatesPanel`. lucide-react only for icons.
- **Conventions:** Vitest + jsdom + Testing Library, colocated `*.test.tsx`; mock `next/navigation`, `next/link`, `@/lib/cognito`, global `fetch` (see `NavItems.test.tsx`, `UserMenu.test.tsx`). Client components read storage in effects (mounted-guard) — never in `useState` initializers (hydration).
- **Reserved namespace:** do NOT create `components/settings/` in this batch — it is reserved for the BL-023 settings *page*. This batch's modal lives at `components/UserSettingsModal.tsx`.
- **Extension points for concurrent batch 2** (must not be blocked by this design):
  1. `SidebarNav` renders from a declarative item table (icon map + `NAV_ITEMS`); adding `Settings` (all users) and `Admin` (only when `useAuthProfile().profile?.role === "admin"`) entries later is additive.
  2. `buildAvatarUrl({ seed, style, backgroundColor })` takes all avatar params; the future Avatar tab (`avatarStyle` / `avatarSeed` / `avatarColor` on `UserProfile`) plugs in via `UserAvatar` props.
  3. `Providers.tsx` stays a flat composition — batch 2 providers append inside it.

---

## 3. Decision register (resolves every open question)

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| D1 | BL-019 new keys | `openportfo.accessToken` (sessionStorage), `openportfo.pkce` (sessionStorage), `openportfo.displayCurrency` (localStorage), `openportfo.markets.{widget}.{market}` (sessionStorage) | Matches existing `openportfo:auth-change` event + `openportfo.chat-bubble-position.v1`; same storage *kind* as today |
| D2 | BL-019 migration mechanism | `lib/storage-migration.ts` plus a self-contained `CLIENT_BOOTSTRAP_SCRIPT` executed as the first `<body>` child, before the React tree. Never mutate storage in a component render. Preferences/cache migrate within their designated storage; auth uses the cross-storage algorithm in §5.1. | Guarantees migration precedes all consumer effects without a render side effect or blank client-only gate; remains static-export safe and unit-testable |
| D3 | BL-019 read-compat | Non-auth reads check new then legacy in the same designated storage. Browser-default auth reads use the precedence/cleanup contract in §5.1; explicitly injected storage reads new then legacy without cross-storage mutation. Writes go to new keys only; clear operations remove both auth/PKCE prefixes for one release. | Preserves the existing local→session token security boundary and one-release compatibility |
| D4 | BL-020 sidebar breakpoint | Static sidebar from **`sm` (≥640px)**; below `sm` = mobile drawer + slim top bar | Matches BL-020's explicit mobile contract; changing the product breakpoint requires stakeholder approval, not an architecture-only deviation |
| D5 | BL-020 widths | Expanded `w-60` (240px) ↔ rail `w-16` (64px); content `sm:pl-60` / `sm:pl-16` with `transition-[padding]` | Matches backlog "~240 / ~64" |
| D6 | BL-020 collapse toggle | Chevron button (`PanelLeftClose`/`PanelLeftOpen`) in sidebar header row, right of brand; `aria-expanded`; state `openportfo.sidebar.collapsed = "1"\|"0"` | Standard app-shell pattern |
| D7 | BL-020 hydration for collapse state | `useState(false)` + read localStorage in `useEffect` (mounted-guard, same as `UserMenu`) | `useState` initializer would hydrate-mismatch under static export; a one-frame width settle for collapsed users is acceptable (not FOUC-critical) |
| D8 | BL-020 fate of Header/NavItems/UserMenu | **Delete** `Header.tsx`, `NavItems.tsx` (+tests), `UserMenu.tsx` (+test), `LanguageSelect.tsx`, `CurrencySelect.tsx`; remove now-unused `NAV_ITEMS` and `MOCK_USER` exports from `lib/mock-data.ts`. Profile/token logic moves to `lib/use-auth-profile.ts` and is instantiated once by `AppShell`, then passed to shell children/modal. | Mobile drawer + sidebar replace all header roles; `FxRatesPanel` is kept at its actual path `components/currency/FxRatesPanel.tsx` |
| D9 | BL-020 ChatWidget overlap | Keep chat behavior, but add a shell `leftInset` contract so launcher/panel clamping respects 240px expanded / 64px collapsed on `sm+`, and 0 below `sm`. Drawer z-index is above chat. | Satisfies BL-020's explicit "must not overlap sidebar" requirement, including user-dragged positions |
| D10 | BL-021 theming mechanism | Keep `@theme` (dark defaults + var registration); append **unlayered** `:root {light values}` + `.dark {dark values}` blocks in `globals.css`; add `@custom-variant dark`. Existing literal classes (`bg-gray-800` etc.) flip with **zero component edits** | **Validated against this repo's compiled CSS**: utilities emit `var(--color-gray-800)` and theme vars live in `@layer theme { :root,:host }`; unlayered rules always beat layered rules; `.dark` (0,1,0) declared after `:root` (0,1,0) wins on source order |
| D11 | BL-021 default theme | Stored `openportfo.theme` = `light`\|`dark`; absent → **dark**. No `prefers-color-scheme` | Product is dark-first today; avoids surprise for existing users; one-click switch in modal |
| D12 | BL-021 FOUC | Inline `<script>` as **first child of `<body>`** in root layout (static-export safe): toggles `dark` class + sets `<html lang>` pre-paint; `<html lang="en" className="dark" suppressHydrationWarning>` | Same technique as next-themes without the dep; proven under static export |
| D13 | BL-021 language infra | `lib/i18n.ts` flat EN/VI dictionary (~24 chrome keys) + `components/LanguageProvider.tsx` context; `openportfo.language`; page content stays EN | Backlog recommends chrome-only; dictionary list fixed in §7.4 |
| D14 | BL-021 apply model | Every selection applies instantly (no Save button) — confirmed | Backlog UX note; matches CurrencyProvider behavior |
| D15 | BL-022 style | **`notionists`** | CC0 (no attribution), hand-drawn professional look purpose-built for productivity tools, legible at 32–40px |
| D16 | BL-022 seed | **`userId`**, fallback `email` (`avatarSeedFor`) | `fetchAuthMe` validates `userId` non-empty; userId survives email changes |
| D17 | BL-022 guest/offline | Signed out → lucide `User` icon fallback; image load error → Radix `AvatarFallback` (2-letter initials) automatically | Acceptance criteria |
| D18 | Market group in rail mode | Rail flattens: Stock and Crypto render as their own icon rows (Market header row hidden) | Keeps rail at 5–6 icons, no nested flyouts |

---

## 4. Storage key registry (single source of truth)

| Constant (export) | Key | Storage | Owner file |
|---|---|---|---|
| `AUTH_TOKEN_STORAGE_KEY` | `openportfo.accessToken` | sessionStorage | `lib/auth.ts` |
| `LEGACY_AUTH_TOKEN_STORAGE_KEY` | `artryx.accessToken` | both (read-compat + migration) | `lib/auth.ts` |
| `PKCE_STORAGE_KEY` | `openportfo.pkce` | sessionStorage | `lib/cognito.ts` |
| `LEGACY_PKCE_STORAGE_KEY` | `artryx.pkce` | sessionStorage | `lib/cognito.ts` |
| `DISPLAY_CURRENCY_STORAGE_KEY` | `openportfo.displayCurrency` | localStorage | `lib/currency.ts` |
| `LEGACY_DISPLAY_CURRENCY_STORAGE_KEY` | `artryx.displayCurrency` | localStorage | `lib/currency.ts` |
| `marketsCacheKey()` | `openportfo.markets.{heatmap\|quotes}.{stock\|crypto}` | sessionStorage | `lib/markets-cache.ts` |
| `THEME_STORAGE_KEY` | `openportfo.theme` | localStorage | `lib/theme.ts` (new) |
| `LANGUAGE_STORAGE_KEY` | `openportfo.language` | localStorage | `lib/i18n.ts` (new) |
| `SIDEBAR_COLLAPSED_STORAGE_KEY` | `openportfo.sidebar.collapsed` | localStorage | `components/sidebar/Sidebar.tsx` (new) |
| `POSITION_KEY` | `openportfo.chat-bubble-position.v1` | localStorage | `components/chat/ChatWidget.tsx` (unchanged) |

---

## 5. BL-019 — Rebrand + storage migration

### 5.1 Migration module

```ts
// frontend/lib/storage-migration.ts (new)
export const STORAGE_PREFIX = "openportfo.";
export const LEGACY_STORAGE_PREFIX = "artryx.";

/** "openportfo.foo" -> "artryx.foo" (identity when no prefix). */
export function legacyKeyFor(key: string): string;

/** Read new key, fall back to legacy key. Reads never migrate. */
export function readMigrated(storage: Pick<Storage,"getItem"> | null, key: string): string | null;

/** One-time, idempotent. Returns list of keys migrated. Never call from render. */
export function runStorageMigration(win?: {
  localStorage?: Pick<Storage,"getItem"|"setItem"|"removeItem"> | null;
  sessionStorage?: Pick<Storage,"getItem"|"setItem"|"removeItem"> | null;
}): string[];
```

- Storage-location rules are explicit, not a generic "each key in each storage" loop:
  - PKCE and the four markets cache keys migrate **sessionStorage → sessionStorage**.
  - Display currency migrates **localStorage → localStorage**.
  - Auth is special. Candidate precedence is `session[new]` → `session[legacy]` → `local[new]` → `local[legacy]`. The winner is copied to `session[new]`; no new or legacy access token may remain in localStorage. If a session write fails, retain an existing `session[legacy]` fallback, but delete persistent local token copies (fail closed for a local-only token). Once `session[new]` exists, remove `session[legacy]` and both local copies.
- For a same-storage preference/cache key: new absent + legacy present → write new, then remove legacy only after the write succeeds; both present → new wins and legacy is removed; nothing present → no-op. Wrap each storage operation defensively because property access and calls can throw.
- `readAuthToken()` repeats the auth precedence/cleanup behavior so direct library use remains safe even if the bootstrap was blocked. `clearAuthToken()` removes new + legacy keys from both storages. Explicitly injected storage retains deterministic semantics: read new then legacy in that one supplied store, and do not infer/cross-write another store.
- Export a self-contained `CLIENT_BOOTSTRAP_SCRIPT` from `lib/storage-migration.ts`. Root `app/layout.tsx` renders it as the **first child of `<body>`**, before `<Providers>`, and the same script also applies theme and `<html lang>`. This is the only production startup call site. Do not call `runStorageMigration()` in `Providers`, a state initializer, `useMemo`, or any component render.
- Test both `runStorageMigration()` and execution of `CLIENT_BOOTSTRAP_SCRIPT` against fake storage objects so the pre-React path cannot drift from the tested helper.

### 5.2 Read-compat wiring

- `lib/auth.ts`: implement the browser-default auth precedence/cleanup contract above. Add `isAuthTokenStorageKey(key: string | null): boolean` (new ∪ legacy) and use it in both `ChatWidget` and `CurrencyProvider` storage listeners (the latter currently checks only `AUTH_TOKEN_STORAGE_KEY`).
- `lib/cognito.ts` `readPkceSession`, `lib/currency.ts` `readStoredDisplayCurrency`, `lib/markets-cache.ts` `readMarketsCache`: same new-then-legacy read.
- Writes always target the new key only.

### 5.3 Occurrence checklist (rename to OpenPortfo / openportfo)

| Location | Change |
|---|---|
| `package.json` name | `openportfo`; regenerate lockfile root name via `npm install --package-lock-only` |
| `components/BrandLogo.tsx` | brand text `OpenPortfo` (BrandMark colors stay hardcoded — logo is theme-invariant) |
| `components/dashboard/Sparkline.tsx` | gradient id → `openportfo-spark-fill` |
| auth-gate copy: `AssetDetailView.tsx`, `PortfolioDashboard.tsx`, `WatchlistView.tsx`, `SearchDialog.tsx` | hint text → `openportfo.accessToken` |
| `components/chat/ChatWidget.tsx` | storage-event key via `isAuthTokenStorageKey` |
| `lib/mock-data.ts` | remove unused `MOCK_USER` and `NAV_ITEMS` after their only consumers are deleted/replaced |
| tests: `lib/auth.test.ts`, `lib/cognito.test.ts`, `lib/currency.test.ts`, `lib/markets-cache.test.ts`, `MarketQuotes.test.tsx`, `StockHeatmap.test.tsx`, `SearchDialog.test.tsx`, `UserMenu.test.tsx` | key/copy literals → new keys |
| `frontend/README.md` | rewrite brand + key references (states current behavior → must change) |
| backlog docs under `docs/backlog/` | append a dated note "keys are now `openportfo.*`"; do not rewrite history sections |

Acceptance exception: legacy constants (`LEGACY_*` in §4) are the only `artryx` strings allowed under `frontend/`.

---

## 6. BL-022 — DiceBear avatars

### 6.1 `frontend/lib/avatar.ts` (new)

```ts
export const DICEBEAR_API_BASE = "https://api.dicebear.com/9.x";
export const DEFAULT_AVATAR_STYLE = "notionists";   // CC0, hand-drawn, legible at 32-40px

/** Curated list for the future Avatar settings tab (BL-023) — do not trim. */
export const AVATAR_STYLES = [
  "notionists", "notionists-neutral", "adventurer-neutral", "big-smile",
  "lorelei", "bottts", "thumbs", "shapes",
] as const;
export type AvatarStyle = (typeof AVATAR_STYLES)[number];

export type AvatarOptions = {
  seed: string;                       // required, deterministic
  style?: AvatarStyle;                // default DEFAULT_AVATAR_STYLE; never interpolate an arbitrary path segment
  backgroundColor?: string | null;    // "#0ed2a8" | "0ed2a8" | null -> omitted when null/invalid
  size?: number;                      // px, positive int -> omitted when invalid
};

/** Pure/deterministic: same input -> same URL.
 *  https://api.dicebear.com/9.x/notionists/svg?seed=<enc>&backgroundColor=0ed2a8&size=64 */
export function buildAvatarUrl(options: AvatarOptions): string;

/** Normalize "#RRGGBB"/"RRGGBB"/"#RGB" -> "RRGGBB"; null when invalid. */
export function normalizeHexColor(raw: string | null | undefined): string | null;

/** Stable identity seed: userId || email || null. */
export function avatarSeedFor(profile: { userId?: string; email?: string } | null | undefined): string | null;

/** Up to 2 uppercase initials from name||email ("Ada Lovelace" -> "AL"); "" when none. */
export function profileInitials(profile: { name?: string | null; email?: string | null } | null | undefined): string;
```

Repository contract (from BL-022): `https://api.dicebear.com/9.x/<style>/svg?seed=…`; `backgroundColor` is emitted without `#` and `size` only for a positive integer. Build the query with `URLSearchParams`; tests assert decoded `url.searchParams` values rather than a particular space encoding (`+` versus `%20`). No runtime fetch is performed by the helper.

### 6.2 `frontend/components/UserAvatar.tsx` (new)

```tsx
type UserAvatarProps = {
  profile?: { userId?: string; email?: string; name?: string | null } | null;
  size?: number;                 // px, default 32
  avatarStyle?: AvatarStyle;     // BL-023 extension point (overrides default)
  avatarSeed?: string;           // BL-023 extension point
  avatarColor?: string | null;   // BL-023 extension point
  className?: string;
};
```

- Uses shadcn `Avatar` + `AvatarImage` + `AvatarFallback` (AvatarImage is exercised for the first time).
- Resolution: explicit `avatarSeed/avatarStyle/avatarColor` props win; else seed = `avatarSeedFor(profile)`, style = `notionists`, color = none (transparent — the `Avatar` root supplies `bg-gray-700`, theme-aware).
- Signed out / no seed → no `AvatarImage`; `AvatarFallback` renders the lucide `User` icon (sr-only "Guest").
- Signed in + image fails (offline) → `AvatarFallback` shows `profileInitials` (2 letters). First test the Radix loading-status behavior with `fireEvent.error`; if jsdom does not expose it reliably, keep explicit local image-error state and reset it whenever the computed URL changes.
- Static-export safe: no next/image anywhere.

---

## 7. BL-021 — Theming + i18n + settings modal

### 7.1 `globals.css` dual palette (final mechanism)

```css
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));   /* class-based dark: variant, if ever needed */

@theme { /* UNCHANGED — registers vars + dark build-time defaults */ }

/* ---- runtime palettes (UNLAYERED — beats @layer theme; .dark after :root wins on order) ---- */
:root  { /* light values */ }
.dark  { /* dark values  */ }
```

**Cascade rules (verified against `.next/static/chunks/*.css`):** utilities emit `background-color: var(--color-gray-800)`; theme vars are emitted under `@layer theme { :root,:host }`; unlayered declarations always override layered ones. **Every variable declared in the `:root` block MUST also be declared in the `.dark` block** (otherwise the light value would leak into dark mode).

`html, body { background: var(--color-gray-900); color: var(--color-gray-400); }` already use vars → flip automatically.

### 7.2 Palette tables

Gray ramp (roles verified by usage census: bg=950/900/800/700/600, text=500/400/300/200/100, border=600/700/800):

| Variable | Dark (current/default) | Light |
|---|---|---|
| `--color-gray-950` | `#030712` | `#eef2f2` |
| `--color-gray-900` | `#050505` | `#f6f8f8` |
| `--color-gray-800` | `#141414` | `#ffffff` |
| `--color-gray-700` | `#212328` | `#e8eded` |
| `--color-gray-600` | `#30333a` | `#d4dcdc` |
| `--color-gray-500` | `#9095a1` | `#5b6670` |
| `--color-gray-400` | `#ccdadc` | `#333b44` |
| `--color-gray-300` | `#d4d4d8` *(pin TW default)* | `#4a545e` |
| `--color-gray-200` | `#e8eeee` | `#222a31` |
| `--color-gray-100` | `#f4f7f7` | `#0e1416` |

Teal / semantic (gray-300 and gray-950 were previously undeclared Tailwind defaults — they MUST be pinned now because they flip):

| Variable | Dark | Light |
|---|---|---|
| `--color-teal-400` | `#0fedbe` | `#0f766e` |
| `--color-teal-500` | `#0ed2a8` | `#0d9488` |
| `--color-teal-950` | `#042f28` | `#ffffff` |
| `--color-teal-300` | `#5eead4` | `#0f766e` |
| `--color-teal-200` | `#99f6e4` | `#115e59` |
| `--color-primary` | `#0fedbe` | `#0f766e` |
| `--color-primary-foreground` | `#042f28` | `#ffffff` |
| `--color-accent` | `#212328` | `#e8eded` |
| `--color-accent-foreground` | `#f4f7f7` | `#1d2429` |
| `--color-muted` | `#212328` | `#e8eded` |
| `--color-ring` | `#0fedbe` | `#0f766e` |
| `--color-background` | `#050505` | `#f6f8f8` |
| `--color-foreground` | `#ccdadc` | `#333b44` |

Status colors (red/amber/emerald steps are currently TW defaults used as *text on dark* — pin dark values, flip for light):

| Variable | Dark | Light |
|---|---|---|
| `--color-red-500` | `#ff495b` | `#dc2626` |
| `--color-red-400` | `#ff6568` | `#b91c1c` |
| `--color-red-300` | `#ffa3a3` | `#dc2626` |
| `--color-red-200` | `#ffcaca` | `#b91c1c` |
| `--color-red-100` | `#ffe2e2` | `#fee2e2` |
| `--color-amber-500` | `#f59e0b` | `#d97706` |
| `--color-amber-400` | `#fbbf24` | `#b45309` |
| `--color-amber-300` | `#fcd34d` | `#92400e` |
| `--color-amber-200` | `#fee685` | `#78350f` |
| `--color-amber-100` | `#fef3c6` | `#78350f` |
| `--color-emerald-400` | `#34d399` | `#047857` |

Chat bubbles (currently hardcoded gradients in `globals.css`) become custom props (declared in the same `:root`/`.dark` blocks, consumed by the existing `.chat-message-bubble--*` rules):

| Variable | Dark | Light |
|---|---|---|
| `--chat-user-bubble-bg` | `linear-gradient(135deg, rgb(4 78 66/.94), rgb(4 47 40/.78))` | `linear-gradient(135deg, rgb(15 118 110/.92), rgb(13 148 136/.85))` |
| `--chat-user-bubble-text` | `#e9fffa` | `#f0fdfa` |
| `--chat-assistant-bubble-bg` | `linear-gradient(150deg, rgb(33 35 40/.98), rgb(20 20 20/.92))` | `linear-gradient(150deg, rgb(255 255 255/.98), rgb(240 245 245/.95))` |
| `--chat-assistant-bubble-text` | `#ccdadc` | `#26313a` |

### 7.3 Theme plumbing

```ts
// frontend/lib/theme.ts (new)
export const THEME_STORAGE_KEY = "openportfo.theme";
export type Theme = "light" | "dark";
export const DEFAULT_THEME: Theme = "dark";
export function resolveTheme(raw: string | null): Theme;          // "light" -> light, else dark
export function applyTheme(theme: Theme): void;                   // html.classList add/remove "dark"
// Theme helpers are imported by providers; the combined pre-React script is
// CLIENT_BOOTSTRAP_SCRIPT from storage-migration.ts.
```

The theme/language fragment is included in `CLIENT_BOOTSTRAP_SCRIPT`, which is the **first child of `<body>`** in `app/layout.tsx` (executes before first paint; static-export safe). It runs storage migration first, then:

```js
(function(){try{var d=document.documentElement;
if(localStorage.getItem("openportfo.theme")==="light"){d.classList.remove("dark")}else{d.classList.add("dark")}
var l=localStorage.getItem("openportfo.language");if(l==="vi"||l==="en"){d.setAttribute("lang",l)}
}catch(e){}})();
```

Root layout html tag becomes: `<html lang="en" className="dark" suppressHydrationWarning>`.

```tsx
// frontend/components/ThemeProvider.tsx (new)
type ThemeContextValue = { theme: Theme; setTheme: (t: Theme) => void; mounted: boolean };
```
- Mount: `resolveTheme(localStorage.getItem(...))` → state (no DOM write needed; script already applied; call `applyTheme` anyway for safety).
- `setTheme`: state + `applyTheme` + `localStorage.setItem` (try/catch).

### 7.4 i18n

```ts
// frontend/lib/i18n.ts (new)
export const LANGUAGE_STORAGE_KEY = "openportfo.language";
export const LANGS = ["en", "vi"] as const;
export type Lang = (typeof LANGS)[number];
export const DEFAULT_LANG: Lang = "en";
export function resolveLang(raw: string | null): Lang;            // "vi" -> vi, else en
export function translate(lang: Lang, key: string): string;       // dict[lang] ?? dict.en ?? key
```

```tsx
// frontend/components/LanguageProvider.tsx (new)
type LanguageContextValue = { lang: Lang; setLang: (l: Lang) => void };
export function useT(): (key: string) => string;                  // bound translate
```
- Mount: read `openportfo.language` (mounted-guard). `setLang`: state + persist + `document.documentElement.lang = lang` (imperative — no hydration involvement).

Dictionary — exact chrome keys (EN → VI):

| Key | EN | VI |
|---|---|---|
| `nav.market` | Market | Thị trường |
| `nav.market.stock` | Stock | Cổ phiếu |
| `nav.market.crypto` | Crypto | Tiền mã hóa |
| `nav.portfolio` | Portfolio | Danh mục |
| `nav.watchlist` | Watchlist | Theo dõi |
| `nav.search` | Search | Tìm kiếm |
| `nav.collapse` | Collapse sidebar | Thu gọn thanh bên |
| `nav.expand` | Expand sidebar | Mở rộng thanh bên |
| `nav.openMenu` | Open navigation menu | Mở menu điều hướng |
| `settings.title` | Settings | Cài đặt |
| `settings.appearance` | Appearance | Giao diện |
| `settings.appearance.light` | Light | Sáng |
| `settings.appearance.dark` | Dark | Tối |
| `settings.language` | Language | Ngôn ngữ |
| `settings.language.en` | English | English |
| `settings.language.vi` | Tiếng Việt | Tiếng Việt |
| `settings.currency` | Display currency | Tiền tệ hiển thị |
| `settings.fxRates` | View FX rates… | Xem tỷ giá… |
| `settings.account.guest` | Guest | Khách |
| `settings.account.signedOut` | Not signed in | Chưa đăng nhập |
| `settings.signIn` | Sign in | Đăng nhập |
| `settings.signOut` | Sign out | Đăng xuất |
| `common.close` | Close | Đóng |
| `search.placeholder` | Search symbols or companies | Tìm mã cổ phiếu hoặc công ty |

Page/dashboard content stays English (documented out of scope). `SearchDialog` placeholder switches to `useT()("search.placeholder")`.

### 7.5 `frontend/components/UserSettingsModal.tsx` (new)

Props: `{ open: boolean; onClose: () => void }` — hand-rolled, same pattern as `SearchDialog`/`FxRatesPanel`:

- Backdrop `fixed inset-0 z-[80] bg-black/60` (click → close); panel `w-full max-w-md rounded-xl border border-gray-600 bg-gray-800 shadow-2xl`; Escape closes. Body scroll lock is owned once by `AppShell`, not independently by every overlay.
- A11y: `role="dialog" aria-modal="true" aria-labelledby` pointing to the visible title; on open, remember `document.activeElement` and focus the close button; on close, restore focus. Tab/Shift+Tab must wrap among modal controls (a small reusable `useDialogFocus` helper is allowed; no dependency).
- Instant-apply sections (no Save):
  1. **Account header** — `UserAvatar` + display name/email (`useAuthProfile`) or `t("settings.account.signedOut")`; small outline button `Sign in` (`beginHostedUiLogin({ next: pathname })`) or `Sign out` (`logoutFromApp()`, then reload state) — signed-out users can still use theme/language/currency.
  2. **Appearance** (`role="radiogroup"`): rows Light (Sun icon) / Dark (Moon icon), `aria-checked`, selected row `border-teal-400 bg-teal-400/10 text-gray-100`; calls `setTheme`.
  3. **Language**: rows English / Tiếng Việt (Languages icon); calls `setLang`.
  4. **Currency**: render rows from `DISPLAY_CURRENCIES` (Coins icon) calling `useDisplayCurrency().setCurrency` (all formatted values re-render via existing provider); footer button `t("settings.fxRates")` → opens `components/currency/FxRatesPanel.tsx` above the kept settings modal.
- Nested FX contract: while FX is open, the settings Escape handler is suspended and its panel is `aria-hidden`/non-interactive; otherwise one Escape would close both overlays. Enhance `FxRatesPanel` to focus its close button on open and return focus to the FX trigger on close. AppShell keeps `settingsOpen=true`, so its single body-lock remains active throughout.

### 7.6 Providers

```tsx
// frontend/components/Providers.tsx (modified)
"use client";
export default function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <CurrencyProvider>{children}</CurrencyProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}
```

`Providers` must remain render-pure. The bootstrap script has already run before React hydrates; consumer helpers retain legacy fallbacks as defense in depth.

---

## 8. BL-020 — Sidebar app shell

### 8.1 Component tree

```
app/layout.tsx (server)
└─ <body>
   ├─ <script>CLIENT_BOOTSTRAP_SCRIPT</script>       (migration + theme/lang, pre-React/pre-paint)
   └─ <Providers>                                   (theme + language + currency; render-pure)
      ├─ <AppShell>                                 components/AppShell.tsx (new, client)
      │  ├─ <Sidebar />                             components/sidebar/Sidebar.tsx        (hidden sm:flex)
      │  │  ├─ brand row: BrandLogo | BrandMark + collapse toggle (PanelLeftClose/Open)
      │  │  ├─ <SidebarNav collapsed onNavigate onSearch />         components/sidebar/SidebarNav.tsx
      │  │  ├─ <div flex-1 />
      │  │  └─ <SidebarUserChip collapsed onOpenSettings />         components/sidebar/SidebarUserChip.tsx
      │  ├─ <MobileTopbar menuOpen onMenu onOpenSettings /> components/sidebar/MobileTopbar.tsx (sm:hidden)
      │  ├─ MobileDrawer (inline in AppShell)       overlay + panel reusing SidebarNav + SidebarUserChip
      │  ├─ <div className={(collapsed ? "sm:pl-16" : "sm:pl-60") + " transition-[padding] duration-200"}>
      │  │   └─ <main className="container py-10">{children}</main>
      │  ├─ <SearchDialog open onClose />           (Cmd/Ctrl+K listener lives here now)
      │  ├─ <UserSettingsModal open onClose auth={auth} />
      │  └─ <ChatWidget leftInset={desktop ? (collapsed ? 64 : 240) : 0} />
```

### 8.2 Contracts

```tsx
// components/sidebar/Sidebar.tsx
export const SIDEBAR_COLLAPSED_STORAGE_KEY = "openportfo.sidebar.collapsed"; // "1" | "0"; absent = expanded
type SidebarProps = {
  collapsed: boolean;
  onToggleCollapsed: () => void;
};
// hidden sm:flex fixed inset-y-0 left-0 z-40 w-60|w-16 border-r border-gray-600 bg-gray-800
// transition-[width] duration-200; collapsed state owned by AppShell (hydration-safe:
// useState(false) + read/persist in useEffect; toggling writes "1"/"0").

// components/sidebar/SidebarNav.tsx
type SidebarNavProps = {
  collapsed: boolean;
  onNavigate?: () => void;      // drawer: close after link click
  onSearch: () => void;         // opens SearchDialog
};
// Renders from a declarative table (extension point for BL-023/024):
//   { href, labelKey, icon } — Portfolio (Briefcase), Watchlist (Star), Search (Search button + ⌘K hint)
//   Market group (LayoutDashboard header, expandable, children Stock=TrendingUp / Crypto=Bitcoin)
// Icons imported from lucide-react (all verified present except CandlestickChart — do not use it).
// Expanded row: icon + t(labelKey), rounded-lg px-3 py-2, active = bg-gray-700/60 text-gray-100 +
//   2px teal left bar; inactive text-gray-500; hover bg-gray-700/50 text-gray-200.
// Rail: icons centered, label hidden but present via title/aria-label; Market group flattens to
//   Stock + Crypto icon rows (D18). Market group open state is local useState(true), not persisted.
// Active detection: copy normalizePath + MARKET_ACTIVE set from NavItems.tsx.

// components/sidebar/SidebarUserChip.tsx
type SidebarUserChipProps = { collapsed: boolean; onOpenSettings: () => void };
// UserAvatar (size 36) button -> onOpenSettings; truncated name/email when expanded
// (hydrated/loading -> "…"); adjacent icon button (LogIn | LogOut, title) for direct auth actions,
// reusing UserMenu's beginHostedUiLogin/logoutFromApp logic. Rail: avatar + icon stacked.

// components/sidebar/MobileTopbar.tsx
type MobileTopbarProps = {
  menuOpen: boolean;
  menuButtonRef?: Ref<HTMLButtonElement>;
  onMenu: () => void;
  onOpenSettings: () => void;
};
// sm:hidden sticky top-0 z-40 h-14 border-b border-gray-600 bg-gray-800:
// hamburger (Menu icon, aria-expanded={menuOpen}, aria-controls="mobile-sidebar-drawer",
// aria-label=t("nav.openMenu")) + BrandLogo + UserAvatar button.

// lib/use-auth-profile.ts (new hook — extracted from UserMenu; also feeds BL-024 admin gating)
export function useAuthProfile(): {
  hydrated: boolean; token: string | null; profile: AuthProfile | null;
  loading: boolean; error: string | null;
  signIn: (next?: string) => void;   // beginHostedUiLogin, sets error on failure
  signOut: () => void;               // logoutFromApp + clears local state
};
// Re-fetches on AUTH_CHANGE_EVENT + token storage events; clears token on 401/403 (authRequired).
// AppShell calls this hook once and passes the returned controller to SidebarUserChip and
// UserSettingsModal; do not mount two shell-level copies that duplicate /api/auth/me requests.

// components/AppShell.tsx
type AppShellProps = { children: ReactNode };
// State: searchOpen, settingsOpen, drawerOpen, collapsed(+mounted read/persist).
// Effects: Cmd/Ctrl+K -> open SearchDialog (and close drawer/settings); Escape closes drawer;
// usePathname change and a transition to sm+ close drawer; one AppShell effect owns body scroll
// lock for drawer/search/settings (including the nested FX panel) so overlays cannot restore it early.
// Drawer: overlay fixed inset-0 z-[60] bg-black/60 + panel fixed inset-y-0 left-0 z-[61]
//   w-64 max-w-[85vw] bg-gray-800 border-r border-gray-600, conditionally mounted while open;
//   focus its close button on open, keep a labelled dialog surface, and return focus to hamburger on close.
// z-order scale: sidebar/topbar 40 < chat 50/51 < drawer 60/61 < search+settings 80 < FX 100.
```

### 8.3 Deletions & CSS cleanup

- Delete `components/Header.tsx`, `components/NavItems.tsx` (+`NavItems.test.tsx`), `components/UserMenu.tsx` (+`UserMenu.test.tsx`), `components/CurrencySelect.tsx`, `components/LanguageSelect.tsx`.
- Delete the now-unused `NAV_ITEMS` and `MOCK_USER` exports from `lib/mock-data.ts`; the translated declarative table belongs with `SidebarNav` (or a new pure `lib/navigation.ts` if test reuse warrants it).
- Keep `components/currency/FxRatesPanel.tsx` (opened from the modal).
- `globals.css`: remove now-dead `.header`, `.header-wrapper`, `.search-text` utilities (grep confirms no other consumers). `container` utility unchanged.
- Replace stale shell copy: `ChatPanel.tsx` "account menu in the header" → settings/avatar wording; `PortfolioDashboard.tsx` "header switcher" → settings; `lib/asset-search.ts` header-only comment → app-shell search; update their affected assertions.

### 8.4 Light-mode polish pass (hardcoded colors that vars cannot flip)

| File | Change |
|---|---|
| `components/dashboard/Sparkline.tsx` | gradient id (BL-019) + `stroke`/`stopColor` `#0FEDBE` → `style={{ stroke: "var(--color-teal-400)" }}` etc. (SVG presentation attributes do not resolve `var()`, use style) |
| `components/asset/AssetHistoryChart.tsx` | same `#0FEDBE` → vars |
| `components/portfolio/PortfolioValueChart.tsx` | same `#0FEDBE` → vars |
| `components/dashboard/StockHeatmap.tsx` | `bg-[#141414]` (3) → `bg-gray-800` |
| `components/portfolio/AllocationPie.tsx` | inner-circle `fill="#141414"` → `style` with `var(--color-gray-800)` |
| `components/chat/ChatComposer.tsx` | `placeholder:text-gray-600` / `text-gray-600` → `text-gray-500` (600 is a border step in the light ramp; only 2 occurrences) |
| `components/BrandLogo.tsx` | keep hardcoded hex (logo is theme-invariant) |

---

## 9. Implementation order (each step ends green: `npm test` + `npm run build`)

| Step | Content | Exit check |
|---|---|---|
| 1 | **BL-019**: storage-migration lib + key renames + read-compat + copy/brand/test/doc renames + lockfile | migration tests pass; suite green; grep shows only `LEGACY_*` "artryx" strings |
| 2 | **BL-022**: `lib/avatar.ts` + `UserAvatar.tsx` (+tests) — not yet wired into UI | avatar tests pass |
| 3 | **BL-021 infra**: globals.css palettes + custom variant + chat vars; `lib/theme.ts`; ThemeProvider; `lib/i18n.ts`; LanguageProvider; layout `<html>`/inline script | suite green; manual toggle of `.dark` class flips app |
| 4 | **BL-021 modal**: `UserSettingsModal.tsx` + currency/FX wiring (+tests); `SearchDialog` placeholder i18n | modal tests pass (still reachable only via old header temporarily) |
| 5 | **BL-020 shell**: `use-auth-profile` hook; AppShell + Sidebar + SidebarNav + SidebarUserChip + MobileTopbar + drawer; rewire `layout.tsx`; add ChatWidget left-inset integration; delete Header/NavItems/UserMenu/CurrencySelect/LanguageSelect and unused mock nav/user exports (+tests); globals/copy cleanup | new shell and chat clamp tests pass; full suite green |
| 6 | **Polish + close-out**: light-mode hardcoded-color pass (§8.4); README/backlog notes; `npm run build` static export verified; manual light/dark smoke on `/markets/stock`, `/markets/crypto`, `/portfolio`, `/watchlist`, `/asset`, chat | build succeeds; no invisible text on key screens |

---

## 10. File-by-file change list

**New (14 + tests):** `lib/storage-migration.ts`, `lib/avatar.ts`, `lib/theme.ts`, `lib/i18n.ts`, `lib/use-auth-profile.ts`, `components/ThemeProvider.tsx`, `components/LanguageProvider.tsx`, `components/UserAvatar.tsx`, `components/UserSettingsModal.tsx`, `components/AppShell.tsx`, `components/sidebar/Sidebar.tsx`, `components/sidebar/SidebarNav.tsx`, `components/sidebar/SidebarUserChip.tsx`, `components/sidebar/MobileTopbar.tsx` — plus colocated tests for each (except `MobileTopbar`, covered via `AppShell.test.tsx`).

**Modified:** `app/layout.tsx`, `app/globals.css`, `components/Providers.tsx`, `lib/auth.ts`, `lib/cognito.ts`, `lib/currency.ts`, `lib/markets-cache.ts`, `lib/mock-data.ts` (remove unused nav/user exports), `lib/asset-search.ts` (stale header comment), `components/BrandLogo.tsx`, `components/SearchDialog.tsx` (copy + placeholder + focus return), `components/currency/FxRatesPanel.tsx` (nested-dialog focus), `components/chat/ChatWidget.tsx` (auth event key + left inset), `components/chat/ChatLauncher.tsx` / `ChatPanel.tsx` (z-order/copy as needed), `components/dashboard/Sparkline.tsx`, `components/asset/AssetHistoryChart.tsx`, `components/portfolio/PortfolioValueChart.tsx`, `components/dashboard/StockHeatmap.tsx`, `components/portfolio/AllocationPie.tsx`, `components/chat/ChatComposer.tsx`, auth-gate/copy in `components/asset/AssetDetailView.tsx` + `components/portfolio/PortfolioDashboard.tsx` + `components/watchlist/WatchlistView.tsx`, `package.json` (+lockfile), `README.md`, backlog docs (notes), and directly affected tests.

**Deleted:** `components/Header.tsx`, `components/NavItems.tsx` + test, `components/UserMenu.tsx` + test, `components/CurrencySelect.tsx`, `components/LanguageSelect.tsx`.

---

## 11. Test plan

| Test file | Cases |
|---|---|
| `lib/storage-migration.test.ts` | PKCE/cache session→session; currency local→local; exact auth four-slot precedence; local-only old/new token moves to session-new and both local copies are deleted; session-new wins; session-old fallback retained if session-new write throws; local-only token deleted if session write throws; idempotence; property/method throws; execute `CLIENT_BOOTSTRAP_SCRIPT` and assert parity/final storage |
| `lib/auth.test.ts` (extend) | browser read order `S-new > S-old > L-new > L-old`; all successful paths finish at S-new with no local token; failed S write retains S-old but deletes persistent copies; failed local-only migration fails closed; explicit storage reads new then legacy only; clear removes both prefixes in both stores; `isAuthTokenStorageKey` accepts both and null safely |
| `lib/cognito.test.ts`, `lib/currency.test.ts`, `lib/markets-cache.test.ts` (extend) | new-key read, legacy fallback, new-key-only write |
| `lib/avatar.test.ts` | deterministic URL; default/allowed style; URL/searchParams preserve seed; arbitrary style cannot alter API path; hex normalization (`#0ed2a8`/`0ed2a8` → param, invalid → omitted); positive-integer `size` passthrough/drop; trimmed `avatarSeedFor` userId→email→null; `profileInitials` |
| `components/UserAvatar.test.tsx` | signed-in renders `img` with expected src; signed-out renders guest icon fallback (no img); image error renders initials; URL change clears explicit error fallback if used |
| `lib/theme.test.ts` + `components/ThemeProvider.test.tsx` | `resolveTheme`; stored light → `html.dark` removed + persisted; default dark; `setTheme` writes key |
| `lib/i18n.test.ts` + `components/LanguageProvider.test.tsx` | every EN key has a VI entry (completeness loop); persistence; `document.documentElement.lang` set |
| `components/UserSettingsModal.test.tsx` | open renders 3 sections; theme/language/currency wiring; FX button opens actual `FxRatesPanel`; first Escape closes only FX and returns to its trigger, second closes settings; backdrop close; initial focus, Tab wrap, final focus restore |
| `lib/use-auth-profile.test.ts` | token→profile fetch (mock fetch); 401 clears token; auth-change event refetches; signOut clears state |
| `components/sidebar/SidebarNav.test.tsx` | renders items with translated labels; active class per pathname (portfolio/watchlist/market paths); Market group expand/collapse (`aria-expanded`); Search button calls `onSearch`; rail mode hides labels, keeps `title`/`aria-label` |
| `components/sidebar/Sidebar.test.tsx` | controlled expanded/collapsed rendering; toggle callback; correct `aria-expanded`; no storage assertions (state is owned by AppShell) |
| `components/sidebar/SidebarUserChip.test.tsx` | click avatar → `onOpenSettings`; sign-in/out buttons call mocked cognito; loading/signed-out states |
| `components/AppShell.test.tsx` | absent storage defaults expanded; stored `"1"` hydrates collapsed; toggle persists `"1"/"0"`; renders nav; Cmd/Ctrl+K opens SearchDialog; hamburger has correct expanded/control state; drawer closes on link click, pathname change, Escape, backdrop, and sm+ media change; drawer focus/return; avatar opens settings; overlays are mutually exclusive and body lock restores once |
| `components/chat/ChatWidget.test.tsx` | existing suite plus expanded/rail/zero left inset clamping and re-clamp when inset changes; drawer/modal z-order does not leave chat controls above the overlay |
| Updated suites | `SearchDialog.test.tsx` (copy + placeholder), `MarketQuotes`/`StockHeatmap` tests (new cache keys) |

Conventions: mock `next/navigation`, `next/link`, `@/lib/cognito` (partial, like `UserMenu.test.tsx`), `vi.stubGlobal("fetch", ...)`, clear `sessionStorage`/`localStorage` in `beforeEach`/`afterEach`.

---

## 12. Acceptance mapping

| BL | Criterion → where satisfied |
|---|---|
| **019** | zero "artryx" except `LEGACY_*` (§5.3 grep step) · session survives rename (migration tests) · suite green · brand text "OpenPortfo" (`BrandLogo`) |
| **020** | no top navbar on desktop, avatar bottom-left (AppShell/Sidebar) · collapse + persistence + accessible rail labels (Sidebar tests) · mobile drawer close on navigate/Escape (AppShell tests) · Cmd+K works (AppShell) · sidebar unit tests · old NavItems/UserMenu tests replaced, suite green |
| **021** | avatar opens modal with 3 working sections · light+dark usable on key screens (§9 step 6 smoke + §8.4 polish) · theme+language persist without flash (inline script + provider tests) · currency drives formatting, FX panel reachable (modal tests) · unit tests · suite green |
| **022** | deterministic avatar keyed by stable identity (avatar tests + UserAvatar) · initials fallback signed-out/on error · URL builder + fallback tests · suite green |

---

## 13. Risks for the implementer

1. **Palette completeness** — every var in the light `:root` block must also exist in `.dark` (§7.1 cascade rule), including the pinned TW defaults (`gray-300/950`, teal-200/300, red/amber/emerald steps). Missing entries leak light values into dark mode.
2. **Hydration/bootstrap** — never read or mutate storage in React render or `useState` initializers. `CLIENT_BOOTSTRAP_SCRIPT` is the sole pre-React mutation path; providers use mounted effects. `<html>` needs `suppressHydrationWarning` because the script mutates class/lang pre-hydration.
3. **Sidebar width settle** — collapsed users see one expanded→rail transition after hydration (accepted, D7). Do not "fix" with an initializer.
4. **SVG `var()`** — presentation attributes (`stroke="#..."`) do not resolve CSS vars; use `style` objects (§8.4).
5. **ChatWidget** — preserve behavior but add/test `leftInset`; re-clamp stored and live positions when sidebar width changes. Chat stays above the desktop sidebar content plane but below drawers/dialogs; it must not visually overlap the sidebar.
6. **Market group in rail** — flatten, don't nest (D18); remember `title`/`aria-label` on icon-only buttons.
7. **Migration ordering/security** — execute `CLIENT_BOOTSTRAP_SCRIPT` before `Providers`; never call the helper from render. Treat auth separately from preference/cache keys and assert that neither prefix remains in localStorage whenever removal is possible.
8. **Lockfile** — after renaming `package.json`, run `npm install --package-lock-only` (root name in lockfile); CI/dev installs tolerate a mismatch but keep it clean.
9. **Batch-2 handoff** — keep `AVATAR_STYLES`, `UserAvatar` override props, the declarative nav table, `useAuthProfile`, and flat `Providers` exactly as specced; they are the extension points BL-023/024 consume.

---

## 14. Agent prompts (one per step)

```
Step 1 / BL-019 ONLY. Rename artryx->openportfo (keys via lib/storage-migration.ts +
pre-React CLIENT_BOOTSTRAP_SCRIPT + exact cross-storage auth handling + read-compat
fallbacks, brand text, copy, tests, docs). TDD the four-slot auth matrix first.
Do not touch layout/components beyond the occurrence list.
```

```
Step 2 / BL-022 ONLY. lib/avatar.ts (buildAvatarUrl seed/style/backgroundColor/size,
notionists default) + components/UserAvatar.tsx with initials/guest fallback. TDD.
No UI wiring yet.
```

```
Step 3 / BL-021 infra ONLY. globals.css dual palette (:root light / .dark dark,
@custom-variant, chat bubble props) + lib/theme.ts + ThemeProvider + lib/i18n.ts +
LanguageProvider + extend the existing bootstrap script's theme/lang fragment. Keep
Providers render-pure and @theme untouched. Suite must stay green.
```

```
Step 4 / BL-021 modal ONLY. components/UserSettingsModal.tsx (theme/language/currency,
FxRatesPanel entry, account header with sign in/out). Instant apply. TDD.
```

```
Step 5 / BL-020 ONLY. AppShell + sidebar components + use-auth-profile; rewire layout;
delete Header/NavItems/UserMenu/CurrencySelect/LanguageSelect (+tests); drawer + Cmd+K;
honor the sm breakpoint and add/test ChatWidget leftInset clamping.
TDD sidebar behavior first.
```

```
Step 6 / polish + close-out. Hardcoded-color pass (charts/heatmap/pie/composer),
README + backlog notes, npm run build (static export), light/dark smoke on
markets/portfolio/watchlist/asset/chat. Full suite green.
```
