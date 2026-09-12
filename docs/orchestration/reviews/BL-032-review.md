# SA Review — BL-032: Daily SES portfolio email

| Field | Value |
|-------|-------|
| **ID** | `BL-032` |
| **Reviewer (SA)** | SA |
| **Date** | 2026-09-12 |
| **Walkthrough** | `docs/orchestration/walkthroughs/BL-032-walkthrough.md` |
| **Verdict** | `approve` |

---

## 1. AC verification

| AC | Satisfied? | Evidence | Note |
|----|------------|----------|------|
| AC1 opt-in switch | yes | `GeneralTab.tsx` checkbox + i18n; `SettingsTabs.test.tsx` save `emailOptIn: true`; Playwright `e2e/settings-email.spec.ts` | Default remains false |
| AC2 crons | yes | `infra/cloudformation.yml` news/price/snapshot `cron(0 17 * * ? *)`; email `cron(15 17 * * ? *)`; no `cron(0 1` news rule | |
| AC3 ICT snapshot date | yes | `job_utils.ict_today`; `snapshot_job._resolve_snapshot_date`; `test_ict_today_at_1700_utc_is_next_calendar_day`; `test_snapshot_omitted_date_uses_ict_today` | BL-030 literal `date` override unchanged |
| AC4 flags + opt-in | yes | `email_job.run_email_job`; `test_email_job_sends_opt_in_user_with_pnl_and_holdings`; `test_email_job_skips_when_flags_off` | |
| AC5 missing snapshot | yes | `test_email_job_skips_missing_today_snapshot` | No live `get_portfolio` in email job |
| AC6 PnL + holdings | yes | `render_email` Holdings table; test asserts `PnL vs cost` and `BTC` | |
| AC7 related news | yes | `related_news` holdings∪watchlist; `test_email_job_news_matches_holdings_and_watchlist_only`; empty news still sends | Does not use `NewsService.list_for_user` |
| AC8 ports + SES IAM | yes | `ports/email.py`; `adapters/ses/sender.py`; CFN `SesSend`; fake `InMemoryEmailSender` | |
| AC9 suites | yes | frontend 426; Playwright 5 pass; LocalStack pass; backend 580 pass + 4 pre-existing FX fails | Same 4 FX failures as baseline |
| AC10 snapshot price warm | yes | `refresh_price_cache` then `get_portfolio(force_refresh=False)`; `test_snapshot_warms_prices_before_pnl` expects 65000 not stale 40000 | |

## 2. Architecture checks

- [x] Ports isolation — verify `ports-isolation` pass; SES `boto3` only in adapters
- [x] No API Gateway; no SSR; FX still admin-on-demand; Lambda schedule-only
- [x] Cost: SES sandbox + existing Lambda; under $50 narrative
- [x] No secrets committed; `SES_FROM_EMAIL` is env

## 3. Code quality

- [x] Tests assert body contents, skip reasons, SES client kwargs, ICT date
- [x] Scope limited to BL-032 (+ snapshot price-first requested at implement time)
- [x] Email failures isolated per user (`EmailSendError`)

## 4. Issues (if request_changes)

| # | File:line | Issue | Required fix |
|---|-----------|-------|--------------|
| — | — | none | — |

## 5. Decision

- **approve:** Orchestrator may keep `feat/BL-032-daily-ses-email` review-ready. Mark backlog `done` after commit if the stakeholder asks. Do not deploy SES/EventBridge until authorized.

## 6. Notes for Orchestrator

- Set Lambda `SES_FROM_EMAIL`; verify SES identities (sandbox).
- Lab: attach `ses:SendEmail` to LabRole; recreate EventBridge rules at the new crons.
- Residual: 4 pre-existing FX `stale_ok` vs `fresh` tests; LocalStack does not prove SES.
