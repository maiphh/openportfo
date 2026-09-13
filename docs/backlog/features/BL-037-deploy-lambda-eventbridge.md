# BL-037 — One-command Lambda + EventBridge update

| Field | Value |
|-------|--------|
| **ID** | `BL-037` |
| **Title** | Deploy jobs zip onto existing Lambda and align EventBridge (incl. email) |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Orchestrator |
| **Requested by** | User |
| **Related PRD / sprint** | BL-032 / BL-034 email jobs; BL-036 sibling |
| **Created** | 2026-09-13 |
| **Ready date** | 2026-09-13 |
| **Done date** | 2026-09-13 |

---

## 1. Problem / user value

Email jobs (BL-032/034) are in git but the live `openportfo-jobs` zip is older. Operators need **one script** that updates the **existing** function and EventBridge rules (including the missing email cron) without CloudFormation or a new Lambda.

---

## 2. User story

As a **lab operator**, I want **one command to ship jobs code**, so that **daily news/price/snapshot/email run on the current Lambda**.

---

## 3. Scope

### In scope

- `scripts/package-lambda.ps1` / `.sh` — Linux wheels via Docker
- `scripts/deploy-lambda.ps1` / `.sh` — `update-function-code` on `openportfo-jobs`
- Update existing EventBridge rules to 00:00 ICT; add `openportfo-job-email` at 00:15 ICT
- Overlay SMTP from local `backend/.env` onto Lambda env **without printing secrets**
- Live deploy of current tree (authorized)

### Out of scope

- `create-function`, new Lambda name, CloudFormation on `openportfo-data`
- Changing EB
- Committing App Passwords

---

## 4. Acceptance criteria

- [x] AC1 Default target is existing function `openportfo-jobs` (fail if missing)
- [x] AC2 Scripts use `update-function-code`, not `aws lambda create-function` / `cloudformation deploy`
- [x] AC3 EventBridge: news/price/snapshot `cron(0 17 * * ? *)`; email `cron(15 17 * * ? *)`
- [x] AC4 Runbook one-liner; package uses Docker linux/amd64
