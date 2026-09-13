# Runbook — BL-035 HTTP API Gateway in front of Beanstalk REST

Lab hosting (BL-031) serves the Next.js static export from Elastic Beanstalk.
This runbook adds an **HTTP API** so browser **REST** calls go:

`Browser → https://{api-id}.execute-api.us-east-1.amazonaws.com/api/… → Beanstalk FastAPI`

Chat SSE (`POST /api/chat/stream`) **stays on the Beanstalk origin**.
Gateway does **not** front `/`, `/_next/*`, `/health`, or Lambda jobs.

Related: `docs/backlog/features/BL-035-api-gateway.md`,
`docs/orchestration/designs/BL-035-api-gateway-design.md`.

**Do not run these AWS commands unless you are authorized to mutate the lab account.**

---

## 1. Order of operations (chicken-egg)

1. Elastic Beanstalk environment already exists (note the origin, https preferred).
2. Update CloudFormation with that origin as `ApiBackendUrl` and CORS origin.
3. Capture `HttpApiUrl` (no trailing slash).
4. Repackage the frontend with `-ApiUrl <HttpApiUrl>` and redeploy the EB bundle.
5. Confirm the Network tab: REST → `execute-api`; chat → same EB host.

Local `next dev` is unchanged: leave `NEXT_PUBLIC_API_URL` unset.

---

## 2. CloudFormation (lab template)

```powershell
aws cloudformation deploy `
  --template-file infra/cloudformation-lab.yml `
  --stack-name openportfo-lab `
  --region us-east-1 `
  --parameter-overrides `
    CreateHttpApi=true `
    ApiBackendUrl=https://<eb-env>.elasticbeanstalk.com `
    HttpApiCorsOrigins="http://localhost:3000,http://localhost:5173,https://<eb-env>.elasticbeanstalk.com"
```

Full template: same parameters on `infra/cloudformation.yml`.

`CreateHttpApi` defaults to **false**. Empty `ApiBackendUrl` also skips the API
(`EnableHttpApi` requires both).

Output: `HttpApiUrl` → bake as `NEXT_PUBLIC_API_URL`.

If the deploy fails with an authorization error, the Learner Lab may block
API Gateway (same class of issue as CloudFront). The templates still document
the intended architecture.

---

## 3. Package frontend for Gateway REST

```powershell
.\scripts\package-eb.ps1 `
  -AppUrl https://<eb-env>.elasticbeanstalk.com `
  -ApiUrl https://<api-id>.execute-api.us-east-1.amazonaws.com
```

Linux:

```bash
API_URL=https://<api-id>.execute-api.us-east-1.amazonaws.com \
  ./scripts/package-eb.sh https://<eb-env>.elasticbeanstalk.com
```

Omit `-ApiUrl` / `API_URL` to keep same-origin `/api/*` (BL-031).

Then upload `eb-bundle.zip` to Elastic Beanstalk (same as BL-031).

FastAPI `CORS_ORIGINS` can keep localhost + EB origin for local and chat;
HTTP API CORS is what the browser uses for REST.

---

## 4. Verify

1. Open `https://<eb-env>.elasticbeanstalk.com/` → app HTML.
2. Sign in. Network tab:
   - `GET …execute-api…/api/auth/me` or `/api/portfolio` → 200 JSON
   - `POST …elasticbeanstalk.com/api/chat/stream` → SSE on the **EB** host
3. `GET https://<eb>/health` still hits Beanstalk directly (not Gateway).
4. Export CSV still downloads (Gateway exposes `Content-Disposition`).

---

## 5. Rollback

1. Repackage **without** `-ApiUrl` (same-origin REST).
2. Redeploy EB.
3. Optionally set `CreateHttpApi=false` and update the stack (deletes the HTTP API).
