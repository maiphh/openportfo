# BL-014 — Portfolio value chart + GitHub-style PnL activity heatmap

| Field | Value |
|-------|--------|
| **ID** | `BL-014` |
| **Title** | Portfolio history chart (like asset detail) + daily PnL contribution heatmap |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | BL-001 (history chart was out of scope); BL-002 `AssetHistoryChart`; sprint-07 snapshots |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |

---

## Review findings

BL-001 explicitly deferred **historical portfolio value / PnL time-series**. `/portfolio` today: summary cards, allocation pie, holdings table.

Asset detail already has `AssetHistoryChart` with range tabs `7d | 30d | 90d | 1y`.

Backend already has:

- `GET /api/portfolio/performance?range=1d|1w|mtd|ytd|max` — equity curve from daily snapshots
- `GET /api/snapshots?from=&to=` — raw daily payloads (`totalsDisplay.marketValue`, `pnl`, …)
- Snapshot **job** writes one payload per user per day

Daily PnL for a GitHub-style grid = **day-over-day change of snapshot market value** (same-currency series). Snapshot `totalsDisplay.pnl` is **unrealized total**, not daily delta — do not color cells from that field.

---

## 1. Problem / user value

Investors need to see **how the book moved over time**, not only today’s totals. A price-like chart plus a year of daily up/down cells (GitHub contribution graph, but red/green PnL) makes streaks of gains and losses obvious.

---

## 2. User story

As an **authenticated investor**, I want **a portfolio value chart like the asset detail page and a GitHub-style heatmap of daily PnL**, so that **I can see trend and which days I was up or down**.

---

## 3. Scope

### In scope

- **Value / equity chart** on `/portfolio` (below summary cards, above or beside pie):
  - Line + area, same visual language as `AssetHistoryChart` (teal stroke, soft fill)
  - Range tabs aligned with existing performance API: **`1w | mtd | ytd | max`** (map UI labels clearly; optional extra `1d` not required)
  - Y-axis / last-value in **session display currency** (convert snapshot points with BL-003 rates when snapshot currency ≠ session)
  - Empty state when fewer than 2 valued points
- **GitHub-style activity heatmap** (last **53 weeks**):
  - 7 rows (days) × ~53 columns (weeks)
  - Month labels on top; weekday labels (Mon/Wed/Fri) on the left
  - Cell color:
    - no snapshot / no delta → dark empty (GitHub unused)
    - **down day** → red, **redder = larger loss**
    - **up day** → green, **greener = larger gain**
    - flat ~0 → near-black / muted
  - Tooltip: date, daily PnL (display currency), optional % vs prior day
  - Intensity scale from percentiles or fixed buckets of \|daily PnL\| (document the buckets in code)
- Data: existing snapshot/performance APIs; small FE client wrappers
- Loading skeletons; error + retry per widget
- Unit tests for: daily delta series, color bucket, empty grid, chart range mapping
- **Next.js App Router UI practices** (static export safe, client islands, a11y)

### Out of scope

- Changing the snapshot job schedule
- Intraday / hourly heatmap
- Benchmark overlay (VNINDEX)
- Editing snapshots
- Public (unauthenticated) charts

---

## 4. Behaviour

### Happy path

1. Signed-in user with snapshot history opens `/portfolio`.
2. Chart shows equity curve for default range **`mtd`** (or `1w` if that has more points — pick **`1w`** as default if MTD may be empty early in the month). **Default range: `1w`.**
3. Heatmap shows the last 53 weeks; days with snapshots light up red/green.
4. Hovering a cell shows `2026-08-18 · +1,234.00 VND`.
5. Changing session currency re-renders converted amounts.

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| No snapshots | Chart empty state: “Daily snapshots appear after the snapshot job runs.” Heatmap all empty cells, same copy |
| One snapshot | Chart empty (need 2 points); heatmap one cell (no delta → empty or flat) |
| Mixed snapshot currencies | Convert each point via session FX; drop points that cannot convert |
| Auth missing | Existing portfolio gate (no extra public fetch) |
| API 5xx | Widget error + Retry; rest of dashboard still visible |

### UX notes

- Reference: GitHub profile contribution graph (week columns, day rows, 5-ish intensity steps) but **diverging red/green**, not monochrome greens
- Do not use the markets treemap heatmap component
- Place: chart full width; heatmap full width under chart or under pie — chart then heatmap then pie/table is fine
- Accessible: `role="img"` + summary text; cells as buttons or `title` + keyboard focus

---

## 5. Acceptance criteria

- [ ] **AC1** `/portfolio` shows a value chart with range tabs `1w | mtd | ytd | max` using `GET /api/portfolio/performance`.
- [ ] **AC2** Chart empty state when < 2 valued points; no fake series.
- [ ] **AC3** GitHub-style 53-week grid of daily PnL (day-over-day MV delta from snapshots).
- [ ] **AC4** Up days green (darker/brighter green = larger gain); down days red (stronger red = larger loss); empty days muted.
- [ ] **AC5** Tooltip includes date and daily PnL in session currency.
- [ ] **AC6** Heatmap does **not** color from cumulative `totalsDisplay.pnl`.
- [ ] **AC7** Unauthenticated users still cannot load snapshot/performance data.
- [ ] **AC8** Loading skeleton + error/retry per widget; holdings table still works if charts fail.
- [ ] **AC9** Unit tests for delta + color mapping.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source | `GET /api/portfolio/performance`, `GET /api/snapshots?from=&to=` |
| Daily PnL | `MV[t] - MV[t-1]` after converting to session currency |
| Auth | Bearer (existing) |
| Jobs | Existing daily snapshot job — do not change |
| Currency | Session display currency (BL-003) |

Default heatmap window: `from = today-371d`, `to = today`.

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `PortfolioDashboard.tsx`, new `PortfolioValueChart.tsx`, `PnlActivityHeatmap.tsx`, `lib/portfolio.ts` fetch helpers, tests |
| Backend | Optional: none if existing APIs suffice; may add `dailyPnl` on performance DTO if cleaner — **allowed additive** |
| Jobs | None |

---

## 8. Dependencies & risks

- Depends on: snapshots actually being written in the environment
- Risk: empty heatmap in local/dev without job — empty state must explain this
- Overlap: BL-013 also edits `/portfolio` — keep this BL to **new chart components** + dashboard composition

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Chart ranges | resolved | `1w \| mtd \| ytd \| max` via existing performance API |
| 2 | Default range | resolved | `1w` |
| 3 | Heatmap window | resolved | 53 weeks |
| 4 | Color meaning | resolved | Red down / green up; intensity = \|daily PnL\| |
| 5 | Data field | resolved | Day-over-day market value, not cumulative pnl |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Charts like asset detail + GitHub PnL heatmap | Performance API + snapshot deltas; diverging red/green grid |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach: FE-only. Client widgets `PortfolioValueChart` (`GET /api/portfolio/performance`, default `1w`, tabs `1w|mtd|ytd|max`) and `PnlActivityHeatmap` (`GET /api/snapshots?from=&to=` last 371 days). Daily PnL is `MV[t]-MV[t-1]` after BL-003 session FX — never `totalsDisplay.pnl`. Heatmap is a 7×53 Sunday-start GitHub grid; intensity is 4 fixed buckets of `|dailyPnl| / maxAbs` (≤25/50/75/>75%) plus empty/flat. Charts fetch independently (skeleton + retry) so holdings still render if they fail. No backend DTO change.
- PR / branch: `feat/BL-014-portfolio-charts`
- Verification: `cd frontend; npx vitest run lib/portfolio-charts.test.ts` (daily delta, color buckets, empty 53-week grid, range mapping, Bearer fetch). Full `npx vitest run` in `frontend/`.
