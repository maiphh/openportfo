# SA Design — BL-037: Lambda + EventBridge update script

| Field | Value |
|-------|-------|
| **ID** | `BL-037` |
| **Title** | Deploy jobs onto existing Lambda + align EventBridge |
| **Status** | `ready_for_implementation` |
| **Date** | 2026-09-13 |
| **Complexity** | `simple` |
| **Feature file** | `docs/backlog/features/BL-037-deploy-lambda-eventbridge.md` |

## Sequence

```
Docker linux/amd64 pip + backend/app + lambda_handler.py → openportfo-jobs.zip
  → update-function-code (openportfo-jobs)
  → merge SMTP_* from backend/.env into existing env (no echo)
  → put-rule existing news/price/snapshot → cron(0 17 * * ? *)
  → put-rule openportfo-job-email → cron(15 17 * * ? *)
  → add-permission for email rule if missing
  → invoke {"job":"email"} smoke
```

Never: create-function, terminate, cloudformation deploy, FX rule.

## TDD

Contract pytest on scripts, then implement, then live deploy.
