# Walkthrough — BL-035: HTTP API Gateway proxy

| Field | Value |
|-------|-------|
| **ID** | `BL-035` |
| **Branch** | `feat/BL-035-api-gateway` |
| **Worktree** | `D:\rmit\cloud\a3-wt-bl035` |
| **Implementor** | Eng |
| **Date** | 2026-09-13 |
| **SA design** | `docs/orchestration/designs/BL-035-api-gateway-design.md` |
| **Research** | `docs/orchestration/research/BL-035-http-api-proxy-research.md` |

---

## 1. Summary (what was built)

HTTP API (API Gateway v2) is now described in both CloudFormation templates as a **conditional** `HTTP_PROXY` for `ANY /api/{proxy+}` → Beanstalk FastAPI. Default is off. The frontend can bake `NEXT_PUBLIC_API_URL` to the Gateway origin; **chat SSE stays same-origin** on public hosts via `chatApiBase()`. **Live addendum 2026-09-13 (BL-038, read-only): Gateway `7duvngr98b` exists with route `ANY /api/{proxy+}` (`anmha94`) → integration `745svs2` `HTTP_PROXY ANY → http://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com/api/{proxy}` (`Payload 1.0`, `Timeout 30000`), stage `$default` `AutoDeploy`; EB `openportfo-api-env` is `Ready/Green` on `v-20260913-http-api`; smoke `GET /health → {"status":"ok"}`, `GET .../api/auth/me` via Gateway → `401 {"detail":"Missing authorization header"}`. No live resources were created in the BL-035 cycle itself; the live wiring above was verified later via `describe/get/curl` only.

## 2. Files changed (path:line)

| File | Change | Lines |
|------|--------|-------|
| `frontend/lib/api.ts:40` | Added `chatApiBase()` | |
| `frontend/lib/chat.ts:1,239,250` | Chat fetch uses `chatApiBase()` | |
| `frontend/lib/api.test.ts` | Gateway URL + chat/REST split tests | |
| `frontend/lib/chat.test.ts` | SSE URL stays `/api/chat/stream` on public host | |
| `infra/cloudformation-lab.yml:45,387` | `CreateHttpApi` + HTTP API resources | |
| `infra/cloudformation.yml` | Same HTTP API block | |
| `scripts/package-eb.ps1:30,63,125` | `-ApiUrl` bake + guard | |
| `scripts/package-eb.sh` | `API_URL` env bake | |
| `backend/tests/unit/infra/test_http_api_cfn.py` | Template + script contract | |
| `docs/runbooks/http-api-gateway.md` | Deploy order (not executed) | |
| `docs/architecture-design.md`, `docs/prd/OpenPortfo_PRD.md` | D2 revised | |

## 3. Decisions & deviations from SA design

| # | SA said | Did | Reason |
|---|---------|-----|--------|
| 1 | HTTP API HTTP_PROXY | Yes | — |
| 2 | Chat same-origin | Yes | — |
| 3 | No live AWS | Yes | User did not authorize mutate |

## 4. How to verify

```powershell
cd D:\rmit\cloud\a3-wt-bl035\frontend
npm run lint
npm test
npm run build
npm run test:e2e

cd D:\rmit\cloud\a3-wt-bl035\backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/unit/infra/test_http_api_cfn.py
```

Live Gateway (only with AWS authorization): `docs/runbooks/http-api-gateway.md`.

## 5. Test evidence (paste)

Frontend: **431 passed** (was 426). Lint pass. `next build` pass. Playwright: **5 passed, 4 skipped** (`single-eb-smoke` needs `SINGLE_EB_SMOKE=1`).

Backend focused: `tests/unit/infra/test_http_api_cfn.py` **3 passed**.

Backend full suite: **588 passed, 5 skipped, 4 failed** — the four failures are **pre-existing** (FX `fresh` vs `stale_ok`), present in the quick baseline before this feature:

- `test_portfolio_with_stored_fx_display_currency`
- `test_export_fx_conversion_when_stored_rate_exists`
- `test_portfolio_export_fx_conversion`
- `test_get_portfolio_reads_fx_repo_not_http`

LocalStack probe: **pass** (`http://localhost:4566`, existing `openportfo-localstack` container). DynamoDB/S3 contracts unchanged. LocalStack does **not** prove HTTP API → Beanstalk.

## 6. API / UX verification

- Local default: REST and chat still use `http://127.0.0.1:8000` on localhost.
- Unit: public host + `NEXT_PUBLIC_API_URL=https://abc123.execute-api.us-east-1.amazonaws.com` → `apiBase()` Gateway, `sendChatMessage` → `/api/chat/stream`.
- Browser: smoke e2e still loads markets nav (same-origin local).
- Live `execute-api` Network tab: **verified 2026-09-13 (BL-038, read-only)** — `GET https://7duvngr98b.execute-api.us-east-1.amazonaws.com/api/auth/me → 401 {"detail":"Missing authorization header"}` (FastAPI through Gateway); `GET http://...EB.../health → {"status":"ok"}`. BL-035 cycle itself did no AWS deploy.

## 7. Ports isolation check

No new SDK imports in `services/` / `api/` / `domain/` / `jobs`. Gateway is CloudFormation only.

## 8. Known limitations / follow-ons

- HTTP API is **live as `7duvngr98b` since 2026-09-13** (created via `apigatewayv2` + EB `-ApiUrl` bundle per `docs/runbooks/http-api-gateway.md`; full CFN `CreateHttpApi=true` not used because `openportfo-data` is `UPDATE_ROLLBACK_COMPLETE`). Lab recycle will require re-creation + EB repack — see BL-038/DEPLOY_STATUS 2026-09-13 section.
- Academy may deny `apigateway:*` (same class as CloudFront).
- Chicken-egg: create Gateway after EB exists, then repackage with `-ApiUrl`.
- Pre-existing FX freshness test failures are out of scope.

## 9. Handoff to SA Review

- Walkthrough ready for SA review: yes
- AC checklist self-assessed: AC1–AC6 repo evidence yes; live invoke no (explicit non-goal)
