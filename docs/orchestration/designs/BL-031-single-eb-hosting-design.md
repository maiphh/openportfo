# SA Design — BL-031: Single-EB hosting (static frontend from Beanstalk API)

| Field | Value |
|-------|-------|
| **ID** | `BL-031` |
| **Title** | Serve Next.js static export from the same EB instance (no CloudFront) |
| **Status** | `ready_for_implementation` |
| **Author (SA)** | Solution Architect (Muse Spark) |
| **Date** | 2026-09-04 |
| **Complexity** | `simple` (no Researcher — single well-known FastAPI StaticFiles pattern, no new lib choice) |
| **Related PRD** | `docs/prd/OpenPortfo_PRD.md#8.11` (Next static CSR, S3+CloudFront), `#12` (locked stack), `#15.2` (env config), `#16` (live deploy) |
| **Related Arch** | `docs/architecture-design.md#3` (hosting map), `#12` (locked stack: `Not used: Next + FastAPI both as live servers on one Beanstalk`) |
| **Feature file** | `docs/backlog/features/BL-031-single-eb-hosting.md` |

---

## 1. Context & constraints

- Problem / user value (1 paragraph, from feature file): Academy lab blocks CloudFront, so the `S3+CloudFront UI + Beanstalk API` split cannot be demoed. One public URL (the EB environment) must serve both the Next.js UI and the FastAPI API with a single Python process and no behaviour regression.
- Locked stack constraints (with variance):
  - No API Gateway for user APIs (Beanstalk FastAPI only) — kept.
  - No Next.js SSR — kept. `frontend/next.config.ts:9-12` already `output:"export"` (prod) + `images.unoptimized` + `trailingSlash:true`; dynamic `[id]` routes have seeded `generateStaticParams` (`frontend/app/crypto/[id]/page.tsx:5`, `frontend/app/stock/[id]/page.tsx:5`); canonical links use static `/asset?type=&id=` entry. No `middleware.ts`, no route handlers. `frontend/out/index.html` builds today.
  - No browser-direct market APIs — kept (`frontend/lib/api.ts:54-80` calls FastAPI only).
  - Cache-first pricing, on-demand FX only — untouched.
  - Cognito JWT via JWKS — kept; only callback/logout origins change.
  - Thin wrappers: no `boto3`/`httpx` outside `adapters/` — kept; static serving uses `starlette.staticfiles` (ships with FastAPI) in the API composition layer only (`backend/app/main.py`), not domain/services.
  - **Variance:** hosting target changes from `S3+CloudFront` to `EB static` for lab. This deliberately bends Arch §3/`frontend/AGENTS.md` S3+CloudFront line. Single static-serving process does **not** violate the "no both live servers on one Beanstalk" ban (that bans `next start` + `uvicorn` dual processes). Record variance in arch + demo narrative; S3 remains in rubric via data bucket (history/snapshots) + Athena.

## 2. Affected surfaces

| Layer | Paths / components | Change type |
|-------|--------------------|-------------|
| Frontend | `frontend/next.config.ts:9-12` | **modify** — always `output:"export"` (drop `isProd` conditional) so EB bundle is deterministic |
| Frontend | `frontend/lib/api.ts:6-13` (`apiBase`) + `frontend/lib/auth.ts` (uses `apiBase`) | **modify** — same-origin when `NEXT_PUBLIC_API_URL` empty; fix `"" \|\| DEFAULT` bug (empty must mean relative, not fallback) |
| Frontend | `frontend/lib/cognito.ts:95-104` (`readCognitoConfig` falls back to `window.location.origin`) | **no change** (already EB-safe); build sets `NEXT_PUBLIC_APP_URL` to EB origin or leaves empty |
| Frontend | `frontend/out/` → packaged copy | **build artifact** — never hand-edited |
| Backend API | `backend/app/main.py:26-60` | **modify** — mount static + SPA fallback after all `/api/*` routers |
| Backend API | `backend/app/core/config.py:117-166` | **modify** — add `SERVE_FRONTEND: bool=true`, `FRONTEND_DIR: str="static_web"` (+ EB env override) |
| Backend API | `backend/app/api/health.py:15-17` (`GET /health`) | **no change** — must stay JSON; regression test guards it |
| Domain / services | `backend/app/services/*`, `domain/*` | **none** |
| Ports | `backend/app/ports/*` | **none** |
| Adapters | `backend/app/adapters/*` | **none** |
| Infra / jobs | `backend/Procfile:1` | **no shape change** — stays single `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Infra | `backend/.ebextensions/01_python.config`, `02_health.config` | **no change** (healthcheck stays `/health`) |
| Infra | `infra/cloudformation-lab.yml:13-19` (`CognitoCallbackUrls`, `CognitoLogoutUrls` still `localhost` + `placeholder.cloudfront.net`) | **modify** — add EB-origin param/defaults + document update step |
| Infra | `scripts/package-eb.ps1` + `scripts/package-eb.sh` (**NEW**), `backend/.ebignore` (check/create) | **new** — build FE, copy `out/`, zip EB bundle |
| Docs / tests | `docs/architecture-design.md`, EB runbook, backend/frontend/Playwright tests | **new/modify** (see §7) |

## 3. API & data model deltas

### 3.1 API

| Method & path | Auth | Request | Response | Notes |
|---------------|------|---------|----------|-------|
| `GET /` | none (static) | — | `index.html` (HTML) when bundled; else JSON `{"detail":"frontend not bundled"}` 404 | New. Must not break `/health`. |
| `GET /_next/static/*`, `/favicon.ico`, `/icon.svg`, trailing-slash dirs (`/portfolio/index.html`, …) | none | — | Static files with correct MIME | New via `StaticFiles(directory=FRONTEND_DIR, html=true)` or explicit mounts. |
| `GET /{spa_path}` (e.g. `/portfolio/`, `/asset/`, `/auth/callback/`) | none | — | `index.html` fallback (200) when bundled | New fallback. Exclude prefixes: `/api`, `/health`, `/docs`, `/openapi.json`, `/redoc`. |
| `GET /health`, `GET /health/ready`, all `/api/*`, `/docs`, `/openapi.json` | per existing | unchanged | unchanged JSON | **No change.** Mount order guarantees API wins. |
| Cognito Hosted UI | Cognito | `redirect_uri=https://<eb>/auth/callback/`, `logout_uri=https://<eb>/` | — | Config-only: register EB URLs in `UserPoolClient` before login works. |

### 3.2 Data model

```
No entity change.
DynamoDB: untouched (all tables per infra/cloudformation-lab.yml).
S3 layout: untouched (snapshots/history). Frontend S3-website bucket not required for lab.
Schemas (app/api/*): untouched.
```

- Static dir resolution: `FRONTEND_DIR` absolute at startup = `<backend>/static_web` (preferred top-level, outside `app/` import path) with fallback `<backend>/app/static_web` for backwards compat if Eng prefers. Decision: **top-level `backend/static_web/`** — keeps import path clean, `.ebignore`-friendly, obvious in zip root. If missing/empty → API-only mode + warning log, `/` returns JSON 404 (AC edge).
- `SERVE_FRONTEND=false` env kill-switch forces API-only even when dir exists (useful for API-only diagnostics).

## 4. Sequence (happy path)

```
Build/pack:  Eng → frontend (npm run build, NEXT_PUBLIC_API_URL="", NEXT_PUBLIC_APP_URL=<eb>) → out/ → scripts/package-eb → backend/static_web/ → eb.zip → EB env
Runtime:     Browser → EB (single uvicorn)
```

ASCII sequence:

```
1. Deploy: package-eb.ps1 sets NEXT_PUBLIC_API_URL="" + NEXT_PUBLIC_APP_URL=https://<eb-env>.elasticbeanstalk.com
2.         → npm run build → frontend/out/ → clean+copy → backend/static_web/ → zip (backend/* + static_web/*, excl .venv/node_modules/.next)
3. Browser GET https://<eb>/ → FastAPI static → static_web/index.html → redirect /markets/stock/ (app/page.tsx)
4. Browser GET https://<eb>/portfolio/ → fallback → index.html → CSR boots → fetch /api/portfolio (same-origin, Bearer Cognito ID token)
5. Browser login → https://<cognito>/oauth2/authorize?redirect_uri=https://<eb>/auth/callback/ → callback → token → GET /api/auth/me
6. EB healthcheck GET /health → {"status":"ok"} (never HTML)
```

## 5. Decisions (ADR style)

| # | Context | Decision | Consequence | Alternatives rejected |
|---|---------|----------|-------------|-----------------------|
| D1 | How to co-host on EB without Node? | Single-process: FastAPI serves prebuilt `out/` via `StaticFiles` + SPA fallback; `Procfile` unchanged shape | No Node on EB, minimal RAM, healthcheck trivial, ban on dual-servers respected | Dual `next start` + `uvicorn` (supervisord/Procfile multi-proc): needs Node on Python platform, 2× RAM on t3.micro, port/healthcheck complexity — rejected |
| D2 | `output:"export"` only in prod today | Always export (`output:"export"` unconditional) | EB bundle deterministic; dev `next dev` unaffected (dev server ignores export) | Keep conditional: risks packaging a non-export build if `NODE_ENV` leaks — rejected |
| D3 | `apiBase()` bug: `"" \|\| DEFAULT` turns intentional same-origin `""` into `127.0.0.1:8000` | Fix to nullish/explicit check: `undefined`/`null` → default; `""`/whitespace → `""` (relative); else trimmed URL sans trailing `/` | Shipped bundle calls `/api/*` on EB origin when built with `NEXT_PUBLIC_API_URL=""` | Absolute EB URL baked per-env: works but forces rebuild per env-swap and CORS config — keep as runbook option, not default |
| D4 | Route shadowing risk (`/` fallback vs `/api/*`, `/health`, `/docs`) | Mount API routers first; mount `/ _next`, `/favicon*`, static files; last catch-all `GET /{path}` excludes `api/health/docs/openapi.json/redoc` and returns `index.html` or 404 JSON | API/Docs/Health can never return HTML | `app.mount("/", StaticFiles(html=true))` alone: simplest but can shadow API depending on order — rejected as sole mechanism; use ordered mounts + explicit fallback handler |
| D5 | Missing `static_web/` (tests, API-only) | Fail open for API: log warning, `/` → JSON 404 `frontend not bundled`; all `/api/*` + `/health` work | Unit tests need no `out/` fixture; EB mis-pack surfaces clearly, not 500 | Hard-fail startup when dir missing: breaks `pytest` + API-only diagnostics — rejected |
| D6 | Cognito origins | Add EB origin to `CognitoCallbackUrls`/`CognitoLogoutUrls` params in `cloudformation-lab.yml`; runbook: update `UserPoolClient` + rebuild FE with `NEXT_PUBLIC_APP_URL=<eb>` (or rely on `window.location.origin` fallback) | Login works from EB without code change to `cognito.ts` | Bake localhost-only URLs: login breaks on EB — rejected |
| D7 | CORS | Keep `CORS_ORIGINS` for localhost dev; same-origin needs no CORS change; do not wildcard in prod | Zero-risk change | Tighten to EB-only: unnecessary churn, breaks local dev — rejected |

## 6. Complexity assessment

- [ ] Requires choosing between ≥2 libs/patterns → Researcher needed — **no** (D1 locks StaticFiles; no new dep)
- [ ] Security / auth / cost-critical AWS path — **partial** (Cognito redirect URLs = config, not new auth code; EB single-instance cost unchanged) — no Researcher
- [ ] No prior port/adapter pattern to reuse — **no** (composition in `main.py` only)
- [ ] Risk to locked decisions — **yes, hosting variance** but explicitly authorized by stakeholder + documented in §1; no SSR/API-GW/market-direct violation

**Verdict:** `simple`

**Research questions:** none.

## 7. Handoff to Implementor

### File ownership

- Allowed to edit:
  - `frontend/next.config.ts`, `frontend/lib/api.ts` (+ `frontend/lib/api.test.ts` or colocated test), `scripts/package-eb.ps1`, `scripts/package-eb.sh`
  - `backend/app/main.py`, `backend/app/core/config.py`, `backend/tests/unit/api/test_static_hosting.py` (**NEW**), `backend/tests/unit/core/test_config.py` (extend)
  - `infra/cloudformation-lab.yml` (Cognito URL params only), `docs/architecture-design.md` (variance note), new `docs/runbooks/eb-single-hosting.md` (**NEW**)
  - Playwright smoke `frontend/e2e/single-eb-smoke.spec.ts` (**NEW**, conditional on env flag)
- Must NOT edit (owned by other active work / out of scope):
  - `backend/app/services/*`, `domain/*`, `ports/*`, `adapters/*`, `jobs/*`
  - `backend/app/api/*` (except import in `main.py`), `backend/Procfile` shape, `.ebextensions` healthcheck path
  - Market/FX/Cognito verify logic, DynamoDB/S3 schemas

### TDD order

1. Test: `backend/tests/unit/api/test_static_hosting.py` — create `tmp_path/static_web/index.html` + fake asset; override `FRONTEND_DIR`/`SERVE_FRONTEND`; assert `/` HTML, `/portfolio/` fallback HTML, `/_next/static/x.js` MIME, `/health` JSON, `/api/*` never HTML, missing-dir → `/` JSON 404 + API still 401/OK.
2. Implement: `config.py` (`SERVE_FRONTEND`, `FRONTEND_DIR` resolution + top-level default) → `main.py` ordered mounts + fallback (API first, static second, catch-all last with prefix exclusions).
3. Test: `frontend/lib/api.test.ts` — `NEXT_PUBLIC_API_URL=""` → `apiBase()===""` and fetch URL starts `/api/`; unset → default `http://127.0.0.1:8000`; trailing-slash trim.
4. Implement: `lib/api.ts` fix per D3.
5. Implement: `next.config.ts` always-export + `scripts/package-eb.*` (build with `NEXT_PUBLIC_API_URL=""`, clean+copy `out/` → `backend/static_web/`, zip excluding `.venv/__pycache__/node_modules/.next/out` source, verify `index.html` + `_next/` present, print zip size).
6. Config/docs: `cloudformation-lab.yml` EB URL params; `docs/runbooks/eb-single-hosting.md` (env table, Cognito update, deploy commands, rollback to API-only via `SERVE_FRONTEND=false`); arch variance paragraph.
7. Verify: `npm run build` (FE) → `pytest` (BE) → `verify.ps1 -Profile full` → Playwright same-origin smoke against local `uvicorn` with `SERVE_FRONTEND=true`.

### Out-of-scope guardrails

- No `boto3`/`httpx`/`requests` outside `adapters/`; static serving imports only `fastapi.staticfiles` / `fastapi.responses` in `main.py`.
- No new tables, buckets, queues, or cron; no API contract change; no SSR/server actions/dynamic server routes.
- Do not commit `backend/static_web/` output or EB zips; do not commit real EB/Cognito URLs or secrets; never `push`/deploy/mutate real AWS without explicit user authorization per `AGENTS.md:10`.
- Stay on `feat/BL-031-*` worktree/branch for code (create via `scripts/worktree.ps1 -Id BL-031 -Slug single-eb-hosting -Base main` when implementation is authorized); docs-only plan stays on current branch.

## 8. Acceptance criteria checklist (copy from feature file)

- [ ] AC1 — `GET /` returns built HTML when bundled.
- [ ] AC2 — deep links fallback HTML; `/api/*` stays JSON (401 unauthenticated, never HTML).
- [ ] AC3 — `/_next/static/*` MIME correct; `/health` JSON intact.
- [ ] AC4 — prod bundle same-origin (`/api/*` on EB origin; no `127.0.0.1:8000` leak; grep guard in package script).
- [ ] AC5 — Cognito round-trip from EB origin (callback/logout registered; `NEXT_PUBLIC_APP_URL` = EB or origin fallback).
- [ ] AC6 — EB zip contains `static_web/` + backend, excludes `.venv`/`node_modules`; single `uvicorn` process.
- [ ] AC7 — `verify.ps1 -Profile full` + Playwright same-origin smoke green.

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| `NEXT_PUBLIC_*` baked stale (points at localhost) | Package script forces `NEXT_PUBLIC_API_URL=""` + `NEXT_PUBLIC_APP_URL=<EB>`; post-build grep for `127.0.0.1:8000` fails build; runbook rebuild-per-origin note |
| Fallback shadows `/api/*` or `/health` | Mount order (API → static → guarded catch-all with prefix denylist) + regression tests for JSON-vs-HTML content-type |
| `out/` stale or missing in zip | Script cleans target, rebuilds, asserts `index.html` + `_next/` exist; backend warns + API-only mode if absent |
| EB bundle too large / slow deploy | Exclude `.venv/node_modules/.next`; top-level `static_web/` only; print size; no source maps change |
| Cognito `redirect_mismatch` on first EB deploy | Update `UserPoolClient` callback/logout URLs before testing login; runbook order: Cognito → deploy → build-URL check → login |
| Marks story loses CloudFront/S3-website | Keep S3-data + Athena + Beanstalk + Lambda narrative; arch variance cites lab constraint; demo script calls out single-URL tradeoff |
| Baseline `ports-isolation` gate env failure (`rg` missing) | Pre-existing, unrelated to BL-031; use `Select-String` fallback locally; record separately from regressions |

## 10. Research linkage (if any)

- Research doc: none (`simple` — no Researcher).
- Baseline (2026-09-04, `verify.ps1 -Profile quick`): `workflow-contract` pass; `backend-tests` 554 pass/5 skip; `frontend-lint` pass; `frontend-unit` 63 files/411 tests pass; `ports-isolation` fail = missing `rg` binary in shell (env issue, not code).

---

**SA sign-off:** _ready_for_implementation_ when stakeholder approves this plan + authorizes `feat/BL-031-*` worktree for code.
