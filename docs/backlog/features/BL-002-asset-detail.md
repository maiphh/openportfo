# BL-002 — Asset detail pages (crypto + stock)

| Field | Value |
|-------|--------|
| **ID** | `BL-002` |
| **Title** | Asset detail pages + global asset click-through |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | PRD M7, FR-C*; asset detail + history APIs (existing); BL-001 portfolio |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |
| **Implement when** | After additional backlog features are clarified (stakeholder hold) |

---

## 1. Problem / user value

Users need to open any named asset and see a rich **profile** (name, description, price, type-specific stats, chart) and optionally **add it to their portfolio**. Clicking an asset name/symbol anywhere in the app should land on the same detail experience.

---

## 2. User story

As an **authenticated investor**, I want to **click any stock/crypto name or symbol and open its detail page**, so that **I can read about the asset, view price history, and add a holding without hunting for a separate screen**.

---

## 3. Scope

### In scope

- Routes: **`/crypto/[id]`** and **`/stock/[id]`** (`id` = symbol or provider slug, e.g. `btc` / `bitcoin` / `VNM`)
- **FE-first** on existing APIs; backend changes only if a gap blocks UI
- Shared page layout + **type-specific sections** (hide null fields)
- Must-have content:
  - Name, symbol, logo/image
  - Description
  - Current price + change %
  - Historical chart with ranges **`7d | 30d | 90d | 1y`**
  - Type-specific stats (mcap, volume, supply, ATH/ATL, exchange, industry, country, …)
  - External links (`homepage`, `profile.links`)
  - **Add to portfolio** → opens **Add Holding modal** prefilled with this asset (qty/cost still required; aligns with BL-001)
- **Global click-through:** wherever an asset name/symbol is shown, it links to the detail page (shared `AssetLink` convention), including:
  - Portfolio holdings table
  - Header search results
  - Markets heatmap tiles
  - Markets quote boards
  - Top stories / news **when a symbol is tagged**
  - Any future list that shows symbol/name
- Auth: **Cognito required**
- Display currency: **BL-003** session currency (VND / USD / EUR) via `currency=` query

### Out of scope

- Public (unauthenticated) detail pages
- Extending history ranges beyond `7d|30d|90d|1y`
- Splitting backend into separate crypto/stock OpenAPI schemas (unless FE blocked)
- Watchlist-specific UI (watchlist is its own BL; links still use `AssetLink` when that UI exists)
- Real-time streaming quotes on the detail page

---

## 4. Behaviour

### Happy path

1. User is signed in.
2. Clicks an asset name/symbol (search, heatmap, quotes, portfolio, tagged news, …).
3. Navigates to `/crypto/{id}` or `/stock/{id}`.
4. Page loads detail from `GET /api/assets/{assetType}/{slug}?currency={session}` (optional `range` or separate history call).
5. Sees header (name/symbol/image), price + change, description, type-specific stats, links, chart with range tabs.
6. Clicks **Add to portfolio** → Add Holding modal opens with asset preselected; user enters qty + cost (session→native per BL-001) → save.

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| Unauthenticated | Sign-in gate (same as portfolio) |
| Unknown slug | **404** page / not-found state |
| Profile partially empty | Show available fields; hide null type-specific stats; fallback short description OK |
| History empty / error | Chart empty state; rest of page still usable |
| FX missing for session currency | Show native price; display fields null/omitted with clear FX status |
| News without symbol tag | Headline **not** forced into asset link |
| Crypto vs stock field mix | Render only relevant section; do not show empty crypto supply block on stocks (and vice versa) |

### UX notes

- Shared shell: header + price strip + chart + about + stats + links + CTA
- Crypto stats emphasis: rank, supply, mcap, volume, ATH/ATL, categories, social links
- Stock stats emphasis: exchange, industry, country, mcap/volume when present
- Chart range control labels: **7D / 30D / 90D / 1Y** (map 1:1 to API)
- Prefer reusable **`AssetLink`** (href builder from `assetType` + symbol/assetId)

---

## 5. Acceptance criteria

- [ ] **AC1** `/crypto/[id]` and `/stock/[id]` render for valid slugs when authenticated.
- [ ] **AC2** Unauthenticated users cannot load portfolio-gated detail data (sign-in required).
- [ ] **AC3** Page shows name, symbol, and image when API provides them.
- [ ] **AC4** Description section shows profile description (or graceful fallback).
- [ ] **AC5** Current price (+ change % when available) respects **session display currency**.
- [ ] **AC6** Chart supports ranges **7d, 30d, 90d, 1y** via history API; switching range updates series.
- [ ] **AC7** Type-specific stats section shows crypto-relevant and stock-relevant fields; nulls hidden.
- [ ] **AC8** External links render when `homepage` / `links` present.
- [ ] **AC9** **Add to portfolio** opens Add Holding modal **prefilled** with this asset (does not invent qty).
- [ ] **AC10** Invalid id → clear not-found/error state (HTTP 404 from API).
- [ ] **AC11** Click-through works from: portfolio holdings, header search, heatmap, quote boards, and news when symbol-tagged.
- [ ] **AC12** Shared link helper/component is used so future symbol/name surfaces can opt in consistently.
- [ ] **AC13** Backend changed only if a concrete UI gap requires it (documented in handoff).

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Detail API | `GET /api/assets/{assetType}/{slug}?currency=&range=` |
| History API | `GET /api/assets/{assetType}/{slug}/history?range=&currency=` (or embedded `history` when `range` on detail) |
| Auth | Cognito Bearer |
| Display currency | Session VND/USD/EUR → `currency` query (aligned with BL-001) |
| Profile shape | Shared JSON; crypto-heavy vs stock-heavy fields may be null by type |
| Holdings CTA | Reuses BL-001 add-holding flow |

### Response shape notes (existing)

Top-level (both types): `assetType`, `symbol`, `assetId`, `name`, `nativeCurrency`, `displayCurrency`, `profile`, `quote`, `fx`, `history`.

**Crypto-leaning `profile` fields:** `imageUrl`, `homepage`, `categories`, `marketCapRank`, `genesisDate`, `hashingAlgorithm`, `circulatingSupply`, `totalSupply`, `maxSupply`, `links`, …

**Stock-leaning `profile` fields:** `exchange`, `industry`, `country`, (plus description / optional mcap-style fields when provider has them).

**Quote:** native `price` + `priceDisplay` / mcap-volume display fields via stored FX.

Slug resolve accepts **symbol or assetId** (e.g. `/crypto/btc` and `/crypto/bitcoin`).

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `app/crypto/[id]/page.tsx`, `app/stock/[id]/page.tsx`, chart, stats sections, Add Holding modal hook, `AssetLink` |
| Click-through | Portfolio table, `SearchDialog`, heatmap, quotes, news cards (if symbol present) |
| Backend API | Existing detail/history; touch only if gap |
| Docs / tests | FE verification; optional API contract tests already exist |

---

## 8. Dependencies & risks

- **Depends on:** BL-001 add-holding modal (or equivalent shared component); Cognito in Artryx; session currency switcher
- **Risks:** Thin VN stock descriptions from provider; news items without reliable symbol tags; FE auth not wired yet

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Delivery scope | resolved | Full stack polish, but FE-first; BE only if blocked |
| 2 | URL shape | resolved | `/crypto/[id]`, `/stock/[id]` |
| 3 | Click-through | resolved | Everywhere asset name/symbol is shown (listed surfaces + shared convention) |
| 4 | Layout | resolved | Shared + type-specific sections |
| 5 | Content | resolved | All listed must-haves including Add Holding CTA |
| 6 | Auth | resolved | Cognito required |
| 7 | Currency | resolved | Session VND/USD/EUR via **BL-003** |
| 8 | Chart ranges | resolved | 7d / 30d / 90d / 1y |
| 9 | Add CTA | resolved | Prefill Add Holding modal |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Intake | Asset detail; BE profile exists; routes like `/stock/[id]`, `/crypto/[id]`; crypto vs stock may differ |
| 2026-08-19 | Discovery | `GET /api/assets/{type}/{slug}` + history; shared DTO with type-specific nullable fields |
| 2026-08-19 | Scope | Full stack polish; FE-first |
| 2026-08-19 | URLs | `/crypto/[id]`, `/stock/[id]` |
| 2026-08-19 | Click-through | **Everywhere** asset name is stated (not portfolio-only) |
| 2026-08-19 | Layout / content | Shared + type sections; full content set incl. chart, stats, links, add CTA |
| 2026-08-19 | Auth / FX | Cognito; session currency |
| 2026-08-19 | Chart / CTA | API ranges; Add Holding modal prefilled |
| 2026-08-19 | Ready | Spec finalized; implement with batch after more features |

---

## 11. Implementation notes (Eng fills after start)

- Approach: FE-first on existing `GET /api/assets/{type}/{slug}` + `/history`. Shared `AssetLink` + `assetDetailHref`; detail shell in `AssetDetailView` with type-specific stats (nulls hidden), chart ranges 7d/30d/90d/1y, Add Holding modal prefill (qty blank). No backend changes.
- PR / branch: `execute-plan/6cc30007-pr-4-bl-002-asset-detail`
- Verification: `cd frontend && npx vitest run` (asset href/helpers + API client tests)
