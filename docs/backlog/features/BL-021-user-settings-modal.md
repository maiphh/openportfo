# BL-021 — User settings modal (theme / language / currency)

| Field | Value |
|-------|--------|
| **ID** | `BL-021` |
| **Title** | Avatar click opens modal to select light/dark theme, language, and currency |
| **Priority** | `P0` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Luna implementer |
| **Requested by** | Product |
| **Related PRD / sprint** | sprint-05; depends on BL-020 (avatar trigger) |
| **Created** | 2026-08-23 |
| **Ready date** | 2026-08-23 |
| **Done date** | 2026-08-23 |

---

## 1. Problem / user value

Today the app is **dark-only** (hardcoded `className="dark"`, single dark-valued `@theme` variables in Tailwind v4 `globals.css`), the `LanguageSelect` dropdown is **cosmetic** (no persistence/effect), and currency lives in a header dropdown that the sidebar redesign removes. Users need one place — opened from their avatar — to control **light/dark mode, language, and display currency**.

---

## 2. User story

As a **user**, I want **to click my avatar and pick light/dark mode, language, and currency in one modal**, so that **the app looks and reads the way I prefer**.

---

## 3. Scope

### In scope

- **User settings modal** (hand-rolled overlay pattern consistent with `SearchDialog`/`FxRatesPanel`): sections for Appearance (Light/Dark), Language (English/Tiếng Việt), Currency (reuse `DISPLAY_CURRENCIES` + `useDisplayCurrency`).
- **Real theming**: light + dark palettes. Recommended approach: keep Tailwind v4 `@theme` variables but override the `--color-*` values under `:root` (light) and `.dark` scopes so existing literal classes (`bg-gray-800` etc.) flip without a mass refactor — SA to validate/design final mechanism. Toggle applies `dark` class on `<html>`, persists to localStorage, no FOUC on load (inline script or suppression strategy — static export constraint).
- **Language**: persist choice (`openportfo.language`), set `<html lang>`. Translation scope (SA decision, pragmatic): app chrome strings (sidebar nav labels, settings modal, common actions) via a small EN/VI dictionary + context; full page-content i18n is out of scope.
- **Currency**: move selection into modal (replaces `CurrencySelect` header dropdown); keep FX rates panel accessible from modal ("View FX rates…" entry).
- Old `LanguageSelect` component retired or absorbed.

### Out of scope

- Full i18n of every page/dashboard string; RTL; more than 2 languages; per-account server-side persistence (client-side localStorage only).

---

## 4. Behaviour

### Happy path

1. Click avatar (sidebar bottom-left) → modal opens.
2. Toggle Light → palette flips instantly, persisted; reload keeps it.
3. Pick Tiếng Việt → chrome strings switch; `<html lang="vi">`; persisted.
4. Pick USD → all currency-formatted values re-render via existing CurrencyProvider.

### Edge cases / errors

- No stored theme → default dark (current behavior); respect `prefers-color-scheme` optionally (SA decision).
- Hydration: theme applied pre-paint without React hydration mismatch (mounted-guard for UI state, inline script for DOM class).
- Modal closes on Escape/backdrop; focus trap or at least focus return.

### UX notes

- Modal sections with radio-group style rows; each selection applies immediately (no Save button needed — SA to confirm).

---

## 5. Acceptance criteria

- [ ] Clicking avatar opens settings modal with three working sections.
- [ ] Light and dark modes both fully usable (no invisible text/contrast breakage on key screens: markets, portfolio, watchlist, asset, chat).
- [ ] Theme + language persist across reloads without flash of wrong theme.
- [ ] Currency selection in modal drives existing currency formatting; FX panel reachable.
- [ ] Unit tests: theme toggling + persistence, language persistence + `<html lang>`, currency selection wiring, modal open/close from avatar.
- [ ] Full suite green.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | localStorage `openportfo.theme`, `openportfo.language`, `openportfo.displayCurrency` |
| New / changed APIs | none |
| Auth required? | no |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | new `components/UserSettingsModal.tsx`, new `ThemeProvider`/`LanguageProvider` (or combined), `app/globals.css` (dual palette), `app/layout.tsx`, `Providers.tsx`, retire `CurrencySelect`/`LanguageSelect` |
| Backend API | none |
| Docs / tests | new tests, existing CurrencySelect/LanguageSelect tests updated |

---

## 8. Dependencies & risks

- Depends on: BL-020 (trigger location), BL-019 (storage key prefix).
- Risks: light-mode palette quality across ~30 components using literal gray classes (variable override strategy mitigates); hydration mismatch; static export forbids server-side theme injection (use inline script).

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | `prefers-color-scheme` as default when no stored value? | open | SA decision |
| 2 | Translation dictionary scope | open | SA decision (chrome-only recommended) |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-23 | Batch created | — |
