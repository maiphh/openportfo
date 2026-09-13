# SA Review — BL-035: HTTP API Gateway proxy

| Field | Value |
|-------|-------|
| **ID** | `BL-035` |
| **Reviewer (SA)** | SA (same cycle) |
| **Date** | 2026-09-13 |
| **Walkthrough** | `docs/orchestration/walkthroughs/BL-035-walkthrough.md` |
| **Verdict** | `approve` |

---

## 1. AC verification

| AC | Satisfied? | Evidence (file:line or test) | Note |
|----|------------|------------------------------|------|
| AC1 | yes | `infra/cloudformation-lab.yml:45` `CreateHttpApi` default false; `:422` `HTTP_PROXY`; `:433` `ANY /api/{proxy+}`; same in `infra/cloudformation.yml`; `test_http_api_cfn.py` | Not deployed live |
| AC2 | yes | `frontend/lib/api.ts` `apiBase()`; `api.test.ts` execute-api case | |
| AC3 | yes | `chatApiBase()` `frontend/lib/api.ts:40`; `chat.ts:239`; chat.test public-host SSE URL | |
| AC4 | yes | localhost still uses `apiBase()` / `DEFAULT_API`; existing chat tests unchanged | |
| AC5 | yes | `scripts/package-eb.ps1:30,63,125`; `package-eb.sh` `API_URL`; contract test | Empty ApiUrl keeps same-origin |
| AC6 | yes | `docs/architecture-design.md` §3.2; `docs/runbooks/http-api-gateway.md`; PRD D2 revised | No live AWS |

## 2. Architecture checks

- [x] Ports isolation — Gateway is CFN + browser URL only; no boto3 in services/api/domain/jobs.
- [x] Locked decisions — **revised D2**: Gateway is HTTP_PROXY to FastAPI, not Lambda user APIs; no SSR; Cognito JWKS still in FastAPI; chat not on Gateway.
- [x] Cost/budget — HTTP API at demo scale; default off so unused labs pay nothing.
- [x] Security — Bearer forwarded; no Cognito authorizer; CORS explicit origins; no secrets in Git.

## 3. Code quality

- [x] Tests meaningful (URL split + CFN contract), not `assert True`.
- [x] File ownership respected.
- [x] FastAPI error model unchanged.

## 4. Issues (if request_changes)

None for this BL.

Pre-existing (not blocking BL-035): four FX tests expect `fresh` and get `stale_ok`. Present in baseline before this work.

## 5. Decision

- **approve.** Orchestrator may merge `feat/BL-035-api-gateway` when requested. **Do not** `aws cloudformation deploy` / EB upload unless the user authorizes real AWS.
- Live Gateway invoke remains a **deploy** step, not an implementation defect.

## 6. Notes for Orchestrator

- Worktree: `D:\rmit\cloud\a3-wt-bl035`
- Next for marks: user-authorized lab deploy per `docs/runbooks/http-api-gateway.md`, then Network-tab screenshot of `execute-api`.
