# Backlog board

**Last updated:** 2026-08-19  
**How to use:** see `docs/backlog/README.md`

Add a row when a feature is listed. Create `features/BL-XXX-….md` once clarification starts (or immediately for large items). Keep this board as the single status view.

**Batch note:** Specs may be marked `ready` while **implementation is held** until more features are clarified (stakeholder request).

---

## Active board

| ID | Title | Priority | Status | Owner | Feature file | Notes |
|----|-------|----------|--------|-------|--------------|-------|
| BL-001 | Portfolio dashboard & holdings (1 per user) | P0 | `ready` | BA | `features/BL-001-portfolio-dashboard.md` | Consumes BL-003 currency |
| BL-002 | Asset detail pages + global click-through | P0 | `ready` | BA | `features/BL-002-asset-detail.md` | `/crypto/[id]`, `/stock/[id]`; consumes BL-003 |
| BL-003 | Session display currency (app-wide) | P0 | `ready` | BA | `features/BL-003-session-currency.md` | Owns header switcher + rates panel |
| BL-004 | Markets live data + skeletons (no mock) | P0 | `ready` | BA | `features/BL-004-markets-live-skeleton.md` | `/markets/stock|crypto`; strip FE mock fallback |

---

## Intake queue (untriaged notes)

| Date | Raw note | Promoted to |
|------|----------|-------------|
| 2026-08-19 | Portfolio: 1/user; create/add holdings stock+crypto; valid only; charts + PnL dashboard | BL-001 |
| 2026-08-19 | Asset detail pages; BE profile exists; click-through everywhere asset named | BL-002 |
| 2026-08-19 | Exchange/display currency in session; whole app applies | BL-003 |
| 2026-08-19 | Markets: cache APIs, no catalog, skeleton, remove mock | BL-004 |

---

## Recently done

| ID | Title | Done date | Feature file |
|----|-------|-----------|--------------|
| — | — | — | — |

---

## Won’t do / deferred

| ID | Title | Status | Reason |
|----|-------|--------|--------|
| — | — | — | — |
