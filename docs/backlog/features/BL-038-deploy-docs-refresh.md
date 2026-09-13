# BL-038 — Refresh stale deploy docs (Lambda + API Gateway live 2026-09-13)

| Field | Value |
|-------|--------|
| **ID** | `BL-038` |
| **Title** | Refresh stale deploy docs — Lambda + API Gateway live |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Eng |
| **Requested by** | User (`update stale docs saying not deployed`) |
| **Related PRD / sprint** | PRD §12 D2; Arch §3.2; BL-035/036/037; sprint-12 `DEPLOY_STATUS.md` |
| **Created** | 2026-09-13 |
| **Ready date** | 2026-09-13 |
| **Done date** | 2026-09-13 |

---

## 1. Problem / user value

Live AWS (checked 2026-09-13, account `059358625850`, `us-east-1`) shows Lambda `openportfo-jobs` + HTTP API `7duvngr98b` + EB `openportfo-api-env` all deployed and wired, but docs still say `not deployed / not verified / optional manual invoke`. Examiners reading docs will under-claim Lambda (6 pts) + API Gateway (6 pts) automation. Fix docs so the paper trail matches the live evidence (no code/infra change).

---

## 2. User story (optional)

As a **demo examiner**, I want **docs to state the live Gateway/Lambda wiring with dates and IDs**, so that **the 6+6 marks story is credible without re-checking the console**.

---

## 3. Scope

### In scope

- `docs/backlog/BACKLOG.md` BL-035 row: replace `not deployed to AWS` with live state (Gateway `7duvngr98b`, EB `v-20260913-http-api`, 4 EventBridge rules ENABLED, date).
- `docs/orchestration/walkthroughs/BL-035-walkthrough.md` §§1/6/8: replace `No live AWS resources were created` / `not verified (no AWS deploy)` with 2026-09-13 live wiring + smokes.
- `docs/implementation/sprints/sprint-12-aws-deploy/DEPLOY_STATUS.md`: bump `Date` 2026-08-09 → 2026-09-13 live section (EB version/health, Gateway route+integration, Lambda LastModified, EventBridge rules, `MARKET_CLIENT_MODE=fixture` caveat). No secrets.
- `docs/backlog/features/BL-035-api-gateway.md` §§8/9/11: flip `no live AWS mutate` / `Deploy live now? No` to deployed state + follow-on (redeploy on lab recycle).
- `docs/backlog/features/BL-036-deploy-eb-update.md` + `BL-037-deploy-lambda-eventbridge.md` implementation notes: note scripts were executed live 2026-09-13 (EB `v-20260913-http-api`, Lambda `2026-09-13T10:05:38Z`).

### Out of scope

- Any `backend/`, `frontend/`, `infra/`, `scripts/` code change.
- Creating/updating/deleting live AWS resources (read-only `describe/get` only for evidence).
- Athena/CloudFront/Containers claims; FX test fixes; committing secrets (`SMTP_PASSWORD`, EB URLs beyond existing placeholders).
- Rewriting historical SA reviews (`BL-035-review.md` stays point-in-time; addendum lives in walkthrough/feature files).
- Merge/push/deploy (review-ready only).

---

## 4. Behaviour

### Happy path

1. Reader opens BACKLOG → BL-035 row states live Gateway + date.
2. Reader opens BL-035 walkthrough → sees route `ANY /api/{proxy+}`, integration `HTTP_PROXY → http://...EB.../api/{proxy}`, stage `$default`, smokes (`GET /health → ok`, `GET .../api/auth/me via Gateway → 401 Missing authorization header`).
3. Reader opens DEPLOY_STATUS → sees 2026-09-13 table (EB Ready/Green, Gateway ID, Lambda + 4 rules ENABLED) and the remaining `fixture` caveat for markets.

### Edge cases / errors

- Lab teardown later invalidates live state → docs are dated (`2026-09-13`) so a future recycle is a new deploy, not a doc lie.
- `openportfo-data` stack `UPDATE_ROLLBACK_COMPLETE` (runbook) → docs state Gateway was created via `apigatewayv2` + EB bundle `-ApiUrl`, not via full CFN deploy.
- No secrets in docs (Dynamo/SMTP values stay out; existing placeholder hostnames only).

### UX notes

- Screens / routes: none.
- Empty / loading / error states: n/a (docs).

---

## 5. Acceptance criteria

- [ ] **AC1** BACKLOG BL-035 row no longer says `not deployed`; cites Gateway `7duvngr98b`, EB `v-20260913-http-api`, 4 rules ENABLED, date `2026-09-13`.
- [ ] **AC2** BL-035 walkthrough §§1/6/8 state live wiring + smokes; no remaining `no AWS deploy` / `not created` claim for Gateway/Lambda path.
- [ ] **AC3** DEPLOY_STATUS `Date` + tables reflect 2026-09-13 live state (EB/ Gateway/ Lambda/ EventBridge) with `fixture` caveat and no secrets.
- [ ] **AC4** BL-035 feature §§8/9/11 + BL-036/037 §11 note live execution 2026-09-13 (not `Live AWS not mutated/created`).
- [ ] **AC5** Historical `BL-035-review.md` untouched (point-in-time `approve` preserved).
- [ ] **AC6** Docs-only: `workflow-contract` pass; no `boto3/httpx` change; pre-existing `backend-tests` 4 FX + `ports-isolation rg` failures recorded as baseline, not introduced.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | Live `describe/get` 2026-09-13 (EB Ready/Green, Gateway route/integration/stage, Lambda config, EventBridge rules+targets, curl smokes) |
| New / changed APIs | none |
| Auth required? | n/a (docs) |
| Caching / freshness | n/a |
| Jobs / schedules | Document only: news/price/snapshot `cron(0 17 * * ? *)`, email `cron(15 17 * * ? *)`, all ENABLED |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | none |
| Backend API | none |
| Domain / services | none |
| Adapters | none |
| Infra / jobs | none (docs reference only) |
| Docs / tests | `docs/backlog/BACKLOG.md`, `docs/orchestration/walkthroughs/BL-035-walkthrough.md`, `docs/implementation/sprints/sprint-12-aws-deploy/DEPLOY_STATUS.md`, `docs/backlog/features/BL-035-api-gateway.md`, `docs/backlog/features/BL-036-deploy-eb-update.md`, `docs/backlog/features/BL-037-deploy-lambda-eventbridge.md`, `docs/orchestration/designs/BL-038-deploy-docs-refresh-design.md`, `docs/orchestration/reviews/BL-038-review.md` |

---

## 8. Dependencies & risks

- Depends on: live evidence captured 2026-09-13 (IDs above); baseline `verify.ps1 -Profile quick` failures recorded (4 FX `fresh vs stale_ok`, `rg` missing).
- Risks: lab recycle stales docs again → mitigated by explicit dates + `runbook` redeploy pointer; secret leak → mitigated by no-secret rule.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Rewrite BL-035 review? | resolved | No — point-in-time; addendum in walkthrough/feature files |
| 2 | New worktree? | resolved | No — docs-only, not substantial; work on `main` working tree, review-ready, no commit without authorization |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-09-13 | Scope = docs only, no AWS mutate | Read-only `describe/get/curl` for evidence; no deploy |
| 2026-09-13 | Live IDs to cite | `7duvngr98b`, `v-20260913-http-api`, Lambda `2026-09-13T10:05:38Z`, 4 rules ENABLED |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach: dated live-state edits only; historical reviews untouched.
- PR / branch: `main` working tree (docs-only, not substantial — no worktree); no commit without authorization.
- Verification: `workflow-contract` pass; `verify.ps1 -Profile quick` baseline failures preserved (see BL-038 design §baseline).
