# BL-035 — HTTP API Gateway proxy in front of Beanstalk `/api/*`

| Field | Value |
|-------|--------|
| **ID** | `BL-035` |
| **Title** | Add Amazon API Gateway (HTTP API) as a proxy for FastAPI REST, keep chat SSE on Beanstalk |
| **Priority** | `P0` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Eng |
| **Requested by** | Stakeholder (assessment rubric: 6-pt Networking service) |
| **Related PRD / sprint** | PRD §12 D2; Arch §3.2, §12; BL-031 single-EB hosting |
| **Created** | 2026-09-13 |
| **Ready date** | 2026-09-13 |
| **Done date** | 2026-09-13 |

---

## 1. Problem / user value

The Academy lab dropped CloudFront, so the live demo has no **Networking & Content Delivery** service on the request path. Assessment 3 grades API Gateway at **6 marks** when it is fully implemented and invoked by the client (not Console-only). OpenPortfo already has FastAPI on Elastic Beanstalk; we need a thin HTTP API proxy so the browser’s REST calls go `Browser → API Gateway → Beanstalk`, without moving business logic off FastAPI or putting Lambda on the user path.

---

## 2. User story

As a **demo examiner**, I want **REST calls in the Network tab to hit `execute-api`**, so that **API Gateway is visibly automated by the UI** while FastAPI still owns auth, portfolio, and market adapters.

---

## 3. Scope

### In scope

- HTTP API (API Gateway v2) `ANY /api/{proxy+}` → Beanstalk `…/api/{proxy}` (`HTTP_PROXY`).
- CloudFormation on **lab** and **full** templates, **off by default** (`CreateHttpApi=false`).
- Frontend: bake `NEXT_PUBLIC_API_URL` to the Gateway URL when packaging; **chat SSE stays same-origin on Beanstalk**.
- CORS on the HTTP API (EB origin); FastAPI CORS unchanged for local `next dev`.
- Packaging scripts (`package-eb.ps1` / `.sh`) accept an optional API Gateway URL.
- Architecture / runbook variance: Gateway is a proxy only; Lambda remains EventBridge-only.

### Out of scope

- Cognito authorizer on Gateway (FastAPI JWKS stays the authz).
- Moving user APIs onto Lambda + Gateway.
- Putting `/`, `/_next/*`, or `/health` on Gateway.
- Creating/updating a live Academy stack (no real AWS mutate in this cycle).
- CloudFront, custom domain, usage plans, API keys, WAF.
- Changing portfolio/market/FX/job contracts.

---

## 4. Behaviour

### Happy path

1. Eng enables HTTP API in CloudFormation with `ApiBackendUrl=<EB origin>` and CORS origins = that origin.
2. Eng packages EB with `-ApiUrl https://<api-id>.execute-api.us-east-1.amazonaws.com` and `-AppUrl <EB origin>`.
3. Viewer opens the EB URL (UI). REST (`/api/portfolio`, `/api/auth/me`, news, markets, admin) goes to Gateway, which proxies to FastAPI.
4. Chat (`POST /api/chat/stream`) stays on the EB origin (no 30s Gateway timeout on SSE).
5. Cognito Hosted UI still returns to the **EB** `/auth/callback/` (unchanged).

### Edge cases / errors

- `CreateHttpApi=false` (default): no Gateway resources; local and current same-origin EB deploys unchanged.
- Empty `ApiBackendUrl` with `CreateHttpApi=true`: condition false, no API created (fail-safe).
- Local `next dev` on localhost: REST and chat still hit `http://127.0.0.1:8000`.
- CSV export through Gateway: `Content-Disposition` must be CORS-exposed so the client can name the file.
- Chat must not use the Gateway base even when `NEXT_PUBLIC_API_URL` is `execute-api`.

### UX notes

- Screens / routes: none new.
- Empty / loading / error states: unchanged.

---

## 5. Acceptance criteria

- [x] **AC1** Lab and full CloudFormation include a conditional HTTP API (`AWS::ApiGatewayV2::Api`) with `HTTP_PROXY` `ANY /api/{proxy+}` to `${ApiBackendUrl}/api/{proxy}`. Default is **not** created.
- [x] **AC2** When `NEXT_PUBLIC_API_URL` is an `execute-api` origin, `apiBase()` returns that origin (no trailing slash) so REST clients call Gateway.
- [x] **AC3** On a public (non-localhost) host, `chatApiBase()` is `""` (same-origin) even if REST `apiBase()` is Gateway — `sendChatMessage` hits `/api/chat/stream` on the page origin.
- [x] **AC4** On localhost / unset env, REST and chat still use the local FastAPI default (`http://127.0.0.1:8000`); existing local tests keep passing.
- [x] **AC5** `package-eb.ps1` / `package-eb.sh` can bake a non-empty API URL; empty API URL keeps today’s same-origin bake; leak guard still rejects `127.0.0.1:8000/api`.
- [x] **AC6** Architecture + EB runbook describe Path A as UI(EB) → Gateway → FastAPI for REST, chat same-origin, Lambda **not** behind Gateway. No live AWS deploy is required for this cycle.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | Unchanged (DynamoDB / S3 / Cognito) |
| New / changed APIs | None at FastAPI; new public hostname for the same `/api/*` REST surface |
| Auth required? | Same Bearer Cognito ID token; Gateway forwards `Authorization` |
| Caching / freshness | Unchanged |
| Jobs / schedules | Unchanged (EventBridge → Lambda) |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `frontend/lib/api.ts` (`chatApiBase`), `frontend/lib/chat.ts`, `frontend/lib/api.test.ts`, `frontend/lib/chat.test.ts` |
| Backend API | None (proxy target only) |
| Domain / services | None |
| Adapters | None |
| Infra / jobs | `infra/cloudformation-lab.yml`, `infra/cloudformation.yml`, `infra/README.md`, `scripts/package-eb.ps1`, `scripts/package-eb.sh` |
| Docs / tests | Arch, BL-031 runbook, new HTTP API runbook notes, CFN contract tests |

---

## 8. Dependencies & risks

- Depends on: existing EB environment URL at **deploy** time (chicken-egg: create/update Gateway after EB exists, then repackage frontend).
- Risks: Academy may block API Gateway (same class of risk as CloudFront). CORS misconfig. SSE through Gateway if AC3 is missed. Duplicate CORS headers (AWS HTTP API **ignores** backend CORS when CorsConfiguration is set).

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | HTTP API vs REST API? | resolved | HTTP API (`HTTP_PROXY`) — cheaper, enough for a catch-all proxy |
| 2 | Chat through Gateway? | resolved | No — same-origin Beanstalk (30s timeout + SSE) |
| 3 | Deploy live now? | resolved | No — repo + IaC only unless the user later authorizes AWS |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-09-13 | Need Gateway for marks vs product | Proxy only; FastAPI remains the API |
| 2026-09-13 | How much app change? | Env bake + `chatApiBase`; no route rewrites |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach: conditional HTTP API in lab + full CFN; `chatApiBase()`; `package-eb -ApiUrl`.
- PR / branch: `feat/BL-035-api-gateway` worktree `D:\rmit\cloud\a3-wt-bl035`
- Verification: see `docs/orchestration/walkthroughs/BL-035-walkthrough.md`. SA review `approve`. Live AWS not created.
