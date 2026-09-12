# Backlog board

**Last updated:** 2026-09-12
**How to use:** see `docs/backlog/README.md`

**Orchestration:** PLAN `6cc30007` complete on `integration/backlog-batch-6cc30007` (**not merged to main**).  
**This batch:** review fixes **BL-011..014** then follow-ons **BL-005..010**. Never merge to `main`.

---

## Active board

| ID | Title | Priority | Status | Owner | Feature file | Notes |
|----|-------|----------|--------|-------|--------------|-------|
| BL-019 | Rebrand Artryx → OpenPortfo (+ storage-key migration) | P0 | `done` | Luna implementer | `features/BL-019-rebrand-openportfo.md` | Architecture-approved 2026-08-23 |
| BL-020 | Collapsible sidebar nav, avatar bottom-left | P0 | `done` | Luna implementer | `features/BL-020-sidebar-nav.md` | Architecture-approved 2026-08-23 |
| BL-021 | User settings modal: light/dark + language + currency | P0 | `done` | Luna implementer | `features/BL-021-user-settings-modal.md` | Architecture-approved 2026-08-23 |
| BL-022 | DiceBear avatars | P1 | `done` | Luna implementer | `features/BL-022-dicebear-avatars.md` | Architecture-approved 2026-08-23 |
| BL-023 | Settings page w/ sub-tabs (General + Avatar) | P0 | `done` | Luna implementer | `features/BL-023-settings-page.md` | Architecture-approved 2026-08-23 |
| BL-024 | Admin page: user matrix + role/settings control + ADMIN_EMAILS whitelist | P0 | `done` | Luna implementer | `features/BL-024-admin-page-whitelist.md` | Architecture-approved 2026-08-23 |
| BL-025 | Chatbot settings tab (models, params) | P1 | `done` | Luna implementer | `features/BL-025-chatbot-settings.md` | Architecture-approved 2026-08-23 |
| BL-026 | FX rates settings tab (view + admin refresh) | P1 | `done` | Luna implementer | `features/BL-026-fx-settings-tab.md` | Architecture-approved 2026-08-23 |
| BL-027 | Portfolio CSV export (authenticated, FX-aware) | P1 | `done` | Eng | `features/BL-027-portfolio-csv-export.md` | SA `approve` 2026-08-24; cherry-picked to `workflow-setup` (not `main`) |
| BL-028 | RSS source news completion | P0 | `done` | Eng | `features/BL-028-rss-news.md` | SA `approve` 2026-08-28; worktree `a3-wt-bl028` — not merged |
| BL-029 | Lambda + EventBridge newsletter | P0 | `done` | Eng | `features/BL-029-lambda-eventbridge.md` | Sibling worktree `a3-wt-bl029`; SA `approve` — not merged |
| BL-011 | Markets stale-while-revalidate + shared BE cache | P0 | `done` | Eng | `features/BL-011-markets-stale-cache.md` | Merged to integration |
| BL-012 | Configurable 2-decimal number format | P0 | `done` | Eng | `features/BL-012-number-format.md` | Merged to integration |
| BL-013 | Portfolio Avg cost / Price in session FX | P0 | `done` | Eng | `features/BL-013-portfolio-unit-fx.md` | Merged to integration |
| BL-014 | Portfolio chart + GitHub-style PnL heatmap | P0 | `done` | Eng | `features/BL-014-portfolio-charts.md` | Merged to integration |
| BL-015 | Personal chatbot backend + safe streaming | P0 | `done` | Eng | `features/BL-015-personal-chatbot-backend.md` | Auth-scoped SSE + POST compatibility |
| BL-016 | Personal chatbot client + safe Markdown | P0 | `done` | Eng | `features/BL-016-personal-chatbot-client.md` | Global production client |
| BL-017 | Draggable chatbot bubble + panel | P1 | `done` | Eng | `features/BL-017-draggable-chat-bubble.md` | Responsive/a11y/viewport clamping |
| BL-018 | Bounded user-scoped chat session | P1 | `done` | Eng | `features/BL-018-bounded-chat-session.md` | Per-account browser persistence |
| BL-005 | Watchlist CRUD UI | P1 | `done` | Eng | `features/BL-005-watchlist-ui.md` | Merged to integration |
| BL-006 | Cognito Hosted UI | P1 | `done` | Eng | `features/BL-006-cognito-hosted-ui.md` | Merged to integration |
| BL-007 | TopStories → real news | P1 | `done` | Eng | `features/BL-007-top-stories-news.md` | Merged to integration |
| BL-008 | Admin FX refresh UI | P1 | `done` | Eng | `features/BL-008-admin-fx-refresh.md` | Merged to integration |
| BL-009 | Live SearchDialog | P1 | `done` | Eng | `features/BL-009-live-search-dialog.md` | Merged to integration |
| BL-010 | BE: no markets catalog fixture fallback | P1 | `done` | Eng | `features/BL-010-no-markets-fixture.md` | Merged to integration |
| BL-031 | Single-EB hosting (serve static frontend from Beanstalk API, no CloudFront) | P0 | `done` | Eng | `features/BL-031-single-eb-hosting.md` | SA design + implementor done, review `approve` 2026-09-04; branch `feat/BL-031-single-eb-hosting` — not merged |
| BL-032 | Daily SES portfolio balance-change email (opt-in + 00:00 ICT jobs, email +15 min) | P1 | `ready` | — | `features/BL-032-daily-ses-balance-email.md` | Plan-only 2026-09-12; design `docs/orchestration/designs/BL-032-daily-ses-balance-email-design.md` |

---

## Intake queue (untriaged notes)

| Date | Raw note | Promoted to |
|------|----------|-------------|
| — | — | — |

---

## Recently done

| ID | Title | Done date | Feature file |
|----|-------|-----------|--------------|
| BL-028 | RSS source news completion | 2026-08-28 | `features/BL-028-rss-news.md` |
| BL-027 | Portfolio CSV export | 2026-08-24 | `features/BL-027-portfolio-csv-export.md` |
| BL-019 | Rebrand OpenPortfo | 2026-08-23 | `features/BL-019-rebrand-openportfo.md` |
| BL-020 | Collapsible sidebar nav | 2026-08-23 | `features/BL-020-sidebar-nav.md` |
| BL-021 | User settings modal | 2026-08-23 | `features/BL-021-user-settings-modal.md` |
| BL-022 | DiceBear avatars | 2026-08-23 | `features/BL-022-dicebear-avatars.md` |
| BL-011 | Markets SWR cache | 2026-08-19 | `features/BL-011-markets-stale-cache.md` |
| BL-012 | 2-decimal number format | 2026-08-19 | `features/BL-012-number-format.md` |
| BL-013 | Portfolio unit FX | 2026-08-19 | `features/BL-013-portfolio-unit-fx.md` |
| BL-014 | Portfolio charts + PnL heatmap | 2026-08-19 | `features/BL-014-portfolio-charts.md` |
| BL-005 | Watchlist CRUD UI | 2026-08-19 | `features/BL-005-watchlist-ui.md` |
| BL-006 | Cognito Hosted UI | 2026-08-19 | `features/BL-006-cognito-hosted-ui.md` |
| BL-007 | TopStories live news | 2026-08-19 | `features/BL-007-top-stories-news.md` |
| BL-008 | Admin FX refresh | 2026-08-19 | `features/BL-008-admin-fx-refresh.md` |
| BL-009 | Live SearchDialog | 2026-08-19 | `features/BL-009-live-search-dialog.md` |
| BL-010 | No markets fixture fallback | 2026-08-19 | `features/BL-010-no-markets-fixture.md` |
| BL-003 | Session display currency | 2026-08-19 | `features/BL-003-session-currency.md` |
| BL-004 | Markets live + skeletons | 2026-08-19 | `features/BL-004-markets-live-skeleton.md` |
| BL-001 | Portfolio dashboard | 2026-08-19 | `features/BL-001-portfolio-dashboard.md` |
| BL-002 | Asset detail + click-through | 2026-08-19 | `features/BL-002-asset-detail.md` |

---

## Won’t do / deferred

| ID | Title | Status | Reason |
|----|-------|--------|--------|
| — | — | — | — |
