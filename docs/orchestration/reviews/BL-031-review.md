# SA Review — BL-031: Single-EB hosting (static frontend from Beanstalk API)

| Field | Value |
|-------|-------|
| **ID** | `BL-031` |
| **Reviewer (SA)** | Solution Architect (SA Reviewer) |
| **Date** | 2026-09-04 |
| **Branch / worktree** | `feat/BL-031-single-eb-hosting` / `D:\rmit\cloud\a3-wt-bl031` |
| **Walkthrough** | `docs/orchestration/walkthroughs/BL-031-walkthrough.md` |
| **Verdict** | `approve` |

Verdict: approve

---

## 1. AC verification

| AC | Satisfied? | Evidence (file:line or test) | Note |
|----|------------|------------------------------|------|
| AC1 — `GET /` returns built HTML | yes | `backend/tests/unit/api/test_static_hosting.py:67-71`; `backend/app/main.py:124-128`; reviewer probe `/` → 200 `text/html` | Served from `FRONTEND_DIR/index.html`; API-only fallback is JSON 404, never 500 |
| AC2 — deep links fallback HTML; `/api/*` stays 401 JSON | yes | `test_static_hosting.py:74-79` (`/portfolio`, `/portfolio/`, `/auth/callback`, `/auth/callback/`), `:96-102` (401 JSON), `:105-110` (unknown-API JSON 404); `main.py:46-49,109-118`; probe `/portfolio/`, `/auth/callback/` → 200 HTML, `/api/portfolio` → 401 JSON | Denylist is case-insensitive; `/API/portfolio`, `/HEALTH` probed → JSON 404, never HTML |
| AC3 — `/_next/static/*` MIME; `/health` JSON | yes | `test_static_hosting.py:82-86` (JS MIME via `StaticFiles`), `:89-93` (`/health` == `{"status":"ok"}`); `main.py:98-105`; `backend/app/api/health.py:15-17` untouched; probe `/health`, `/health/ready` → 200 JSON | `02_health.config` unchanged, healthcheck stays `/health` |
| AC4 — prod bundle same-origin, no `127.0.0.1:8000` leak | yes | `frontend/lib/api.ts:10-18`; `frontend/lib/api.test.ts:136-184` (6 tests: `""`→`""`, ws→`""`, unset→default, trim, absolute, relative `/api/*` URL); `scripts/package-eb.ps1:40-51,65-73`; `scripts/package-eb.sh:34-58`; `frontend/next.config.ts:11` always-export | Old `"" \|\| DEFAULT` bug fixed; leak guard targets `127.0.0.1:8000/api` (deviation justified, §4) |
| AC5 — Cognito round-trip from EB origin | pass* | `infra/cloudformation-lab.yml:13-26` (localhost + CloudFront entries byte-identical, `EB_PLACEHOLDER` appended); `docs/runbooks/eb-single-hosting.md:33-53` (Cognito-first order, trailing-slash requirement) | *Config-level only: live Hosted-UI login needs a real EB deploy, which is forbidden in this review (no AWS mutation). Residual risk logged for orchestrator. No auth code changed (`git diff` shows zero changes under `services/`, `adapters/`, `api/`, `lib/cognito.ts`, `lib/auth.ts`). |
| AC6 — EB bundle has `static_web/`, excludes junk, single process | yes | `scripts/package-eb.ps1:76-83` (clean+copy, asserts `index.html` + `_next/`), `:85-107` (allow-list `app/ Procfile requirements.txt .ebextensions/ static_web/`), `:114-133` (contents check: required entries, excluded-path scan, `_next` assets); `.sh:61-113` twin; `backend/.ebignore:1-11` (`static_web/` deliberately not ignored); `backend/Procfile:1` unmodified single `uvicorn` | Implementor ran the `.ps1` end-to-end: 270 entries, `contents OK`, 1.11 MB; artifacts cleaned, not committed. `.sh` logic-reviewed only (noted, acceptable). |
| AC7 — focused + full gates | pass* | Focused: `test_static_hosting.py` 10/10, `lib/api.test.ts` 16/16, settings 5/5 (all re-run by reviewer). Full backend `pytest`: **569 passed, 5 skipped**. Playwright smoke correctly gated (`single-eb-smoke.spec.ts:16,23`). | *`verify.ps1 -Profile full` (lint/build/full e2e) is the orchestrator's step per walkthrough handoff; implementor evidence cites lint clean, 417 frontend tests, build export OK, live smoke 4/4 on :8123. |

---

## 2. Architecture checks

- [x] Ports isolation (`boto3`/`httpx`/`requests` only in `adapters/`)? Reviewed `backend/app/main.py:1-34` — imports are only `fastapi`, `fastapi.middleware`, `fastapi.responses`, `fastapi.staticfiles`, `starlette.types` + stdlib `logging`/`pathlib`. `config.py:1-13` adds only stdlib `pathlib` (+ existing pydantic). `Select-String` scan of all `backend/app/**/*.py` outside `adapters/` for `boto3|botocore|httpx|requests` imports → **no matches**. Static serving uses `starlette.staticfiles` in the API composition layer only, as the SA design allowed.
- [x] Locked decisions intact? No API Gateway added; no SSR/server actions/route handlers/middleware (`api.ts`, `next.config.ts` diff only; SSR grep → no matches); no browser-direct market APIs (`api.ts` calls `/api/*` only, provider grep → no matches); cache-first pricing, on-demand FX, Cognito JWT verify untouched (diff touches none of `services/`, `domain/`, `ports/`, `adapters/`, `jobs/`, `api/`); single-process `Procfile` shape unchanged; healthcheck `/health` unchanged.
- [x] Cost/budget impact ≤$50 narrative respected? Single `t3.micro` process, no new AWS resources, no new tables/buckets/cron. Arch variance note (`docs/architecture-design.md:248-255`) keeps the S3-data + Athena story and cites the lab constraint. Accurate.
- [x] Security (no secrets in frontend/Git, no presigned leak)? No secrets added; `EXCHANGE_RATE_API_KEY` stays server-side per runbook (`eb-single-hosting.md:26`); CFN defaults use `EB_PLACEHOLDER`, never a real URL; `_safe_join` (`main.py:52-59`) resolves + `relative_to` checks traversal (probed `/%2e%2e` → SPA HTML, no file disclosure); non-GET methods delegate to the original default (probed POST `/portfolio/` → 404 JSON, POST `/api/auth/me` → 405 JSON).

## 3. Code quality

- [x] Tests green + meaningful (not `assert True`)? 10 static-hosting tests assert status + content-type + body markers across bundled/API-only/`SERVE_FRONTEND=false` modes plus late-route precedence; 6 `apiBase` tests cover `""`/whitespace/unset/trim/absolute/relative-URL; 5 settings tests cover defaults/env/absolute/resolution/bundle-present. All re-run green by reviewer.
- [x] File ownership respected? Modified: `backend/app/main.py`, `backend/app/core/config.py`, `backend/tests/unit/test_settings.py`, `frontend/lib/api.ts`, `frontend/lib/api.test.ts`, `frontend/next.config.ts`, `infra/cloudformation-lab.yml`, `docs/architecture-design.md` — all in the SA allowed list. New: `test_static_hosting.py`, `single-eb-smoke.spec.ts`, `package-eb.ps1/.sh`, `.ebignore`, runbook — all allowed. Nothing touched in `services/`, `domain/`, `ports/`, `adapters/`, `jobs/`, `api/`, `Procfile`, `.ebextensions`.
- [x] Error model `{detail: ...}` + correct HTTP codes? API-only `/` → 404 `{"detail":"frontend not bundled"}`; excluded unknown API paths → 404 `{"detail":"Not Found"}`; unauthenticated API → 401 JSON; `/health` → 200 JSON. No HTML ever leaks on API/health/docs paths (probed `/api/`, `/health/ready`, `/openapi.json`, `/docs`, `/redoc` — all correct types).
- [x] Cleanliness? Mount order correct (`_mount_frontend` last, `main.py:184`, after all routers); denylist `{"api","health","docs","openapi.json","redoc"}` complete incl. trailing-slash edge (`/api/` → first segment `api` → excluded, probed) and case-insensitive; `FRONTEND_DIR` resolution prefers top-level `backend/static_web/`, falls back to legacy `backend/app/static_web/`, absolute passthrough (`config.py:72-97`); API-only path logs a warning (observed in probe output); `.ebignore` does not ignore `static_web/`; Cognito localhost entries preserved.

## 4. Issues (none blocking)

| # | Severity | File:line | Issue | Required fix |
|---|----------|-----------|-------|--------------|
| 1 | minor | `backend/app/core/config.py:86-90` | Legacy-fallback branch (`top-level` missing + `app/static_web/` exists) has no test — `test_resolve_frontend_dir_prefers_top_level_over_legacy` only asserts the default path | Optional: add one `tmp_path`-based test with monkeypatched `_BACKEND_ROOT`, or accept as-is (fallback is defensive compat). Not a merge blocker. |
| 2 | minor | `scripts/package-eb.ps1:98-106` vs `scripts/package-eb.sh:80-93` | Twin asymmetry: `.ps1` strips `__pycache__/*.pyc` under staged `app/` and root `.pytest_cache`; `.sh` excludes `__pycache__/.pytest_cache/node_modules/.next/*.pyc` anywhere. Both are safe (allow-list construction excludes `.venv`/`node_modules` by design); inert-literal metric also differs (occurrences vs files) — informational only | Optional harmonization. Not a blocker; `.ps1` is the exercised path. |
| 3 | minor | `docs/architecture-design.md:247` (pre-existing) | `CORS: FastAPI allows CloudFront origin only` was already stale before BL-031 (defaults are localhost dev origins; same-origin needs no CORS change per D7) | Optional one-line touch-up outside BL-031 scope. Not required. |

No `request_changes` items. Deviations in the walkthrough (§3) are all accepted:

1. `router.default` no-match override instead of `GET /{full_path:path}` — **justified and superior**: a path route shadows routes registered after `create_app()` (broke 3 existing `test_auth.py` tests); `router.default` fires only on true no-match. Covered by `test_late_registered_routes_keep_precedence_over_fallback` (`test_static_hosting.py:145-155`). Observable AC behaviour identical, plus unknown `/api/*` stays JSON 404.
2. Settings tests in `backend/tests/unit/test_settings.py:254-304` instead of non-existent `tests/unit/core/test_config.py` — **correct**, that directory does not exist.
3. Leak guard fails on `127.0.0.1:8000/api` rather than bare `127.0.0.1:8000` — **justified**: the inert `DEFAULT_API` fallback literal ships by design (dead branch when built with `NEXT_PUBLIC_API_URL=""`); a bare-literal grep would fail every build.

## 5. Decision

- **Approve:** Orchestrator may merge branch `feat/BL-031-single-eb-hosting` → `integration/*` or `main` per the release plan, then mark backlog `done`.
- Required before `done` (orchestrator-owned, cannot be done in this review): run `.workflows/verify.ps1 -Profile full`; on a `SERVE_FRONTEND=true` backend serving a real `frontend/out` build, run the live smoke (`SINGLE_EB_SMOKE=1`, `single-eb-smoke.spec.ts`) and exercise Cognito login/logout from the EB origin (AC5 live leg).

## 6. Notes for Orchestrator

- Commands run by reviewer (workdir `D:\rmit\cloud\a3-wt-bl031`, read-only use of `D:\rmit\cloud\a3\backend\.venv` interpreter binary, nothing written outside the worktree):
  - `pytest backend/tests/unit/api/test_static_hosting.py -q` → **10 passed** (`PYTHONPATH=<worktree>/backend`, `OPENPORTFO_DISABLE_ENV_FILE=1`)
  - `npx vitest run lib/api.test.ts` (in `frontend/`) → **16 passed**
  - `pytest backend/tests -q` → **569 passed, 5 skipped** (baseline 554/5 + 15 new: 10 static + 5 settings)
  - `Select-String` ports-isolation scan outside `adapters/` → **no matches**
  - Live `TestClient` probes (temp bundle + missing-dir): `/`→200 HTML, `/portfolio/`+`/auth/callback/`→200 HTML, `/health`+`/health/ready`→200 JSON, `/api/`→404 JSON, `/api/portfolio`→401 JSON, unknown `/api/*`→404 JSON, `/docs`→200, `/openapi.json`→200, `/redoc`→200, `/API/portfolio`+`/HEALTH`→404 JSON, POST `/api/auth/me`→405 JSON, POST `/portfolio/`→404 JSON, traversal→SPA HTML (no disclosure)
- Residual risks: (a) live Cognito round-trip from a real EB origin unproven until deploy (expected; runbook order mitigates `redirect_mismatch`); (b) `package-eb.sh` logic-reviewed only, `.ps1` ran end-to-end; (c) pre-existing `ports-isolation` verify gate needs `rg` binary (env issue, unrelated — `Select-String` equivalent is clean).
- Worktree has uncommitted changes + untracked BL-031 files (implementation + docs); review doc written at `docs/orchestration/reviews/BL-031-review.md`. No commit/push/deploy/AWS mutation performed.
