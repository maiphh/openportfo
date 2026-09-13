# SA Design — BL-038: Refresh stale deploy docs (Lambda + API Gateway live)

| Field | Value |
|-------|-------|
| **ID** | `BL-038` |
| **Title** | Refresh stale deploy docs — Lambda + API Gateway live 2026-09-13 |
| **Status** | `ready_for_implementation` |
| **Author (SA)** | SA |
| **Date** | 2026-09-13 |
| **Complexity** | `simple` |
| **Related PRD** | `docs/prd/OpenPortfo_PRD.md#12` (D2 HTTP API proxy), `#16` (live deploy) |
| **Related Arch** | `docs/architecture-design.md#3.2` (hosting map), `#3.1` (Path A/B) |
| **Feature file** | `docs/backlog/features/BL-038-deploy-docs-refresh.md` |

---

## 1. Context & constraints

- Problem / user value (1 paragraph, from feature file): Live AWS 2026-09-13 proves Lambda + Gateway + EB wired, but BACKLOG/BL-035 walkthrough/DEPLOY_STATUS/BL-035-037 feature files still claim `not deployed / not verified / optional manual invoke`. Update the paper trail to the dated live state so the 6+6 automation story is credible. No code/infra change.
- Locked stack constraints:
  - No API Gateway for user APIs (Beanstalk FastAPI only) — **revised D2**: Gateway is `HTTP_PROXY` to FastAPI, not Lambda user APIs; chat SSE stays same-origin; preserved, docs must repeat it.
  - No Next.js SSR (CSR/static export → EB single-hosting in lab; S3+CloudFront remains design target) — docs must not claim CloudFront live.
  - No browser-direct market APIs (server-side only) — unchanged.
  - Cache-first pricing, on-demand FX only (admin refresh) — unchanged; docs must keep `MARKET_CLIENT_MODE=fixture` caveat (live env still fixture).
  - Cognito JWT verification via JWKS — unchanged.
- Baseline (pre-existing, not introduced): `verify.ps1 -Profile quick` 2026-09-13 — `workflow-contract pass`, `ports-isolation fail` (`rg` missing binary), `backend-tests fail` (4 FX `fresh vs stale_ok`: `test_portfolio.py:325`, `test_portfolio_export.py:316`, `test_export_service.py:237`, `test_portfolio_service.py:244`), `frontend-lint pass`, `frontend-unit pass` (431). Same FX failures noted in BL-035 walkthrough §5.

## 2. Affected surfaces

| Layer | Paths / components | Change type |
|-------|--------------------|-------------|
| Frontend | none | — |
| Backend API | none | — |
| Domain / services | none | — |
| Ports | none | — |
| Adapters | none | — |
| Infra / jobs | none (reference only) | — |
| Docs / tests | `docs/backlog/BACKLOG.md` (1 row) | modify |
| Docs / tests | `docs/orchestration/walkthroughs/BL-035-walkthrough.md` (§§1/6/8) | modify |
| Docs / tests | `docs/implementation/sprints/sprint-12-aws-deploy/DEPLOY_STATUS.md` (date + tables) | modify |
| Docs / tests | `docs/backlog/features/BL-035-api-gateway.md` (§§8/9/11) | modify |
| Docs / tests | `docs/backlog/features/BL-036-deploy-eb-update.md` (§11), `BL-037-deploy-lambda-eventbridge.md` (§11+) | modify |
| Docs / tests | `docs/orchestration/reviews/BL-038-review.md` | create |

## 3. API & data model deltas

### 3.1 API

| Method & path | Auth | Request | Response | Notes |
|---------------|------|---------|----------|-------|
| none | — | — | — | docs-only; live smokes cited, not changed |

Live evidence to cite (read-only, 2026-09-13, `059358625850/us-east-1`):
- EB `openportfo-api-env` (`e-njepgizthf`) `Ready/Green`, `VersionLabel v-20260913-http-api`, `DateUpdated 2026-09-13T09:20:25Z`; `GET /health → {"status":"ok"}`.
- Gateway `7duvngr98b` (`https://7duvngr98b.execute-api.us-east-1.amazonaws.com`): route `ANY /api/{proxy+}` (`anmha94`) → integration `745svs2` `HTTP_PROXY ANY → http://...EB.../api/{proxy}`, `Payload 1.0`, `Timeout 30000`; stage `$default` `AutoDeploy`; smoke `GET .../api/auth/me → 401 {"detail":"Missing authorization header"}`.
- Lambda `openportfo-jobs`: `Active`, `LastModified 2026-09-13T10:05:38Z`, `CodeSize 20469631`, `python3.12`, `LabRole`; env `prod/aws/fixture` (keep fixture caveat).
- EventBridge 4x `ENABLED`: news/price/snapshot `cron(0 17 * * ? *)`, email `cron(15 17 * * ? *)`; `openportfo-job-news` target `NewsJob → ...:openportfo-jobs Input {"job":"news"}`.

### 3.2 Data model

```
Entity: none (docs-only)
```

- DynamoDB: none.
- S3 layout: none (cite existing `history/` + `snapshots/` only if DEPLOY_STATUS needs context; no key change).
- Schemas (`app/api/schemas.py`): none.

## 4. Sequence (happy path)

```
User → Docs (BACKLOG → walkthrough → DEPLOY_STATUS → feature files) → consistent live story
```

ASCII sequence:

```
1. BACKLOG BL-035 row → live Gateway/EB/rules + date (AC1).
2. BL-035 walkthrough §§1/6/8 → route/integration/stage + smokes; limitations rewritten to lab-recycle note (AC2).
3. DEPLOY_STATUS → 2026-09-13 tables + fixture caveat, no secrets (AC3).
4. BL-035 §§8/9/11 + BL-036/037 §11 → deployed-2026-09-13 notes (AC4).
5. BL-035 review untouched (AC5); workflow-contract pass (AC6).
```

## 5. Decisions (ADR style)

| # | Context | Decision | Consequence | Alternatives rejected |
|---|---------|----------|-------------|-----------------------|
| D1 | Historical `approve` reviews are point-in-time | Leave `BL-035-review.md` untouched; put live addendum in walkthrough + feature files | Preserves audit trail; avoids rewriting history | Editing the old review to pretend it verified live deploy |
| D2 | Lab recycles stale docs fast | Date every live claim `2026-09-13` + cite IDs (`7duvngr98b`, `v-20260913-http-api`, `2026-09-13T10:05:38Z`) | Future teardown reads as expiry, not error | Undated `live` assertions |
| D3 | `openportfo-data` stack is `UPDATE_ROLLBACK_COMPLETE` (runbook) | State Gateway came via `apigatewayv2` + EB `-ApiUrl` bundle, not full CFN deploy | No false CFN success claim | Claiming `CreateHttpApi=true` stack update |
| D4 | Live Lambda env still `MARKET_CLIENT_MODE=fixture` | Keep fixture caveat in DEPLOY_STATUS; do not claim live CoinGecko/vnstock | Third-party story stays honest (FX only provably live) | Silent `http` claim |
| D5 | No worktree for this item | Work on `main` working tree, review-ready, no commit without authorization | Minimal ceremony for docs-only non-substantial change | New `feat/BL-038-*` worktree + branch for 6 doc edits |

## 6. Complexity assessment

- [ ] Requires choosing between ≥2 libs/patterns → Researcher needed
- [ ] Security / auth / cost-critical AWS path
- [ ] No prior port/adapter pattern to reuse
- [ ] Risk to locked decisions

**Verdict:** `simple`

**If complex, research questions:** n/a (docs-only; live evidence already captured read-only).

## 7. Handoff to Implementor

### File ownership

- Allowed to edit: `docs/backlog/BACKLOG.md` (BL-035 row only), `docs/orchestration/walkthroughs/BL-035-walkthrough.md` (§§1/6/8 + handoff line), `docs/implementation/sprints/sprint-12-aws-deploy/DEPLOY_STATUS.md`, `docs/backlog/features/BL-035-api-gateway.md` (§§8/9/11), `docs/backlog/features/BL-036-deploy-eb-update.md` (§11), `docs/backlog/features/BL-037-deploy-lambda-eventbridge.md` (§11+), `docs/backlog/features/BL-038-deploy-docs-refresh.md` (status only), `docs/orchestration/reviews/BL-038-review.md` (create).
- Must NOT edit (owned by other active sprint/BL): `backend/**`, `frontend/**`, `infra/**`, `scripts/**`, `docs/orchestration/reviews/BL-035-review.md`, `docs/architecture-design.md`, `docs/prd/**`.

### TDD order

1. Test: `workflow-contract` gate is the docs-only test (no new unit tests; `rg`-missing + 4 FX failures are baseline).
2. Implement: AC1 → AC4 in file order above (one focused edit per AC, keep diffs dated, no secrets).
3. Verify: re-read each edited hunk; run `workflow-contract` check (full `verify.ps1` only to confirm no new failures vs baseline).

### Out-of-scope guardrails

- No `boto3/httpx` or code/config edits; no AWS mutate; no secrets (`SMTP_PASSWORD`, new EB URLs); no Athena/CloudFront/Containers claims; no FX test fixes; no commit/merge/push.

## 8. Acceptance criteria checklist (copy from feature file)

- [ ] AC1: BACKLOG BL-035 row cites Gateway `7duvngr98b`, EB `v-20260913-http-api`, 4 rules ENABLED, date `2026-09-13`.
- [ ] AC2: BL-035 walkthrough §§1/6/8 state live wiring + smokes; no `no AWS deploy` / `not created` for Gateway/Lambda path.
- [ ] AC3: DEPLOY_STATUS reflects 2026-09-13 live state with `fixture` caveat and no secrets.
- [ ] AC4: BL-035 §§8/9/11 + BL-036/037 §11 note live execution 2026-09-13.
- [ ] AC5: `BL-035-review.md` untouched.
- [ ] AC6: `workflow-contract` pass; baseline failures unchanged.

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Lab teardown re-stales docs | Explicit `2026-09-13` dating + runbook redeploy pointers (`deploy-eb.ps1`, `deploy-lambda.ps1`, `http-api-gateway.md`) |
| Secret leak in DEPLOY_STATUS | No-secret rule; cite env keys only (`MARKET_CLIENT_MODE=fixture`), never values for passwords/keys |
| Scope creep into code/FX fixes | Guardrails §7; FX `fresh vs stale_ok` stays pre-existing, referenced not fixed |

## 10. Research linkage (if any)

- Research doc: none (`simple`; no Researcher).
- Research recommendation adopted: n/a.

---

**SA sign-off:** _ready_for_implementation_ when checklist + TDD order complete.
