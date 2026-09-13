# SA Design — BL-036: One-command Beanstalk update

| Field | Value |
|-------|-------|
| **ID** | `BL-036` |
| **Title** | Deploy a new app version onto the existing Beanstalk environment |
| **Status** | `ready_for_implementation` |
| **Author (SA)** | Orchestrator / SA |
| **Date** | 2026-09-13 |
| **Complexity** | `simple` |
| **Related PRD** | Lab hosting BL-031 / BL-035 |
| **Feature file** | `docs/backlog/features/BL-036-deploy-eb-update.md` |

---

## 1. Context

Code deploys are Elastic Beanstalk **application versions**, not CloudFormation. Operators need one command that packages and rolls onto **openportfo-api-env**.

## 2. Affected surfaces

| Layer | Paths | Change |
|-------|-------|--------|
| Scripts | `scripts/deploy-eb.ps1`, `scripts/deploy-eb.sh` | **new** |
| Scripts | `scripts/package-eb.ps1` / `.sh` | **call only** |
| Docs | `docs/runbooks/eb-single-hosting.md`, `http-api-gateway.md` | one-liner |
| Tests | `backend/tests/unit/infra/test_deploy_eb_script.py` | **new** |

## 3. Sequence

```
package-eb.ps1 -AppUrl https://EB -ApiUrl https://execute-api
  → s3 cp eb-bundle.zip
  → create-application-version (new label)
  → update-environment --environment-name openportfo-api-env --version-label …
  → wait Ready
  → GET http://CNAME/health
```

Never: `create-environment`, `create-application`, `cloudformation deploy`, new HTTP API.

## 4. Defaults (Learner Lab)

Overridable via parameters / `EB_APP_URL`, `EB_API_URL`, `EB_APPLICATION`, `EB_ENVIRONMENT`, `EB_REGION`, `EB_S3_BUCKET`.

- App / env: `openportfo-api` / `openportfo-api-env`
- AppUrl: `https://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com`
- ApiUrl: `https://7duvngr98b.execute-api.us-east-1.amazonaws.com`
- Bucket: `elasticbeanstalk-us-east-1-059358625850`

## 5. TDD order

1. Contract test: scripts exist; contain `update-environment` + `create-application-version`; forbid `create-environment` and `cloudformation deploy`.
2. Implement scripts.
3. `pytest backend/tests/unit/infra/test_deploy_eb_script.py`

## 6. Acceptance criteria (copied)

- AC1 no-arg defaults target existing app/env
- AC2 package then version-roll; no create-env / CFN
- AC3 missing env is an error
- AC4 runbook one command
