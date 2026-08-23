# BL-019 — Rebrand Artryx → OpenPortfo

| Field | Value |
|-------|--------|
| **ID** | `BL-019` |
| **Title** | Rename all "Artryx"/"artryx" brand references to "OpenPortfo"/"openportfo" |
| **Priority** | `P0` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Luna implementer |
| **Requested by** | Product (project rename: the project is **OpenPortfo**; "Artryx" was a misunderstanding) |
| **Related PRD / sprint** | sprint-05 |
| **Created** | 2026-08-23 |
| **Ready date** | 2026-08-23 |
| **Done date** | 2026-08-23 |

---

## 1. Problem / user value

The product was accidentally branded "Artryx" while the real project name is **OpenPortfo** (already used by root metadata, Cognito domain, zips). Users see inconsistent branding; code/docs/storage keys carry the wrong name.

Note: the misspelling is **"Artryx"/"artryx"** (with "rtr") — the string "artyx" appears nowhere.

---

## 2. User story

As a **user**, I want **the app to consistently say OpenPortfo**, so that **branding and saved preferences belong to the product I use**.

---

## 3. Scope

### In scope

- Visible brand text: `BrandLogo.tsx` ("Artryx" → "OpenPortfo"), page `<title>`/metadata.
- Package name `frontend/package.json` → `openportfo`.
- Canonical browser-storage keys use the `openportfo.*` namespace. No legacy migration is required because no former-name build was released to users.
- SVG gradient id `artryx-spark-fill` → `openportfo-spark-fill` (cosmetic).
- UI copy mentioning `artryx.accessToken` (auth-gate hints in AssetDetailView, PortfolioDashboard, WatchlistView, SearchDialog).
- Docs: update `frontend/README.md` and backlog feature docs that reference old keys (read-only history docs: add a note, don't rewrite history where it documents past behavior — except where the doc states current behavior).
- Tests referencing old keys.

### Out of scope

- Backend (no occurrences).
- Cognito domain (already `openportfo-…`), root zips, deploy/infra naming.

---

## 4. Behaviour

### Happy path

1. A user signs in and the ID token is stored at `openportfo.accessToken` in tab-scoped sessionStorage.
2. Theme, language, currency, and market caches use only their canonical `openportfo.*` keys.

### Edge cases / errors

- A token found only in localStorage is rejected and removed; browser auth remains tab-scoped.
- Preferences are applied by their React providers after hydration.

### UX notes

- No visual change beyond the brand string itself.

---

## 5. Acceptance criteria

- [x] Zero case-insensitive occurrences of the former name under active `frontend/` source (excluding build output and package-lock history).
- [x] Authentication uses only canonical sessionStorage and rejects persistent localStorage tokens.
- [ ] All frontend tests green (`npm test` in `frontend/`).
- [ ] Brand text reads "OpenPortfo" in the UI.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | localStorage/sessionStorage keys |
| New / changed APIs | none |
| Auth required? | no |
| Caching / freshness | n/a |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `package.json`, `components/BrandLogo.tsx`, `lib/auth.ts`, `lib/cognito.ts`, `lib/currency.ts`, `lib/markets-cache.ts`, `components/dashboard/Sparkline.tsx`, auth-gate copy in `AssetDetailView`, `PortfolioDashboard`, `WatchlistView`, `SearchDialog`, `ChatWidget` |
| Backend API | none |
| Docs / tests | `frontend/README.md`, backlog docs (current-behavior sections), all tests referencing old keys |

---

## 8. Dependencies & risks

- Depends on: none (do first).
- Risks: saved theme/language preferences apply after hydration, so a non-default theme can briefly show the default dark/English shell on reload.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Keep old-key read compatibility? | resolved | No. Product confirmed no former-name build was released; bootstrap and compatibility reads were removed before first release. |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-23 | Rename scope confirmed product-wide | Batch created |
| 2026-08-23 | Confirmed no former-name release/users | Removed bootstrap migration and all legacy-key compatibility before first release |
