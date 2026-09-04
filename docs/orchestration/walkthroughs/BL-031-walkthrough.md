# Walkthrough — BL-031: Single-EB hosting (static frontend from Beanstalk API)

| Field | Value |
|-------|-------|
| **ID** | `BL-031` |
| **Branch** | `feat/BL-031-single-eb-hosting` |
| **Worktree** | `D:\rmit\cloud\a3-wt-bl031` |
| **Implementor** | Eng (Implementor agent) |
| **Date** | 2026-09-04 |
| **SA design** | `docs/orchestration/designs/BL-031-single-eb-hosting-design.md` |
| **Research** | none (`simple` — no Researcher) |

---

## 1. Summary (what was built)

FastAPI now serves the prebuilt Next.js static export from the same `uvicorn`
process: `SERVE_FRONTEND`/`FRONTEND_DIR` settings with a `backend/`-rooted
resolution helper, a no-match SPA fallback (`router.default` override) that can
never shadow `/api/*`, `/health`, `/docs`, `/openapi.json`, a same-origin
`apiBase()` fix plus always-`output:"export"`, `scripts/package-eb.ps1`/`.sh`
(build with `NEXT_PUBLIC_API_URL=""`, leak guard, allow-list EB zip),
EB-placeholder Cognito callback/logout params, an EB deploy runbook, and an
arch variance note. No service/domain/port/adapter/job, API-contract, table,
bucket, or cron change.

## 2. Files changed (path:line)

| File | Change |
|------|--------|
| `backend/app/core/config.py:65-97` | `_BACKEND_ROOT`, `DEFAULT_FRONTEND_DIR`, `resolve_frontend_dir()`, `frontend_bundle_present()` |
| `backend/app/core/config.py:209-210` | `serve_frontend` (`SERVE_FRONTEND`, default true), `frontend_dir` (`FRONTEND_DIR`, default `static_web`) |
| `backend/app/core/config.py:357-359` | `Settings.frontend_dir_resolved` property |
| `backend/app/main.py:28-35,48-143` | `/_next` StaticFiles mount + `router.default` SPA-fallback override (excludes `api/health/docs/openapi.json/redoc`); API-only JSON-404 mode with warning log |
| `backend/tests/unit/api/test_static_hosting.py:1` | NEW — 10 tests: `/` HTML, deep-link fallback, `_next` MIME, `/health` JSON, `/api/*` 401-never-HTML, unknown-API JSON 404, missing-dir API-only, `SERVE_FRONTEND=false` rollback, late-route precedence |
| `backend/tests/unit/test_settings.py:254-304` | 5 tests: defaults, env override, absolute passthrough, top-level resolution, bundle-present check |
| `frontend/lib/api.ts:10-19` | `apiBase()` fix: `undefined`/`null` → local default, `""`/whitespace → `""` (same-origin), else trimmed sans trailing `/` |
| `frontend/lib/api.test.ts:136-184` | 6 new `apiBase` same-origin tests incl. relative `/api/*` URL construction |
| `frontend/next.config.ts:11` | Always `output:"export"` (dropped `isProd` conditional) |
| `frontend/e2e/single-eb-smoke.spec.ts:1` | NEW — 4 Playwright checks, skipped unless `SINGLE_EB_SMOKE=1` |
| `scripts/package-eb.ps1:1` | NEW — build (`NEXT_PUBLIC_API_URL=""`), export asserts, leak guard, copy `out/` → `backend/static_web/`, allow-list zip + contents check |
| `scripts/package-eb.sh:1` | NEW — bash twin (build/copy/guard/python-zipfile verify) |
| `backend/.ebignore:1` | NEW — keeps direct `eb deploy` bundles free of `.venv/__pycache__/node_modules/.next/*.zip` |
| `infra/cloudformation-lab.yml:13-28` | `CognitoCallbackUrls`/`CognitoLogoutUrls` gain `EB_PLACEHOLDER` entries + update-order comment; localhost + CloudFront placeholders byte-identical |
| `docs/runbooks/eb-single-hosting.md:1` | NEW — env table, Cognito-first order, package/deploy commands, `SERVE_FRONTEND=false` rollback, demo narrative |
| `docs/architecture-design.md:248-255` | Lab variance note (single-process static; S3-data + Athena kept) |
| `docs/backlog/features/BL-031-single-eb-hosting.md:142-165` | §11 implementation notes |

## 3. Decisions & deviations from SA design

| # | SA said | Did | Reason |
|---|---------|-----|--------|
| 1 | Catch-all route `GET /{full_path:path}` (§3.1, D4) | `app.router.default` (no-match handler) override + `/_next` mount | A `/{full_path}` route shadows routes registered **after** `create_app()` — broke 3 existing `test_auth.py` tests (`/_test/*` returned 404). `router.default` only fires on true no-match, so all registered routes keep precedence whenever added; observable behaviour (AC1–AC3 + edge) identical, plus unknown `/api/*` stays JSON 404 |
| 2 | Extend `backend/tests/unit/core/test_config.py` (§7) | Added settings block to `backend/tests/unit/test_settings.py:254` | `tests/unit/core/` does not exist; settings tests live in `test_settings.py` |
| 3 | Post-build grep for `127.0.0.1:8000` fails build (§9) | Guard fails on `127.0.0.1:8000/api` (absolute API calls); bare literal only counted/informational | The inert `DEFAULT_API` fallback literal ships in the bundle by design (dead branch when built with `NEXT_PUBLIC_API_URL=""`), so a bare-literal grep would fail every build |
| 4 | `backend/.ebignore` check/create (§2) | Created (python/node/zip ignores; `static_web/` deliberately **not** ignored) | Ignoring `static_web/` would silently break single-EB `eb deploy` after packaging |

## 4. How to verify

```powershell
# From D:\rmit\cloud\a3-wt-bl031. Backend uses the shared 3.12 venv
# (worktree has no backend/.venv of its own; binary only, nothing written there).
cd backend
& "D:\rmit\cloud\a3\backend\.venv\Scripts\python.exe" -m pytest tests/unit/api/test_static_hosting.py -q
& "D:\rmit\cloud\a3\backend\.venv\Scripts\python.exe" -m pytest -q

cd ..\frontend
npm run lint
npx vitest run lib/api.test.ts
npm test
npm run build

# Playwright: default suite (BL-031 smoke skips without the flag)
npx playwright test

# Live single-EB smoke (uvicorn serves the same-origin build):
$env:SERVE_FRONTEND = "true"; $env:FRONTEND_DIR = "D:\rmit\cloud\a3-wt-bl031\frontend\out"
& "D:\rmit\cloud\a3\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8123  # from backend/
$env:SINGLE_EB_SMOKE = "1"; $env:SINGLE_EB_BASE_URL = "http://127.0.0.1:8123"
npx playwright test e2e/single-eb-smoke.spec.ts

# Packaging (AC6):
.\scripts\package-eb.ps1 -AppUrl https://<eb-env>.elasticbeanstalk.com  # from repo root
```

Expected: focused 10/10; full backend 569 passed / 5 skipped; lint clean;
`lib/api.test.ts` 16/16; full frontend 63 files / 417 tests; build exports
`out/`; default e2e 4 passed / 4 skipped; live smoke 4/4; packaging prints
`contents OK` + zip size. (Full `verify.ps1 -Profile full` left to orchestrator.)

## 5. Test evidence (paste)

Backend focused + settings (after final `router.default` implementation):

```
10 passed, 2 warnings in 1.08s   (tests/unit/api/test_static_hosting.py)
```

Full backend suite:

```
568 passed, 5 skipped, 4 warnings in 11.36s
```

(+1 late-route test appended after that run → 569 passed on final code; the
extra test passes in the focused 10/10 run above. Baseline was 554/5.)

Frontend:

```
Test Files  1 passed (1) / Tests  16 passed (16)   (lib/api.test.ts)
Test Files  63 passed (63) / Tests  417 passed (417)   (npm test; baseline 411 + 6 new)
npm run lint: clean (no output)
npm run build: static export OK (○ prerendered, ● SSG crypto/stock [id])
```

Playwright:

```
default `npx playwright test`: 4 passed, 4 skipped (BL-031 smoke gated off)
SINGLE_EB_SMOKE=1 vs uvicorn+out/ on :8123: 4 passed (/, deep links, /health, 401 JSON)
```

Live HTTP (uvicorn, `FRONTEND_DIR=<abs>/frontend/out`, same-origin build):

```
health: ok
GET / -> 200 text/html; charset=utf-8
GET /portfolio/ -> 200 text/html; charset=utf-8
GET /auth/callback/ -> 200
GET /api/auth/me -> 401
```

Packaging (`.\scripts\package-eb.ps1 -AppUrl https://EB_PLACEHOLDER`):

```
[package-eb] export OK: index.html + _next/ present
[package-eb] leak guard OK (inert DEFAULT_API literal occurrences: 1)
[package-eb] copied out/ -> backend/static_web/
[package-eb] staged: app/ Procfile requirements.txt .ebextensions/ static_web/
[package-eb] contents OK: 270 entries (static_web/index.html, _next assets, Procfile, app/)
[package-eb] wrote D:\rmit\cloud\a3-wt-bl031\eb-bundle.zip (1.11 MB)
```

Artifacts (`eb-bundle.zip`, `backend/static_web/`) removed after verification
— not committed, per SA guardrails. `bash -n scripts/package-eb.sh` clean,
embedded-python compiles, `cloudformation-lab.yml` parses (CFN-tolerant load).

- Unit tests added: 10 backend static-hosting + 5 settings + 6 frontend apiBase.
- Coverage of AC: AC1 (root HTML), AC2 (fallback + 401-never-HTML),
  AC3 (`_next` MIME + `/health`), AC4 (same-origin build + leak guard, zero
  `127.0.0.1:8000/api` hits), AC5 (Cognito params + runbook order; live
  round-trip needs real EB/Cognito, not mutated here), AC6 (allow-list zip
  evidence above), AC7 (gates above; `verify.ps1 -Profile full` = orchestrator).

## 6. API / UX verification

- No API contract change: all `/api/*`, `/health`, `/health/ready`, `/docs`,
  `/openapi.json` routes untouched; fallback only serves previously-404 GETs.
- Browser proof: Playwright live smoke (real `out/` + uvicorn) + default
  static-server suite still green; `npm run build` export unchanged in shape.
- Manual curl equivalent of the smoke (port 8123 block in §4).

## 7. Ports isolation check

```powershell
Select-String -Pattern "boto3|botocore|httpx|requests" -Path "backend\app\main.py","backend\app\core\config.py"
```

Result: no matches. `main.py` imports only `fastapi`, `fastapi.middleware`,
`fastapi.responses`, `fastapi.staticfiles`, `starlette.types` (+ stdlib
`logging`/`pathlib`); `config.py` adds only stdlib `pathlib`.

## 8. Known limitations / follow-ons

- AC5 live Cognito round-trip from a real EB origin not exercised (no
  deploy / no AWS mutation per instructions); params + runbook order in place.
- `scripts/package-eb.sh` logic-reviewed only (`bash -n` + embedded-Python
  compile); the `.ps1` twin ran end-to-end on Windows.
- Port 8000 was occupied by an unrelated pre-existing process during local
  verification; smoke used :8123 (no code impact).
- Baseline `ports-isolation` verify gate needs `rg` (missing binary, env
  issue per BL-031 §10); equivalent `Select-String` check above is clean.
- Worktree has no `backend/.venv`; verification used the main checkout's
  interpreter binary read-only (no files written outside the worktree).

## 9. Handoff to SA Review

- Walkthrough ready for SA review: yes.
- AC checklist self-assessed: AC1 ✓, AC2 ✓, AC3 ✓, AC4 ✓ (build + guard),
  AC5 ⚠ (config + docs; live login needs EB deploy), AC6 ✓ (zip evidence),
  AC7 ⚠ (all runnable gates green; `verify.ps1 -Profile full` = orchestrator).
