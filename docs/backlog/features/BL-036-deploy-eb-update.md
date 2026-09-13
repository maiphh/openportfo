# BL-036 — One-command Elastic Beanstalk update

| Field | Value |
|-------|--------|
| **ID** | `BL-036` |
| **Title** | Deploy a new app version onto the existing Beanstalk environment |
| **Priority** | `P2` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Orchestrator |
| **Requested by** | User |
| **Related PRD / sprint** | Assessment 3 lab hosting (BL-031 / BL-035) |
| **Created** | 2026-09-13 |
| **Ready date** | 2026-09-13 |
| **Done date** | 2026-09-13 |

---

## 1. Problem / user value

Packaging + S3 upload + `create-application-version` + `update-environment` is easy to get wrong (new env, CloudFormation update). Operators need **one script** that rolls a new zip onto the **current** environment.

---

## 2. User story (optional)

As a **lab operator**, I want **one PowerShell command after a code change**, so that **the live Beanstalk env updates without creating new AWS resources**.

---

## 3. Scope

### In scope

- `scripts/deploy-eb.ps1` (Windows) and `scripts/deploy-eb.sh` (Linux)
- Package via existing `package-eb.*`, upload zip, create **application version**, `update-environment` on the existing env
- Refuse to run if the named environment does not exist
- Runbook one-liner

### Out of scope

- Creating an application, environment, stack, Lambda, or HTTP API
- `cloudformation deploy`
- Changing Cognito / env vars on every deploy
- Fixing unrelated FX unit tests

---

## 4. Behaviour

### Happy path

1. From repo root: `.\scripts\deploy-eb.ps1`
2. Script packages with current AppUrl + Gateway ApiUrl
3. Uploads zip, creates a new version label, updates `openportfo-api-env`
4. Waits until Ready/Green and smokes `/health`

### Edge cases / errors

- Missing AWS CLI / expired Academy credentials → fail before upload
- Environment missing or Terminated → fail; do not create
- Environment already Updating → fail; do not stack another update

---

## 5. Acceptance criteria

- [x] AC1 `.\scripts\deploy-eb.ps1` with no args targets existing app `openportfo-api` / env `openportfo-api-env`
- [x] AC2 Scripts call `package-eb` then `create-application-version` + `update-environment` (not `create-environment` / `cloudformation deploy`)
- [x] AC3 Missing environment is an error, not a create
- [x] AC4 Runbook documents the one command

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | Existing EB env + HTTP API `7duvngr98b` |
| New / changed APIs | none |
| Auth required? | AWS CLI (voclabs) |
| Caching / freshness | n/a |
| Jobs / schedules | Lambda zip not deployed |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | none (packaged as today) |
| Backend API | none |
| Domain / services | none |
| Adapters | none |
| Infra / jobs | `scripts/deploy-eb.ps1`, `scripts/deploy-eb.sh` |
| Docs / tests | runbooks, `backend/tests/unit/infra/test_deploy_eb_script.py` |

---

## 8. Dependencies & risks

- Depends on: live env `openportfo-api-env`, package-eb leak/API_URL guards
- Risks: hardcoded lab hostnames go stale if the env is replaced; overrides via parameters/env

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Create a new EB environment? | resolved | No — update current env only |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-09-13 | One script to ship code to live | Update existing env; no CFN |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach: thin wrapper over `package-eb` + AWS EB version roll
- PR / branch: `main` (uncommitted)
- Verification: `pytest tests/unit/infra/test_deploy_eb_script.py` (3 passed). Live AWS not mutated in this cycle.
