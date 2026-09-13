# SA Review — BL-038: Refresh stale deploy docs (Lambda + API Gateway live)

| Field | Value |
|-------|-------|
| **ID** | `BL-038` |
| **Reviewer (SA)** | SA (separate review pass) |
| **Date** | 2026-09-13 |
| **Design** | `docs/orchestration/designs/BL-038-deploy-docs-refresh-design.md` |
| **Feature** | `docs/backlog/features/BL-038-deploy-docs-refresh.md` |
| **Verdict** | `approve` |

---

## 1. AC verification

| AC | Satisfied? | Evidence (file:line or test) | Note |
|----|------------|------------------------------|------|
| AC1 | yes | `docs/backlog/BACKLOG.md:44` — row cites Gateway `7duvngr98b`, EB `v-20260913-http-api`, 4 rules ENABLED, date `2026-09-13`; no `not deployed` remains | Matches live `describe` 2026-09-13 |
| AC2 | yes | `docs/orchestration/walkthroughs/BL-035-walkthrough.md:17` (live addendum: route `anmha94` → integration `745svs2`, stage `$default`, smokes); `:78` (`execute-api ... → 401` verified); `:86` (live-since note + recycle pointer) | No `no AWS deploy` / `not created` left for Gateway/Lambda path |
| AC3 | yes | `docs/implementation/sprints/sprint-12-aws-deploy/DEPLOY_STATUS.md:5` (date 2026-09-13), `:12` (stack `UPDATE_ROLLBACK_COMPLETE`, Gateway not via CFN), `:18-23` (Lambda/EB/Gateway/rules/smokes), `:32-34` (CFN + fixture caveats), `:49` (`fixture` live note), `:52` (no-secrets note), `:56` (no-CFN-deploy warning) | Env keys only; `SMTP_PASSWORD` value absent (secret scan clean) |
| AC4 | yes | `docs/backlog/features/BL-035-api-gateway.md:117` (risk cleared), `:127` (deploy-live Yes), `:144` (live addendum); `BL-036-deploy-eb-update.md:128` (EB addendum); `BL-037-deploy-lambda-eventbridge.md:60` (Lambda/rules addendum) | Historical scope text (§3) intentionally preserved |
| AC5 | yes | `git diff --stat` shows no change to `docs/orchestration/reviews/BL-035-review.md` | Point-in-time `approve` preserved |
| AC6 | yes | `.workflows/runs/latest.json` post-change: `workflow-contract pass`; `ports-isolation fail` (`rg` missing) + `backend-tests fail` (4 FX `fresh vs stale_ok`) identical to pre-change baseline; `frontend-lint/unit pass` | Docs-only; no code/config touched |

## 2. Architecture checks

- [x] Ports isolation — `git diff --stat` = docs only (`BACKLOG.md`, 3 feature files, `DEPLOY_STATUS.md`, walkthrough); no `backend/app/services|api|domain|jobs` change; no new `boto3/httpx`.
- [x] Locked decisions intact — D2 repeated correctly (Gateway `HTTP_PROXY` to FastAPI, Lambda EventBridge-only, chat same-origin per walkthrough `:17` + DEPLOY_STATUS `:20-21`); no SSR/CloudFront-live claim; no browser-direct market claim; `fixture` caveat kept (`DEPLOY_STATUS.md:34,49`).
- [x] Tests green + meaningful? — docs-only gate is `workflow-contract pass`; full-suite deltas nil vs baseline (same 4 FX + `rg` fails, recorded pre-existing in design §1).
- [x] Walkthrough accurate? — live IDs/dates/smokes match read-only evidence: `7duvngr98b`, `v-20260913-http-api`, Lambda `2026-09-13T10:05:38Z`, rules `cron(0/15 17 * * ? *)` ENABLED, `GET /health → ok`, `GET .../api/auth/me → 401 Missing authorization header`.
- [x] No secrets — secret scan over edited docs hit only prose (`no secrets`, `App Password`); no `SMTP_PASSWORD` value, no key material.

## 3. Code quality

- [x] Dated claims (`2026-09-13`) so lab recycle reads as expiry, not error.
- [x] File ownership respected (design §7 allow-list only).
- [x] No scope creep (Athena/CloudFront/Containers/FX fixes untouched).

## 4. Issues (if request_changes)

None.

Pre-existing (not blocking BL-038): 4 FX `fresh vs stale_ok` unit failures + missing `rg` binary — identical before/after, logged in design §1 and feature §8.

## 5. Decision

- **approve.** Backlog may mark BL-038 `done`; result is review-ready on the `main` working tree. No commit/merge/push/deploy without user authorization.

## 6. Notes for Orchestrator

- Working tree: `D:\rmit\cloud\a3` (`main`, docs-only, no worktree per design D5).
- Evidence: `.workflows/runs/latest.json` (post-change quick); `git diff --stat` (6 modified + 2 new docs); secret scan clean.
- Residual risk: lab teardown re-stales live docs — mitigated by explicit dates + redeploy pointers (`deploy-eb.ps1`, `deploy-lambda.ps1`, `http-api-gateway.md`).
