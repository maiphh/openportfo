# SA Design — BL-028: RSS source news completion

| Field | Value |
|-------|-------|
| **ID** | `BL-028` |
| **Title** | RSS source management and reliable news ingestion |
| **Status** | `ready_for_implementation` |
| **Author (SA)** | Solution Architect |
| **Date** | 2026-08-28 |
| **Complexity** | `simple` |
| **Related PRD** | `docs/prd/OpenPortfo_PRD.md#8.7` (FR-N1–N4), `docs/prd/OpenPortfo_PRD.md#8.8` (FR-AD2–AD5), `docs/prd/OpenPortfo_PRD.md#8.9` (FR-J2 news job) |
| **Related Arch** | `docs/architecture-design.md#2.3` (News — RSS), `#4.1` (Admin RSS / News read), `#4.2` (Admin page), `#4.3` (RssSources / JobRuns / News), `#5` (scheduled pipelines — deploy owned by BL-029) |
| **Feature file** | `docs/backlog/features/BL-028-rss-news.md` |

---

## 1. Context & constraints

- Problem / user value: The repo already reads news and has RSS/job foundations, but admins cannot manage RSS sources in-product, the HTTP fetcher swallows transport failures as empty feeds, memory URL validation is weaker than Dynamo, ingest skips entirely when the global needle set is empty, and News rows never store matched asset symbols. Complete the existing path so admins configure sources/job flags/JobRuns on `/admin` and signed-in users get reliable, bounded, relevant news via `/api/news` + Top Stories — without deploying Lambda/EventBridge (BL-029).

- Locked stack constraints:
  - No API Gateway for user APIs (Beanstalk FastAPI only) — reuse existing `/api/admin/*` and `/api/news`
  - No Next.js SSR (CSR/static export → S3+CloudFront) — extend `/admin` client panels only
  - No browser-direct RSS/market HTTP — all feed fetch stays in `backend/app/adapters/rss/fetcher.py`
  - Cache-first pricing / on-demand FX unchanged — news path does not touch FX or market APIs
  - Cognito JWT via JWKS; admin mutations use `require_admin`; news read uses `get_current_user`
  - Ports isolation: no `boto3`/`httpx`/`feedparser` outside `adapters/` (and tests/fakes)

- Foundations to complete (not redesign): S08/S10/S12 admin RSS API, `run_news_job`, `NewsService`, Top Stories CSR client.

---

## 2. Affected surfaces

| Layer | Paths / components | Change type |
|-------|--------------------|-------------|
| Frontend | `frontend/lib/admin-api.ts` — add RSS + JobRun types and CRUD/list helpers beside existing settings/users clients | **modify** |
| Frontend | `frontend/components/admin/RssSourcesPanel.tsx` (**NEW**), `JobControlsPanel.tsx` (**NEW**), `JobRunsPanel.tsx` (**NEW**) + co-located `*.test.tsx` | **new** |
| Frontend | `frontend/components/admin/AdminPageClient.tsx` — compose new panels below (or beside) user-role table; do not break user CRUD | **modify** |
| Frontend | `frontend/lib/i18n.ts` — EN/VI strings for RSS/jobs/runs loading/empty/validation/conflict/error | **modify** |
| Frontend | `frontend/lib/news.ts`, `frontend/components/dashboard/TopStories.tsx` | **reuse** (verify only; no mock fallback) |
| Frontend | `frontend/e2e/admin-rss.spec.ts` (**NEW**) | **new** |
| Backend API | `backend/app/api/admin.py` — existing `/api/admin/rss-sources`, `/api/admin/settings`, `/api/admin/job-runs` (no new routes) | **reuse / minor fix only if response sanitization gaps appear** |
| Backend API | `backend/app/api/news.py` — `GET /api/news` | **reuse** |
| Domain / services | `backend/app/services/news_service.py` — keep no-needle → recent unfiltered; title/`symbols` match; never read legacy `keywords` | **reuse** (change only if AC6 regressions require) |
| Ports | `backend/app/ports/rss.py` — add typed `RssFetchError` (+ export) | **modify** |
| Ports | `backend/app/ports/admin.py` (`RssSource`, `JobRun`, repos), `backend/app/ports/news.py` (`NewsItem.symbols`) | **reuse** |
| Adapters | `backend/app/adapters/rss/fetcher.py` — raise `RssFetchError` on transport/non-2xx/redirect exhaustion; keep SSRF + redirect re-validation; UTC `published_at`; optional entry/response bound | **modify** |
| Adapters | `backend/app/adapters/memory/admin.py` — `InMemoryRssSourcesRepo` must call shared `assert_public_http_url` (parity with Dynamo) | **modify** |
| Adapters | `backend/app/adapters/dynamodb/rss.py` — already uses `assert_public_http_url`; keep | **reuse** |
| Adapters | `backend/app/adapters/dynamodb/news.py` / `memory/news.py` — deterministic `put` upsert by existing PK/SK | **reuse** |
| Adapters | `backend/app/adapters/memory/rss.py` (`FakeRssFetcher`) | **reuse / minor if fake must raise** |
| Infra / jobs | `backend/app/jobs/news_job.py` — bounded no-needle ingest, symbol-only tags, source isolation, one aggregate JobRun | **modify** |
| Infra / jobs | `backend/app/jobs/job_utils.py`, `handler.py`, `context.py` | **reuse** |
| Infra / jobs | `infra/*`, Lambda packaging, EventBridge | **MUST NOT edit** (BL-029) |
| Docs / tests | `backend/tests/unit/adapters/test_rss_fetcher.py` (**NEW**), extend `backend/tests/unit/jobs/test_jobs.py`, `backend/tests/unit/api/test_admin.py`, `backend/tests/unit/api/test_news.py` as needed | **new/modify** |
| Docs | this design + feature status | **modify** |

---

## 3. API & data model deltas

### 3.1 API

| Method & path | Auth | Request | Response | Notes |
|---------------|------|---------|----------|-------|
| `GET /api/admin/rss-sources` | Admin (`require_admin`) | — | `[{sourceId,name,url,enabled}]` | Existing |
| `POST /api/admin/rss-sources` | Admin | `{name,url,enabled?,sourceId?}` | `201` source | URL validated in repo → `400` `AdminValidationError` |
| `PUT /api/admin/rss-sources/{sourceId}` | Admin | `{name?,url?,enabled?}` | source | `404` missing; `400` bad URL |
| `DELETE /api/admin/rss-sources/{sourceId}` | Admin | — | `204` | `404` missing |
| `GET /api/admin/settings` | Admin | — | settings incl. `version`, `jobs.{news,snapshot,email,price}` | News toggle uses `jobs.news` + optimistic `version` |
| `PUT /api/admin/settings` | Admin | `{version, jobs?: {news?: bool, …}, …}` | settings | `409` `{code:"settings_conflict"}` → UI reloads |
| `GET /api/admin/job-runs?jobType=&limit=` | Admin | query | `[{runId,jobType,status,startedAt,finishedAt,message,counts}]` | Sanitized `message` only (no raw headers/bodies) |
| `GET /api/news?limit=` | Signed-in user | `limit` 1–200 | `[{id,title,url,source,publishedAt,symbols,date}]` | Unchanged contract; filled by job |

**No new backend routes.** No browser endpoint that invokes the news job (BL-029 schedules Lambda).

### 3.2 Data model

```
RssSources:  PK=RSS / SK=sourceId
  attrs: sourceId, name, url, enabled
News:        PK=date|NEWS / SK=source#{id}
  attrs: id, title, url, source, publishedAt, symbols[], date
SystemSettings: SETTINGS/GLOBAL
  attrs: jobs_news, version, … (existing)
JobRuns:     existing job-run table / memory list
  attrs: runId, jobType="news", status=success|partial|error|skipped,
         startedAt, finishedAt, message, counts
```

- DynamoDB: **no key redesign**. Counts keys (keep compatibility): `written`, `fetched`, `sources`, `sources_attempted`, `sources_succeeded`, `sources_failed`, plus aliases `attempted`/`succeeded`/`failed`.
- S3: none for this BL.
- Schemas: reuse `RssCreate`/`RssUpdate` in `backend/app/api/admin.py`; `NewsItemResponse` in `backend/app/api/schemas.py`. Port: add `RssFetchError` in `backend/app/ports/rss.py`.

**Ingest constants (locked):** `MAX_ITEMS_PER_SOURCE = 25` (recent slice after parse, newest-first when timestamps exist). Article id = `sha256(normalize_url(url) + "|" + normalize_title(title))[:24]` so replay upserts.

---

## 4. Sequence (happy path)

```
Admin → /admin UI → FastAPI admin APIs → RssSources/Settings/JobRuns (Dynamo)
Event (BL-029 later) → run_news_job → RssFetcher → NewsRepo → JobRuns
User → TopStories → GET /api/news → NewsService → NewsRepo
```

ASCII sequence:

```
A. Admin configures sources + news job
1. Admin opens /admin (AdminPageClient)
2. RssSourcesPanel: GET /api/admin/rss-sources → list; POST/PUT/DELETE for CRUD/enable
3. JobControlsPanel: GET /api/admin/settings → toggle jobs.news via PUT {version, jobs:{news:true}}
   - on 409 settings_conflict → reload settings and show conflict copy
4. JobRunsPanel: GET /api/admin/job-runs?jobType=news → show sanitized status/counts

B. News ingest (job code path; schedule deploy is BL-029)
5. run_news_job(ctx): if !settings.jobs_news → JobRun status=skipped, counts zeros
6. List enabled RssSources only; collect symbol_needles (holdings+watchlist) and keyword_needles (profiles)
7. For each enabled source independently:
   a. HttpRssFetcher.fetch(url) — SSRF check, redirects re-validated, else raise RssFetchError
   b. Take up to MAX_ITEMS_PER_SOURCE recent items
   c. If any needles exist: keep items matching title against union(needles)
      Else: keep the bounded recent slice (AC4)
   d. For each kept item: symbols = asset symbols that appear in title (never keywords);
      put NewsItem with deterministic id; count written/fetched
   e. On RssFetchError/other: sources_failed++; sanitize into failures[]; continue
8. Persist ONE JobRun: aggregate_status(attempted, failed) → success|partial|error

C. User reads news
9. TopStories → fetchNews → GET /api/news
10. NewsService.list_for_user: filter by user keywords+symbols; if user has no needles → recent slice
11. UI shows source/title/link/date/symbols with loading|empty|auth|error+retry (no mock data)
```

---

## 5. Decisions (ADR style)

| # | Context | Decision | Consequence | Alternatives rejected |
|---|---------|----------|-------------|-----------------------|
| D1 | Fetcher currently returns `[]` on `httpx.HTTPError` / `ValueError`, so jobs cannot distinguish empty feed vs failure (AC2/AC3) | Add `RssFetchError` on the port; `HttpRssFetcher` raises it for transport, non-2xx, redirect missing/exhaustion, and SSRF rejection after initial parse gate; job catches per source | Partial/error JobRuns become accurate; empty parse still returns `[]` success | Keep empty-list swallow; map failures only via logging |
| D2 | Memory RSS repo only checks `http(s)+host`; Dynamo uses `assert_public_http_url` | Both repos call the same `assert_public_http_url` from `adapters/rss/fetcher.py` (or a tiny shared helper imported by both adapters). Validate create/update URLs; fetcher re-validates every redirect target | Consistent 400s in tests and LocalStack; redirect SSRF mitigated best-effort | Duplicate weaker memory rules; DNS-pinning proxy (out of scope) |
| D3 | Empty global needles currently skip all fetches (`news_job.py` “successful no-op”) | Always fetch enabled sources when `jobs_news`; if no needles, ingest up to `MAX_ITEMS_PER_SOURCE` recent items per source; personalization stays in `NewsService` at read time | AC4 satisfied; demo works before any user keywords exist | Keep skip; require seed keywords |
| D4 | Written `symbols` always `[]`; private keywords must not leak into shared News | Split collection into `asset_symbols` vs `keyword_needles`; match on union for *selection*; persist only title-matched **asset** symbols in `NewsItem.symbols` | AC5 privacy + Top Stories symbol chips | Persist keywords; store userId on News |
| D5 | Admin UI only manages users today | Add three focused panels on existing `/admin`; reuse `/api/admin/*`; no new route, no “Run job now” button | FR-AD2–AD4 in product; BL-029 remains scheduler | New `/admin/news` route; browser-triggered Lambda |

---

## 6. Complexity assessment

- [ ] Requires choosing between ≥2 libs/patterns → Researcher needed — **false** (`httpx` + `feedparser` already locked)
- [ ] Security / auth / cost-critical AWS path — **false for research**: reuse existing admin Cognito gate + existing SSRF helper; no new AWS cost surface (Lambda deploy is BL-029)
- [ ] No prior port/adapter pattern to reuse — **false** (`RssFetcher`, `RssSourcesRepo`, `run_news_job`, admin API already exist)
- [ ] Risk to locked decisions — **false** (no API GW, no SSR, no browser RSS, no table redesign)

**Verdict:** `simple`

**Research questions:** none

---

## 7. Handoff to Implementor

### File ownership

- Allowed to edit (this worktree / this BL):
  - `backend/app/ports/rss.py`
  - `backend/app/adapters/rss/fetcher.py`
  - `backend/app/adapters/memory/admin.py` (RSS URL validation parity)
  - `backend/app/jobs/news_job.py`
  - `backend/tests/unit/adapters/test_rss_fetcher.py` (new)
  - `backend/tests/unit/jobs/test_jobs.py` (rewrite/extend news cases)
  - `backend/tests/unit/api/test_admin.py` (URL rejection / auth as needed)
  - `frontend/lib/admin-api.ts`, `frontend/lib/i18n.ts`
  - `frontend/components/admin/AdminPageClient.tsx` + new panel components/tests
  - `frontend/e2e/admin-rss.spec.ts`
  - Docs under `docs/orchestration/*` / feature file only if Implementor walkthrough phase

- Must NOT edit:
  - `infra/**`, Lambda/EventBridge wiring, `backend/app/jobs/lambda_entry.py` deploy config (BL-029)
  - Unrelated BLs / other worktrees
  - Portfolio/FX/chat/holdings features beyond incidental import reuse
  - Production AWS resources; no push/merge/deploy

### TDD order

1. **RSS adapter (failing first)** — `backend/tests/unit/adapters/test_rss_fetcher.py`
   - `test_fetch_parses_rss_atom_and_utc_published_at`
   - `test_fetch_raises_rss_fetch_error_on_http_transport_failure`
   - `test_fetch_raises_on_non_2xx`
   - `test_fetch_rejects_private_loopback_and_link_local_hosts`
   - `test_fetch_rejects_unsafe_redirect_target_and_redirect_exhaustion`
2. **URL validation parity** — extend admin/memory tests (in `test_admin.py` or small adapter test)
   - `test_memory_and_dynamo_reject_same_unsafe_rss_urls` (or memory-focused cases mirroring Dynamo)
3. **News job** — `backend/tests/unit/jobs/test_jobs.py`
   - Replace/repurpose `test_news_job_skips_write_when_no_needles` → `test_news_job_ingests_bounded_slice_when_no_needles`
   - `test_news_job_tags_matched_asset_symbols_not_keywords`
   - `test_news_job_deterministic_dedupe_on_replay`
   - Keep/extend: `test_news_job_disabled_skips`, `test_news_job_isolates_sources_and_persists_one_partial_run`, disabled-source not fetched
4. Implement backend changes until focused pytest green.
5. **Frontend unit** — `frontend/lib/admin-api` tests (new or extend) + panel tests:
   - RSS CRUD success/validation/forbidden mapping
   - Job toggle `409` → reload
   - JobRuns empty/loading/error + sanitized message display
   - a11y: labelled controls, `role="alert"` on errors
6. Implement panels + compose into `AdminPageClient`; keep Top Stories regression green (`TopStories.test.tsx`, `news.test.ts`).
7. **Playwright** — `frontend/e2e/admin-rss.spec.ts`: admin CRUD/enable + jobs panel happy path; one validation/failure boundary; desktop + one mobile viewport if layout changes.
8. Verification: focused pytest/Vitest → LocalStack Dynamo evidence for RSS/News/JobRuns keys → `.workflows/verify.ps1 -Profile full`.

### Out-of-scope guardrails

- Do **not** deploy or configure Lambda/EventBridge (BL-029).
- Do **not** add “Run news job” browser/API trigger.
- Do **not** add public/unauthenticated news, API Gateway, SES, NLP, or News GSI redesign.
- Do **not** persist `newsKeywords` or user ids on shared News rows.
- Do **not** put `httpx`/`feedparser`/`boto3` in `services/`, `domain/`, or `jobs/` (jobs call ports only).
- Do **not** mutate real AWS outside LocalStack test keys; delete only exact test keys.

---

## 8. Acceptance criteria checklist (copy from feature file)

- [ ] AC1 Admins can list/create/update/enable/disable/delete RSS sources; non-admin access remains forbidden.
- [ ] AC2 Malformed, loopback, private/link-local/reserved hosts and unsafe redirect targets are rejected consistently; transport/non-2xx/redirect exhaustion is observable as a source failure.
- [ ] AC3 Only enabled sources are fetched; one source failure does not stop healthy sources and one aggregate JobRun reports success/partial/error/skipped with accurate counts.
- [ ] AC4 A bounded recent set is ingested even with no user keywords, holdings, or watchlist; repeated ingestion is deterministic and does not create duplicate logical articles.
- [ ] AC5 Matching known holding/watchlist symbols are stored in `symbols`; private `newsKeywords` are never persisted in shared News rows.
- [ ] AC6 Existing authenticated `/api/news` and Top Stories render real source/title/link/date/symbol data, including loading, empty, auth, and retry behavior without mock fallback.
- [ ] AC7 The `/admin` UI exposes the news job toggle and recent sanitized JobRuns, handles settings version conflicts by reloading, and provides accessible desktop/mobile controls.
- [ ] AC8 Focused pytest/Vitest/Playwright tests, LocalStack DynamoDB evidence, production build, and `.workflows/verify.ps1 -Profile full` pass.

---

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| DNS rebinding after initial resolve | Re-validate every redirect URL with `assert_public_http_url`; document residual risk; keep Lambda egress narrow in BL-029 |
| Feed quality / bad timestamps | Best-effort UTC parse; source isolation; visible JobRun failures |
| Dynamo News full-table scan | Accept demo scale; no index redesign in BL-028 |
| Existing test `test_news_job_skips_write_when_no_needles` encodes old behaviour | Explicitly rewrite to bounded-ingest assertion (D3) |
| Admin settings conflict UX | Mirror user-role 409 reload pattern already in `AdminPageClient` |

---

## 10. Research linkage (if any)

- Research doc: _n/a_ (simple)
- Research recommendation adopted: _n/a_

---

**SA sign-off:** `ready_for_implementation` — Implementor may start in worktree `D:\rmit\cloud\a3-wt-bl028` on `feat/BL-028-rss-news`.
