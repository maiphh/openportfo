# Runbook — BL-031 Single-EB hosting (static frontend from Beanstalk API)

Lab constraint: Academy lab blocks CloudFront, so the locked
`S3 + CloudFront (UI) + Beanstalk (API)` split cannot be demoed.
This runbook deploys **one public URL** — the Elastic Beanstalk environment —
serving both the Next.js static export and the FastAPI API from a **single
`uvicorn` process** (no `next start` on EB, no second server).

Related: `docs/backlog/features/BL-031-single-eb-hosting.md`,
`docs/orchestration/designs/BL-031-single-eb-hosting-design.md`.

---

## 1. Environment variables (EB Software Configuration)

| Variable | Value | Notes |
|----------|-------|-------|
| `SERVE_FRONTEND` | `true` | Kill-switch: `false` forces API-only mode (`GET /` → JSON 404) |
| `FRONTEND_DIR` | `static_web` (default) | Resolved under `backend/`; prefers `backend/static_web/`, falls back to `backend/app/static_web/` |
| `APP_ENV` | `prod` | Triggers production runtime validation |
| `AUTH_MODE` | `cognito` | Required in prod |
| `STORAGE_BACKEND` | `aws` | Required in prod |
| `DATA_BUCKET` | `<from stack Outputs.DataBucketName>` | S3 data bucket (history/snapshots) |
| `COGNITO_REGION` / `COGNITO_USER_POOL_ID` / `COGNITO_APP_CLIENT_ID` | `<from stack Outputs>` | JWT verification |
| `CORS_ORIGINS` | keep localhost dev origins | Same-origin needs no CORS change |
| `EXCHANGE_RATE_API_KEY` | `<server-side only>` | Never in frontend or Git |

`GET /health` stays the EB healthcheck (see
`backend/.ebextensions/02_health.config` — unchanged).

---

## 2. Cognito update order (do this FIRST — else login fails)

`redirect_mismatch` is the expected failure if the EB origin is not
registered. Order matters:

1. Deploy / update the CloudFormation lab stack with the EB origin appended:
   ```powershell
   aws cloudformation deploy `
     --template-file infra/cloudformation-lab.yml `
     --stack-name openportfo-lab `
     --region us-east-1 `
     --parameter-overrides `
       CognitoCallbackUrls="http://localhost:3000/auth/callback,http://localhost:5173/auth/callback,https://placeholder.cloudfront.net/auth/callback,https://<eb-env>.elasticbeanstalk.com/auth/callback/" `
       CognitoLogoutUrls="http://localhost:3000/,http://localhost:5173/,https://placeholder.cloudfront.net/,https://<eb-env>.elasticbeanstalk.com/"
   ```
   (Trailing slashes required: frontend `callbackRedirectUri` ends with
   `/auth/callback/` and `postLogoutUri` ends with `/`.)
2. Note the real EB origin (`https://<eb-env>.elasticbeanstalk.com`) —
   never commit it; pass it as the packaging `-AppUrl`.
3. Then package + deploy below (frontend bakes `NEXT_PUBLIC_APP_URL=<eb>`,
   with `window.location.origin` fallback in `lib/cognito.ts` if empty).

---

## 3. Build / package / deploy

Update the **existing** environment (no new env, no CloudFormation):

```powershell
# From repo root, Academy lab session started:
.\scripts\deploy-eb.ps1
```

That packages, uploads a new application version, and runs `update-environment` on `openportfo-api-env`. Linux: `./scripts/deploy-eb.sh`.

Manual package-only (if you will upload the zip yourself):

```powershell
# Same-origin REST (BL-031 default):
.\scripts\package-eb.ps1 -AppUrl https://<eb-env>.elasticbeanstalk.com

# REST via HTTP API Gateway (BL-035), after HttpApiUrl exists:
.\scripts\package-eb.ps1 `
  -AppUrl https://<eb-env>.elasticbeanstalk.com `
  -ApiUrl https://<api-id>.execute-api.us-east-1.amazonaws.com
```

`eb-bundle.zip` lands at the repo root. Prefer `.\scripts\deploy-eb.ps1` over `eb create` / a new environment.

What the script does: `npm run build` with `NEXT_PUBLIC_API_URL=""` by
default (same-origin `/api/*`), or the Gateway origin when `-ApiUrl` is set.
Chat SSE always uses same-origin on the public EB host (`chatApiBase()`).
Leak-guard rejects baked `127.0.0.1:8000/api`. See
`docs/runbooks/http-api-gateway.md`.
clean-copy `frontend/out/` → `backend/static_web/`, zip allow-list
(`app/`, `Procfile`, `requirements.txt`, `.ebextensions/`, `static_web/`
— `.venv`/`__pycache__`/`node_modules`/`.next` excluded by construction).

Linux/CI equivalent: `./scripts/package-eb.sh <app-url> [output-zip]`.

---

## 4. Verify on EB

1. `GET https://<eb-env>.elasticbeanstalk.com/` → app HTML
   (redirects to `/markets/stock/` per `app/page.tsx`).
2. `GET https://<eb-env>.elasticbeanstalk.com/health` → `{"status":"ok"}`.
3. Deep link `GET .../portfolio/` and `.../auth/callback/` → HTML 200
   (refresh on any route still renders).
4. Browser network tab: without `-ApiUrl`, API calls go to same-origin
   `/api/*`. With BL-035 `-ApiUrl`, REST goes to `execute-api` and chat
   stays on the EB origin. No `127.0.0.1:8000`.
5. Login via Cognito Hosted UI returns to `.../auth/callback/` → dashboard.

---

## 5. Rollback (API-only mode)

No redeploy of code needed for diagnostics:

1. Set `SERVE_FRONTEND=false` in the EB environment Software Configuration.
2. `GET /` returns JSON `{"detail":"frontend not bundled"}` (404);
   all `/api/*` + `/health` keep working.
3. Re-enable with `SERVE_FRONTEND=true` (or redeploy a bundle whose
   `static_web/` was mis-packed — missing/empty dir also degrades to
   API-only with a warning log, never a 500).

---

## 6. Demo narrative (why no CloudFront in the diagram story)

> "The design target is S3 + CloudFront for the UI, but the Academy lab
> blocks CloudFront distributions, so this deployment serves the same static
> export from the Beanstalk API process — one public URL, still a single
> Python server, no SSR, no browser-direct market calls. The S3 + Athena
> evidence remains via the **data** bucket: price-history JSON, daily
> portfolio snapshots, and the Athena query over `snapshots/` partitions."

Marks mapping: Beanstalk + Lambda (compute), HTTP API Gateway (networking,
when enabled), DynamoDB (database), S3 **data** + Athena (storage/analytics).
