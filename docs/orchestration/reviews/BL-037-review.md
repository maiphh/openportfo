# SA Review — BL-037: Lambda + EventBridge update

| Field | Value |
|-------|-------|
| **ID** | `BL-037` |
| **Reviewer (SA)** | SA (same cycle) |
| **Date** | 2026-09-13 |
| **Verdict** | `approve` |

## AC

| AC | Satisfied? | Evidence |
|----|------------|----------|
| AC1 | yes | `scripts/deploy-lambda.ps1` defaults `openportfo-jobs`; fails if missing |
| AC2 | yes | `update-function-code`; contract test forbids `aws lambda create-function` / CFN |
| AC3 | yes | Live rules: news/price/snapshot `cron(0 17 * * ? *)`; email `cron(15 17 * * ? *)` |
| AC4 | yes | `infra/lambda/README.md`; Docker `linux/amd64` package |

## Residual

- SMTP overlay reads local `backend/.env` (not git). Script must not echo values.
- Live invoke sent 1 daily email (opt-in user) after deploy.
- Pre-existing FX unit failures unrelated.
