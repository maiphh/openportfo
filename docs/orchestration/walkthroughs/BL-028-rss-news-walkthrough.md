# Walkthrough — BL-028: RSS source news completion

| Field | Value |
|-------|-------|
| **ID** | `BL-028` |
| **Branch** | `feat/BL-028-rss-news` |
| **Worktree** | `D:\rmit\cloud\a3-wt-bl028` |
| **Implementor** | Implementor (Cursor) |
| **Date** | 2026-08-28 |
| **SA design** | `docs/orchestration/designs/BL-028-rss-news-design.md` |
| **Research** | _n/a_ (simple) |

---

## 1. Summary (what was built)

Completed admin RSS source management, news-job toggle / JobRuns panels on `/admin`, typed `RssFetchError` transport failures, shared `assert_public_http_url` validation for memory+Dynamo+redirects, bounded no-needle ingest (`MAX_ITEMS_PER_SOURCE=25`), and asset-symbol-only tagging on News rows — without Lambda/EventBridge (BL-029) or new API routes.

## 2. Files changed (path:line)

| File | Change | Lines |
|------|--------|-------|
| `backend/app/ports/rss.py:18` | Added `RssFetchError` | |
| `backend/app/adapters/rss/fetcher.py:73` | Shared `assert_public_http_url`; raise `RssFetchError` on transport/non-2xx/redirect/SSRF; fixed IPv4 `ipv4_mapped` AttributeError | |
| `backend/app/adapters/memory/admin.py:104` | Memory RSS URL validation via `assert_public_http_url` (parity with Dynamo) | |
| `backend/app/jobs/news_job.py:21` | `MAX_ITEMS_PER_SOURCE=25`; always fetch when news job on | |
| `backend/app/jobs/news_job.py:45` | Persist title-matched asset symbols only | |
| `backend/app/jobs/news_job.py:80` | Split asset symbols vs keyword needles | |
| `backend/tests/unit/adapters/test_rss_fetcher.py` | New fetcher TDD suite | |
| `backend/tests/unit/api/test_admin.py` | Unsafe URL rejection parity tests | |
| `backend/tests/unit/jobs/test_jobs.py` | Bounded ingest / symbols / dedupe / disabled source | |
| `frontend/lib/admin-api.ts` | RSS CRUD + job-runs clients; 204 DELETE | |
| `frontend/lib/admin-api.test.ts` | New client unit tests | |
| `frontend/lib/i18n.ts` | EN/VI RSS/jobs/runs strings | |
| `frontend/components/admin/RssSourcesPanel.tsx` | NEW admin RSS panel | |
| `frontend/components/admin/JobControlsPanel.tsx` | NEW news job toggle + 409 reload | |
| `frontend/components/admin/JobRunsPanel.tsx` | NEW sanitized JobRuns table | |
| `frontend/components/admin/AdminPageClient.tsx:211` | Compose three panels under users table | |
| `frontend/e2e/admin-rss.spec.ts` | Playwright admin RSS/jobs happy + validation + mobile | |
| `.workflows/runs/bl028_localstack_evidence.py` | LocalStack key evidence (untracked runs/) | |

## 3. Decisions & deviations from SA design

| # | SA said | Did | Reason |
|---|---------|-----|--------|
| 1 | D1–D5 locked | Followed | Typed errors, shared URL assert, bounded no-needle ingest, symbol-only persist, `/admin` panels only |
| 2 | `verify.ps1 -Profile full` | All gates green except `localstack-contract` compose name conflict | Existing `openportfo-localstack` container already healthy from another compose project; contract probe + BL-028 evidence script passed against `http://localhost:4566` |
| 3 | Fetcher IPv4 path | Fixed `getattr(ip, "ipv4_mapped", None)` | Pre-existing AttributeError on IPv4Address when DNS resolved public hosts |

## 4. How to verify

```powershell
cd D:\rmit\cloud\a3-wt-bl028\backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider

cd ..\frontend
npm run lint
npm test
npm run build
npx playwright test e2e/admin-rss.spec.ts e2e/smoke.spec.ts

# LocalStack (existing healthy container)
cd ..
backend\.venv\Scripts\python.exe .agents\skills\localstack-verification\scripts\verify_localstack.py
$env:DYNAMODB_ENDPOINT_URL='http://localhost:4566'
backend\.venv\Scripts\python.exe .workflows\runs\bl028_localstack_evidence.py

# Full gate (localstack compose may conflict if container already named)
.\.workflows\verify.ps1 -Profile full
```

## 5. Test evidence (paste)

```
backend focused: 30 passed (rss_fetcher + admin + jobs)
backend full:    543 passed, 5 skipped
frontend unit:   408 passed (63 files)
frontend lint:   pass
frontend build:  pass (next build --turbopack)
playwright:      4 passed (admin-rss ×3 + smoke)
LocalStack probe: status=pass (tables include openportfo-rss, openportfo-news, openportfo-job-runs)
BL-028 evidence: status=pass
  rss pk=RSS sk=bl028-evidence-src
  news pk=2026-08-28 sk=EvidenceFeed#bl028evidenceid000000001 symbols=[BTC]
  jobRun pk=JOB#news sk=2026-08-28T00:00:00+00:00#bl028-evidence-run
verify.ps1 full: 7/8 gates pass; localstack-contract fail (docker name conflict only)
```

### AC checklist

| AC | Met | Evidence |
|----|-----|----------|
| AC1 | yes | Admin RSS CRUD API + `RssSourcesPanel` + e2e create/toggle; `test_user_forbidden_on_admin` |
| AC2 | yes | `test_rss_fetcher` SSRF/redirect/non-2xx/transport; memory+Dynamo URL rejection |
| AC3 | yes | `test_news_job_isolates_sources_and_persists_one_partial_run`; disabled source skipped |
| AC4 | yes | `test_news_job_ingests_bounded_slice_when_no_needles` (25); deterministic dedupe replay |
| AC5 | yes | `test_news_job_tags_matched_asset_symbols_not_keywords` |
| AC6 | yes | Existing news/TopStories tests remain green (reuse path) |
| AC7 | yes | JobControlsPanel 409 reload unit test; JobRunsPanel; e2e mobile viewport |
| AC8 | mostly | pytest/vitest/playwright/build pass; LocalStack evidence pass; verify compose gate blocked by shared container name |

## 6. API / UX verification

- No new routes; reused `/api/admin/rss-sources`, `/api/admin/settings`, `/api/admin/job-runs`, `/api/news`.
- Playwright: admin session via `sessionStorage` token + routed API stubs; CRUD, enable toggle, news job toggle, validation alert, mobile layout.
- No “Run job now” control (BL-029).

## 7. Ports isolation check

```powershell
rg -n "^\s*(from\s+(boto3|botocore|httpx|requests)\b|import\s+(boto3|botocore|httpx|requests)\b)" backend/app/services backend/app/api backend/app/domain backend/app/jobs
```

Result: **clean** (exit code 1 / no matches). `httpx`/`feedparser` remain in `backend/app/adapters/rss/fetcher.py` only. Jobs import ports only.

## 8. Known limitations / follow-ons

- DNS rebinding residual risk documented in SA; redirect hops re-validated.
- News table still full-scan at demo scale (no GSI redesign).
- `verify.ps1` `localstack-contract` fails when `/openportfo-localstack` already exists from another compose project; endpoint + evidence otherwise green.
- Worktree needed local `npm ci` (junction `node_modules` broke Turbopack).
- Lambda/EventBridge scheduling is BL-029.

## 9. Handoff to SA Review

- Walkthrough ready for SA review: **yes**
- AC checklist self-assessed: **AC1–AC7 met; AC8 met with LocalStack evidence caveat on compose name conflict**
- Commits: **none** (left uncommitted for Orchestrator)
