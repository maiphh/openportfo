# Research — BL-035: HTTP API proxy in front of Beanstalk

| Field | Value |
|-------|-------|
| **ID** | `BL-035` |
| **Date** | 2026-09-13 |
| **Researcher** | Orchestrator (inline; CORS + integration type) |
| **SA questions** | Q1 HTTP API vs REST API; Q2 CORS with HTTP_PROXY; Q3 path-variable proxy URI |
| **Status** | `done` |

---

## 1. Problem restatement

We must put API Gateway on the **browser REST path** without replacing FastAPI or Lambda jobs. Choice of API type, CORS owner, and `{proxy+}` URI mapping must match AWS HTTP API behaviour so the demo does not fail OPTIONS or drop path segments.

---

## 2. Search method

- Queries: `AWS API Gateway HTTP API HTTP_PROXY CloudFormation`, `http-api-cors`, `http-api-develop-integrations-http`
- Sources fetched:
  - https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-apigatewayv2-integration.html
  - https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-apigatewayv2-api.html
  - https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html
  - https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-http.html

## 3. Options

| # | Option | Pros | Cons | Cost | Security | Complexity | Source |
|---|--------|------|------|------|----------|------------|--------|
| 1 | **HTTP API + HTTP_PROXY** `ANY /api/{proxy+}` → EB | Pass-through headers/body; `$default` stage (no `/prod` prefix); built-in CORS | 30s max; poor SSE | HTTP API cheap at demo scale | Forwards Bearer; no extra authorizer | Low | [Integration](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-apigatewayv2-integration.html), [HTTP proxy](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-http.html) |
| 2 | REST API (v1) HTTP proxy | Familiar in older labs | More resources (Deployment, Resource, Method); `/stage` prefix | Similar/higher | Same | Medium | — |
| 3 | HTTP API **AWS_PROXY → Lambda** for user APIs | Classic “Gateway + Lambda” slide | Duplicates/abandons Beanstalk 6-pt compute | Lambda free tier | Rewrite all routes | High — rejected | — |

## 4. Tradeoff analysis

- Locked stack: FastAPI on Beanstalk stays the business API; Lambda stays EventBridge-only.
- CORS: if HTTP API `CorsConfiguration` is set, API Gateway answers OPTIONS and **ignores backend CORS headers** ([http-api-cors](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html)). FastAPI CORS remains for local `localhost:3000 → :8000`.
- Path mapping: greedy `{proxy+}` on `/api/{proxy+}` integrates to `https://backend/api/{proxy}` ([HTTP proxy with path variables](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-http.html)).
- Chat SSE: HTTP API integration timeout is 30s — keep chat off Gateway.

## 5. Recommendation

**Recommended:** Option 1.

**Rationale:**

- Cited: [HTTP_PROXY](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-apigatewayv2-integration.html) — client request passed through as-is (`PayloadFormatVersion: "1.0"`).
- Cited: [CORS](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html) — Gateway adds CORS headers; backend CORS ignored when configured.
- Cited: [path variables](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-http.html) — `/parent/{proxy+}` → `https://endpoint/{proxy}`.

## 6. What SA should lock

- Decision D1: HTTP API, not REST API, not Lambda proxy.
- Decision D2: CORS on Gateway; expose `Content-Disposition` for CSV.
- Decision D3: Chat same-origin; REST via `NEXT_PUBLIC_API_URL`.
- Infra: `CreateHttpApi` default `false`; no IAM role required for public HTTP_PROXY.
- Risk if ignored: SSE timeouts, `/prod` prefix confusion, or losing Beanstalk marks by moving APIs to Lambda.

## 7. Open questions (if any)

- Whether the Learner Lab SCP allows `apigateway:*` — only knowable at deploy time.

---

**Verification:** URLs fetched via WebFetch/WebSearch on 2026-09-13. No hallucinated links.
