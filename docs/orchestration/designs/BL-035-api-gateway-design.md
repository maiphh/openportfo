# SA Design — BL-035: HTTP API Gateway proxy

| Field | Value |
|-------|-------|
| **ID** | `BL-035` |
| **Title** | HTTP API proxy in front of Beanstalk FastAPI REST |
| **Status** | `ready_for_implementation` |
| **Author (SA)** | Orchestrator / SA |
| **Date** | 2026-09-13 |
| **Complexity** | `complex` (locked-decision change + CORS) — research attached |
| **Related PRD** | `docs/prd/OpenPortfo_PRD.md` §12 D2 |
| **Related Arch** | `docs/architecture-design.md` §3.2, §12 |
| **Feature file** | `docs/backlog/features/BL-035-api-gateway.md` |
| **Research** | `docs/orchestration/research/BL-035-http-api-proxy-research.md` |

---

## 1. Context & constraints

Academy lab hosting (BL-031) serves UI + API from one Beanstalk URL, which removed CloudFront from the live path. Stakeholders want API Gateway on the REST path for Assessment 3 (6-pt high-value + Networking category) without rewriting FastAPI.

Locked stack **updated (variance, not a dual-server or Lambda-for-users change):**

- User business APIs remain FastAPI on Elastic Beanstalk.
- API Gateway is an **HTTP API pass-through** for `/api/*` REST only.
- Lambda remains EventBridge-only (no Gateway → Lambda user APIs).
- No Next.js SSR; UI still CSR static export on Beanstalk.
- No browser-direct market APIs.
- Cognito JWT still verified in FastAPI (JWKS). Gateway does not become the authorizer.
- Cache-first pricing; admin-only FX refresh.

## 2. Affected surfaces

| Layer | Paths / components | Change type |
|-------|--------------------|-------------|
| Frontend | `frontend/lib/api.ts` | **modify** — add `chatApiBase()` |
| Frontend | `frontend/lib/chat.ts` | **modify** — use `chatApiBase()` |
| Frontend | `frontend/lib/api.test.ts`, `chat.test.ts` | **modify** — AC2–AC4 |
| Backend API / domain / adapters | — | **none** |
| Infra | `infra/cloudformation-lab.yml`, `infra/cloudformation.yml` | **modify** — conditional HTTP API |
| Scripts | `scripts/package-eb.ps1`, `scripts/package-eb.sh` | **modify** — optional `-ApiUrl` / `API_URL` |
| Docs | architecture, runbooks, infra README | **modify** |
| Tests | `backend/tests/unit/infra/test_http_api_cfn.py` | **new** — template contract |

## 3. API & data model deltas

### 3.1 API

No FastAPI path changes. Public REST hostname may become:

`https://{api-id}.execute-api.us-east-1.amazonaws.com/api/...` → `https://{eb}/api/...`

| Method & path | Auth | Notes |
|---------------|------|--------|
| `ANY /api/{proxy+}` on HTTP API | Bearer forwarded | HTTP_PROXY, payload `1.0` |
| `POST /api/chat/stream` | Bearer | **Not** via Gateway; page origin |
| `GET /health`, `GET /`, `/_next/*` | — | Stay on Beanstalk only |

### 3.2 Data model

No DynamoDB/S3/schema change.

## 4. Sequence (happy path)

```
Browser (EB origin)
  ├─ GET /  → Beanstalk StaticFiles
  ├─ POST /api/chat/stream → Beanstalk FastAPI (same-origin)
  └─ GET /api/portfolio → HTTP API → Beanstalk FastAPI → DynamoDB/S3/markets
```

```
1. User opens https://<eb>/
2. Portfolio fetch: apiBase() = https://<api-id>.execute-api.us-east-1.amazonaws.com
3. Gateway HTTP_PROXY to https://<eb>/api/portfolio (Authorization forwarded)
4. FastAPI JWKS verify, same handlers as today
5. Chat: chatApiBase() = "" → POST https://<eb>/api/chat/stream
```

## 5. Decisions (ADR style)

| # | Context | Decision | Consequence | Alternatives rejected |
|---|---------|----------|-------------|-----------------------|
| D1 | Need Gateway marks without dropping Beanstalk | HTTP API `HTTP_PROXY` to EB `/api/{proxy}` | Browser REST shows `execute-api` | REST API v1; Lambda AWS_PROXY |
| D2 | Cross-origin REST | CORS on HTTP API; AllowHeaders Authorization, Content-Type, Accept; ExposeHeaders Content-Disposition | CSV filename still readable | FastAPI-only CORS (browser never hits EB for REST) |
| D3 | SSE 30s Gateway timeout | `chatApiBase()` same-origin on public hosts | Chat stays on EB | Proxy chat too |
| D4 | Auth | Keep FastAPI JWKS; no Cognito authorizer on Gateway | OPTIONS stays simple | Gateway authorizer |
| D5 | Lab chicken-egg | `CreateHttpApi` default false; enable with `ApiBackendUrl` after EB exists; then repackage with `-ApiUrl` | Two-step deploy | Quick-create Target on `$default` (would also catch `/`) |
| D6 | Local/dev | Unset `NEXT_PUBLIC_API_URL` unchanged | localhost still uses `:8000` | Always Gateway |

Research → D1/D2: AWS HTTP API CORS ignores backend CORS when configured; `{proxy+}` maps to `{proxy}` in IntegrationUri.

## 6. Complexity assessment

- [x] Security / auth / CORS
- [x] Risk to previous “no API Gateway” lock (explicit variance)

**Verdict:** `complex` (research done; no extra lib)

## 7. Handoff to Implementor

### File ownership

- Allowed: feature/design/research already written; frontend `lib/api.ts` + `lib/chat.ts` + tests; both CFN templates; package-eb scripts; arch + runbooks; new pytest contract.
- Must NOT: domain/services, market adapters, job handlers, Cognito Hosted UI flow, live `aws cloudformation deploy`.

### TDD order

1. Test: `apiBase()` with execute-api URL (AC2).
2. Test: `chatApiBase()` public host → `""`; localhost → local default (AC3–AC4).
3. Test: `sendChatMessage` URL is `/api/chat/stream` when REST base is Gateway.
4. Implement `chatApiBase` + wire `chat.ts`.
5. Test: CFN files contain conditional HTTP API resources (AC1).
6. Implement CFN + package-eb `-ApiUrl` (AC5).
7. Docs (AC6).

### Out-of-scope guardrails

- Do not invoke real AWS.
- Do not put UI or health on Gateway.
- Do not add boto3 in services.
- Do not change `apiBase()` empty-string same-origin meaning (BL-031).

## 8. Acceptance criteria checklist (copy from feature file)

- [ ] AC1 CFN conditional HTTP API proxy
- [ ] AC2 `apiBase()` Gateway URL
- [ ] AC3 chat same-origin on public host
- [ ] AC4 localhost unchanged
- [ ] AC5 package-eb optional ApiUrl + leak guard
- [ ] AC6 as-built docs; no live deploy required

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Lab denies API Gateway | Template still demos intent; runbook says confirm console |
| Duplicate CORS | Gateway CorsConfiguration; AWS ignores backend CORS |
| Chat via Gateway | `chatApiBase()` never uses execute-api by default |
| Mixed content | Bake `https://` execute-api URL |
| LocalStack cannot prove Gateway→EB | CFN contract tests + frontend unit tests; LocalStack probe only to show DynamoDB/S3 templates still intact |

## 10. Research linkage

- `docs/orchestration/research/BL-035-http-api-proxy-research.md`
- Adopted: HTTP API HTTP_PROXY + Gateway CORS + greedy `/api/{proxy+}`.

---

**SA sign-off:** `ready_for_implementation`
