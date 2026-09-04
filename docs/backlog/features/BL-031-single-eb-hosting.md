# BL-031 — Single-EB hosting (serve static frontend from Beanstalk API)

| Field | Value |
|-------|--------|
| **ID** | `BL-031` |
| **Title** | Serve Next.js static export from the same Elastic Beanstalk instance (no CloudFront) |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Eng (unassigned) |
| **Requested by** | Stakeholder (lab has no CloudFront) |
| **Related PRD / sprint** | PRD §8.11, §12, §15–16; Arch §3, §12; sprint-12-deploy |
| **Created** | 2026-09-04 |
| **Ready date** | 2026-09-04 |
| **Done date** | |

---

## 1. Problem / user value

Academy lab blocks CloudFront, so the locked `S3 + CloudFront (UI) + Beanstalk (API)` split cannot be demoed. We need one public URL — the Beanstalk environment — serving both the Next.js UI and the FastAPI API, with no second live server and no behaviour regression.

---

## 2. User story

As a **demo viewer**, I want **to open the EB URL and use the full app (login, dashboard, charts, news, admin)**, so that **the live demo works without CloudFront/S3-website**.

---

## 3. Scope

### In scope

- FastAPI serves prebuilt Next.js static export (`frontend/out/`) from the same EB process (single `uvicorn`, `Procfile` unchanged in shape).
- Same-origin API: frontend built with relative/same-origin API base; `GET /health` stays the EB healthcheck.
- SPA fallback for static-export routes (`/`, `/portfolio/`, `/asset/`, `/auth/callback/`, etc.) without shadowing `/api/*`, `/health`, `/docs`, `/openapi.json`.
- Packaging script: `frontend build → copy out/ → zip EB bundle` (excludes `.venv`, `node_modules`).
- Cognito callback/logout URLs updated for EB origin (CloudFormation params + runbook).
- Arch/PRD variance note (CloudFront omitted in lab; S3 still used for data/history/snapshots).

### Out of scope

- Running `next start` (Node SSR server) alongside FastAPI on EB — explicitly rejected.
- S3-website / CloudFront distribution work.
- Changing auth mode, data model, market/FX logic, or API contracts.
- Multi-env blue/green, CDN caching, custom domain + ACM.

---

## 4. Behaviour

### Happy path

1. Eng runs package script → `frontend/out/` copied to `backend/static_web/` (or `backend/app/static_web/`) → EB zip uploaded.
2. Viewer opens `https://<eb-env>.elasticbeanstalk.com/` → `index.html` (redirect to `/markets/stock/` per `app/page.tsx`).
3. App calls same-origin `/api/*` (no CORS failure); login via Cognito Hosted UI returns to `https://<eb-env>.../auth/callback/`.
4. Refresh on any deep link (`/portfolio/`, `/asset/?type=…`) still renders (SPA/file fallback).
5. `/health` returns `{"status":"ok"}` for EB health checks.

### Edge cases / errors

- `static_web/` missing (e.g. unit-test checkout, API-only deploy): API still works; `/` returns JSON `{"detail":"frontend not bundled"}` or 404 with clear message — never 500.
- Unknown non-API path: SPA fallback to `index.html` where it exists, else 404 — never hijacks `/api/*`.
- `NEXT_PUBLIC_*` baked at build time: stale `NEXT_PUBLIC_API_URL` pointing at `127.0.0.1:8000` must not ship; build must use same-origin.
- Cognito redirect mismatch (old localhost/placeholder URLs): login fails at Cognito with redirect error — runbook covers updating UserPoolClient callback/logout URLs first.

### UX notes

- Screens / routes: all existing routes unchanged; no new UI except optional build-stamp footer (out of scope by default).
- Empty / loading / error states: unchanged (frontend behaviour identical).

---

## 5. Acceptance criteria

- [ ] **AC1** `GET /` on EB (or local `SERVE_FRONTEND=true` run) returns the built frontend HTML (contains app root/marker), not an API 404.
- [ ] **AC2** Deep link `GET /portfolio/` (and `/auth/callback/`) returns HTML fallback (200), while `GET /api/portfolio` without token still returns 401 JSON (not HTML).
- [ ] **AC3** Static assets `GET /_next/static/...` served with correct content-type; `GET /health` still `{"status":"ok"}`.
- [ ] **AC4** Frontend production build uses same-origin API (no hard-coded `127.0.0.1:8000` in shipped bundle path); browser network tab shows `/api/*` on EB origin.
- [ ] **AC5** Cognito login round-trip works from EB origin (callback + logout URLs registered; `NEXT_PUBLIC_APP_URL` = EB origin or `window.location.origin` fallback).
- [ ] **AC6** EB bundle contains `static_web/` + backend, excludes `.venv`/`node_modules`/`frontend/.next`; single-process `Procfile` (`uvicorn app.main:app`).
- [ ] **AC7** Focused + full gates pass: backend pytest, frontend lint/unit/build, Playwright same-origin smoke, `verify.ps1 -Profile full`.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | No data change; DynamoDB + S3-data (history/snapshots) unchanged |
| New / changed APIs | None (only new `GET /` + static + fallback; existing `/api/*`, `/health`, `/health/ready` unchanged) |
| Auth required? | UI routes public (static); `/api/*` keeps Cognito JWT; Cognito UserPoolClient URLs gain EB origin |
| Caching / freshness | No change (PriceCache/FX logic untouched); EB serves static with default `StaticFiles` cache headers |
| Jobs / schedules | None (Lambda/EventBridge untouched) |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `frontend/next.config.ts` (always `output:"export"`), `frontend/lib/api.ts` (`apiBase` same-origin), `frontend/.env*` build args, packaging copy from `frontend/out/` |
| Backend API | `backend/app/main.py` (mount static + fallback), `backend/app/core/config.py` (`SERVE_FRONTEND`, `FRONTEND_DIR`), `backend/app/api/health.py` (unchanged, must stay JSON) |
| Domain / services | None |
| Adapters | None (no `boto3`/`httpx` outside adapters — static serve uses `starlette.staticfiles` in API layer only) |
| Infra / jobs | `backend/Procfile` (keep single web), `backend/.ebextensions/*` (healthcheck stays `/health`), `infra/cloudformation-lab.yml` (Cognito callback/logout params), new `scripts/package-eb.*` |
| Docs / tests | Arch variance note, EB deploy runbook, backend static-mount tests, frontend `apiBase` test, Playwright same-origin smoke |

---

## 8. Dependencies & risks

- Depends on: static export staying green (`npm run build` → `frontend/out/`); EB Python platform serves single process.
- Risks / unknowns:
  - `NEXT_PUBLIC_*` bake-time staleness → mitigate with package script forcing `NEXT_PUBLIC_API_URL=""` (same-origin) + CI grep guard.
  - Route shadowing (`/` fallback eating `/api/*`) → mitigate with mount order + tests.
  - Bundle bloat / stale `out/` → script always rebuilds + cleans target dir.
  - Marks narrative: CloudFront/S3-website evidence gone → keep S3-data + Athena story, document lab constraint explicitly.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Single-process static vs dual `next start` on EB? | resolved | Single-process static (this BL); dual-server rejected — violates arch "no both live servers on one Beanstalk", needs Node, more RAM |
| 2 | Serve dir `backend/static_web/` vs `backend/app/static_web/`? | open | Decide in SA design (prefer top-level `backend/static_web/` out of import path) |
| 3 | Keep S3 frontend bucket for later? | resolved | Keep code/build compatible with S3 (export stays), just don't require it for lab demo |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-09-04 | Lab blocks CloudFront — can EB serve both? | Allocated BL-031, single-process static scope |
| 2026-09-04 | Baseline `verify.ps1 -Profile quick` | backend 554 pass/5 skip, frontend 411 pass, lint pass; `ports-isolation` gate fails on missing `rg` binary (env, not code) |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach: single-process static serving per SA design D1–D7. `Settings`
  gains `SERVE_FRONTEND` (default true) + `FRONTEND_DIR` (default
  `static_web`) with `resolve_frontend_dir()` preferring top-level
  `backend/static_web/` over legacy `backend/app/static_web/`
  (`backend/app/core/config.py`). `backend/app/main.py` mounts `/_next`
  via `StaticFiles`, explicit `GET /`, and a guarded catch-all
  `GET /{full_path:path}` that excludes `api/health/docs/openapi.json/redoc`,
  serves exact files + trailing-slash `index.html` dirs, else SPA fallback;
  missing/empty bundle (or `SERVE_FRONTEND=false`) degrades to API-only
  (`/` → JSON 404, warning log). `apiBase()` fixed so `""` means same-origin
  (`frontend/lib/api.ts`); `next.config.ts` always `output:"export"`.
  Packaging via `scripts/package-eb.ps1`/`.sh` (build with
  `NEXT_PUBLIC_API_URL=""`, leak-guard on `127.0.0.1:8000/api`, allow-list
  zip). Cognito params gain `EB_PLACEHOLDER` entries
  (`infra/cloudformation-lab.yml`); deploy order + rollback in
  `docs/runbooks/eb-single-hosting.md`; arch variance note in
  `docs/architecture-design.md` §3.2.
- Deviations: settings coverage added to `backend/tests/unit/test_settings.py`
  (SA named a non-existent `tests/unit/core/test_config.py`); leak guard
  fails on `127.0.0.1:8000/api` rather than any `127.0.0.1:8000` because the
  inert `DEFAULT_API` fallback literal ships in the bundle by design.
- PR / branch: `feat/BL-031-single-eb-hosting` (worktree `../a3-wt-bl031`).
- Verification: `tests/unit/api/test_static_hosting.py` (9 tests) +
  `test_settings.py` frontend-settings block green; `lib/api.test.ts` 16/16
  green; full backend pytest + `npm run lint/test/build` + Playwright smoke
  evidence in `docs/orchestration/walkthroughs/BL-031-walkthrough.md`.
