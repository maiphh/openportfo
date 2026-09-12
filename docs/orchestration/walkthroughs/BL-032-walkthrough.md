# Walkthrough — BL-032: Daily SES portfolio email

| Field | Value |
|-------|-------|
| **ID** | `BL-032` |
| **Branch** | `feat/BL-032-daily-ses-email` |
| **Worktree** | current repo (`D:\rmit\cloud\a3`) — branch created in place so uncommitted design docs stayed with the work |
| **Implementor** | Eng |
| **Date** | 2026-09-12 |
| **SA design** | `docs/orchestration/designs/BL-032-daily-ses-balance-email-design.md` |
| **Research** | n/a |

---

## 1. Summary (what was built)

Daily EventBridge → Lambda email for opt-in users: **PnL, per-holding performance, news matching holdings/watchlist**. News/price/snapshot run at **00:00 ICT**; email at **00:15 ICT**. Snapshot **force-refreshes prices before** portfolio math so PnL is not computed from a stale cache. SES is behind an `EmailSender` port.

## 2. Files changed (path:line)

| File | Change |
|------|--------|
| `backend/app/ports/email.py` | `EmailSender` + `EmailMessage` + `EmailSendError` |
| `backend/app/adapters/ses/sender.py` | SES `send_email` adapter |
| `backend/app/adapters/memory/email.py` | Recording fake |
| `backend/app/jobs/email_job.py` | Opt-in send; snapshot delta; related news |
| `backend/app/jobs/snapshot_job.py` | ICT today; `refresh_price_cache` before `get_portfolio` |
| `backend/app/jobs/price_job.py` | Shared `refresh_price_cache` |
| `backend/app/jobs/handler.py` | `{"job":"email"}` |
| `infra/cloudformation.yml` | `cron(0 17 * * ? *)` news/price/snapshot; email `cron(15 17 * * ? *)`; `ses:SendEmail` |
| `frontend/components/settings/GeneralTab.tsx` | Daily email opt-in copy + helper |
| `frontend/components/admin/JobControlsPanel.tsx` | Daily email admin toggle |
| `frontend/e2e/settings-email.spec.ts` | Opt-in save |

## 3. Decisions & deviations from SA design

| # | SA said | Did | Reason |
|---|---------|-----|--------|
| D14 | Snapshot warms prices before PnL | `refresh_price_cache` then `get_portfolio(force_refresh=False)` | Stakeholder: snapshot must update prices first |
| D8 | News at 00:00 ICT | CFN news cron moved; 08:00 rule removed | Stakeholder |
| Worktree | `a3-wt-bl032` | Feature branch in this clone | Keep already-written design files with the implementation |

## 4. How to verify

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/unit/jobs tests/unit/adapters/test_ses_sender.py -q -p no:cacheprovider

cd ../frontend
npm test -- components/admin/JobControlsPanel.test.tsx components/settings/SettingsTabs.test.tsx
npx playwright test e2e/settings-email.spec.ts e2e/admin-rss.spec.ts
```

## 5. Test evidence (paste)

Focused jobs/SES: **99 passed** (`tests/unit/jobs` + SES adapter + settings config).

Full `verify.ps1 -Profile full` (`.workflows/runs/latest.json`):

| Gate | Result |
|------|--------|
| workflow-contract | pass |
| ports-isolation | pass |
| backend-tests | fail — **4 pre-existing** FX `stale_ok` vs `fresh` (same as baseline); **580 passed** (+12 vs 568 baseline) |
| frontend-lint | pass |
| frontend-unit | pass (426) |
| frontend-build | pass |
| playwright-e2e | pass (5 passed, 4 skipped BL-031) including settings email opt-in |
| localstack-contract | pass (DynamoDB+S3 only; not SES) |

New tests: `test_snapshot_warms_prices_before_pnl`, `test_snapshot_omitted_date_uses_ict_today`, `test_email_job_*`, `test_ses_sender_*`, `test_ict_today_*`.

## 6. API / UX verification

- Settings checkbox “Receive daily portfolio email” → `PUT /api/settings` `{ emailOptIn: true }` (Playwright).
- Admin “Daily portfolio email” → `emailEnabled` + `jobs.email` (Playwright admin-rss).
- Lambda: `{"job":"email"}` (unit handler). No live SES send (sandbox / no deploy).

## 7. Ports isolation check

`rg` gate **pass**. `boto3`/`botocore` only in `backend/app/adapters/ses/sender.py`.

## 8. Known limitations / follow-ons

- SES sandbox: verify from-address and recipients; set `SES_FROM_EMAIL` on Lambda.
- Lab CFN cannot create IAM — attach `ses:SendEmail` to LabRole by hand.
- Same-minute news/price/snapshot still overlap; snapshot now warms prices itself; email waits 15 minutes.
- Rare duplicate mail on Lambda retry (no sent-log table).
- Pre-existing FX `stale_ok` vs `fresh` failures unchanged.

## 9. Handoff to SA Review

- Walkthrough ready for SA review: **yes**
- AC checklist self-assessed: AC1–AC10 yes (SES live send not exercised)
