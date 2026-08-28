# SA Review — BL-028: RSS source news completion

| Field | Value |
|-------|-------|
| **ID** | `BL-028` |
| **Reviewer (SA)** | Solution Architect (review mode) |
| **Date** | 2026-08-28 |
| **Walkthrough** | `docs/orchestration/walkthroughs/BL-028-rss-news-walkthrough.md` |
| **Verdict** | `approve` |

---

## 1. AC verification

| AC | Satisfied? | Evidence (file:line or test) | Note |
|----|------------|------------------------------|------|
| AC1 | yes | API: `test_rss_crud` `backend/tests/unit/api/test_admin.py:102-118`; forbid: `test_user_forbidden_on_admin` `:36`; UI: `RssSourcesPanel` create/toggle/delete `frontend/components/admin/RssSourcesPanel.tsx:52-100`, unit `RssSourcesPanel.test.tsx`; compose `AdminPageClient.tsx:211`; e2e `frontend/e2e/admin-rss.spec.ts` | List/create/update(enable)/delete covered; non-admin remains forbidden. |
| AC2 | yes | Fetcher: `test_fetch_raises_rss_fetch_error_on_http_transport_failure` `test_rss_fetcher.py:64-70`; `test_fetch_raises_on_non_2xx` `:73-79`; `test_fetch_rejects_private_loopback_and_link_local_hosts` `:82-98`; `test_fetch_rejects_unsafe_redirect_target_and_redirect_exhaustion` `:101-130`; raise sites `fetcher.py:161-164`, `:196`, `:201`, `:205`, `:207`; URL parity: `test_memory_rejects_unsafe_rss_urls` `test_admin.py:130-147`, `test_memory_and_dynamo_reject_same_unsafe_rss_urls` `:150-166`; memory `admin.py:104-108` → `assert_public_http_url` | Shared validator; transport/non-2xx/redirect/SSRF → `RssFetchError`. |
| AC3 | yes | `test_news_job_isolates_sources_and_persists_one_partial_run` `test_jobs.py:499-527`; `test_news_job_skips_disabled_sources` `:308-332`; `test_news_job_disabled_skips` `:125`; enabled-only filter `news_job.py:193`; one JobRun `news_job.py:239-253` | `partial` + accurate counts; disabled never fetched. |
| AC4 | yes | `test_news_job_ingests_bounded_slice_when_no_needles` `test_jobs.py:229-245` (`written==25`); `MAX_ITEMS_PER_SOURCE=25` `news_job.py:21`, slice `:128-138`; `test_news_job_deterministic_dedupe_on_replay` `:286-305`; id `news_job.py:32-34` | No-needle ingest + replay upsert (same logical id). |
| AC5 | yes | `test_news_job_tags_matched_asset_symbols_not_keywords` `test_jobs.py:248-283`; persist `_matched_asset_symbols` only `news_job.py:219`; split collection `:80-125` | Keywords match for selection; never stored in `symbols`. |
| AC6 | yes | Reuse path unchanged: `frontend/lib/news.ts` `fetchNews`; `TopStories.tsx`; green suite claims `news.test.ts` (no mock seed `:108`, auth/retry), `TopStories.test.tsx` (loading/empty/401/retry, no mock headlines) | No mock fallback; no BL-028 edits required on news read path. |
| AC7 | yes | `JobControlsPanel.tsx:36-67` (409 → reload + notice); unit `JobControlsPanel.test.tsx` “toggles news job and reloads on settings conflict”; `JobRunsPanel.tsx` + `JobRunsPanel.test.tsx` (empty/loading/`role="alert"`/sanitized message); e2e mobile viewport in `admin-rss.spec.ts`; panels on `/admin` `AdminPageClient.tsx:211-213` | No “Run job now” control. |
| AC8 | yes | Re-ran focused pytest: **15 passed** (rss_fetcher + admin URL/forbidden/crud + news job suite). Walkthrough: backend full 543 passed / FE 408 / lint+build / playwright 4. LocalStack: container `openportfo-localstack` **Up (healthy)** `:4566`; probe + `.workflows/runs/bl028_localstack_evidence.py` pass (RSS/News/JobRuns keys). | **AC8 LocalStack limb:** `verify.ps1` `localstack-contract` compose-up name conflict against an *already healthy* LocalStack does **not** fail AC8 when probe + Dynamo evidence against `http://localhost:4566` pass — that is the contract intent. Compose project-name collision is env-only, not a BL-028 product defect. |

---

## 2. Architecture checks

- [x] Ports isolation (`boto3`/`httpx` only in `adapters/`)? Grep of import forms under `backend/app/services`, `api`, `domain`, `jobs`: **empty**. `httpx`/`feedparser` only in `backend/app/adapters/rss/fetcher.py`. Jobs import ports only (`news_job.py:9-19`). Shared `assert_public_http_url` imported adapter→adapter (`memory/admin.py:10`, `dynamodb/rss.py:15`) — allowed by D2.
- [x] Locked decisions intact?
  - No Lambda/EventBridge / `infra/**` / `lambda_entry` in diff (BL-029).
  - No API GW; no new routes — reuse `/api/admin/*` + `/api/news`.
  - No SSR — panels are `"use client"`.
  - Typed `RssFetchError` `backend/app/ports/rss.py:18-19`.
  - Shared URL validation `assert_public_http_url` `fetcher.py:73-85`.
  - `MAX_ITEMS_PER_SOURCE=25` `news_job.py:21`.
  - Symbol-only tags `news_job.py:219` (+ AC5 test).
  - No browser RSS/market HTTP; Cognito admin/`get_current_user` reuse; cache-first/FX untouched.
- [x] Cost/budget impact ≤$50 narrative respected? No multi-AZ, NAT, new AWS surface; schedule deploy deferred to BL-029.
- [x] Security (no secrets in frontend/Git, no presigned leak)? SSRF/redirect re-validation; JobRun messages sanitized via existing `sanitize_error`; no secrets added.

---

## 3. Code quality

- [x] Tests green + meaningful (not just `assert True`)? Focused re-run **15 passed**; assertions cover HTTP codes, bounds (25), symbols≠keywords, partial isolation, SSRF/redirect/`RssFetchError`.
- [x] File ownership respected? Diff limited to design allow-list (+ `BACKLOG.md`, panel tests, evidence script under `.workflows/runs/`). **Not edited:** `infra/**`, Lambda/EventBridge, portfolio/FX/chat beyond incidental.
- [x] Error model `{detail: ...}` + correct HTTP codes? Admin validation → `400`; forbidden → `403`; settings conflict → `409` UI reload; DELETE → `204` handled `admin-api.ts:80`.

---

## 4. Issues (if request_changes)

| # | File:line | Issue | Required fix |
|---|-----------|-------|--------------|
| — | — | none | — |

---

## 5. Decision

- **If approve:** Orchestrator may merge branch `feat/BL-028-rss-news` → `integration/*` or `main`, mark backlog `done`.
- **If request_changes:** Implementor to address issues in same worktree, re-run tests, update walkthrough, re-request review. No new worktree.

**Verdict: `approve`.** Orchestrator may mark `docs/backlog/features/BL-028-rss-news.md` `done` and merge when ready. Do **not** add Lambda/EventBridge or a browser “Run news job” trigger under this BL (BL-029).

---

## 6. Notes for Orchestrator

1. Implementation is **uncommitted** in worktree `D:\rmit\cloud\a3-wt-bl028` — commit/merge as Orchestrator policy requires.
2. AC8 compose caveat accepted: existing healthy `openportfo-localstack` on `:4566` + probe + `bl028_localstack_evidence.py` satisfy LocalStack Dynamo evidence. Optional hygiene: tear down conflicting compose project before a vanity `verify.ps1 -Profile full` 8/8, or harden the gate later (out of BL-028 ownership).
3. Walkthrough file:line claims spot-checked and accurate (`ports/rss.py:18`, `fetcher.py:73`, `news_job.py:21/45/80`, `AdminPageClient.tsx:211`).
4. Non-blocking: isolation fake raises `RuntimeError` not `RssFetchError` (`test_jobs.py:394`); job `except Exception` still isolates — OK.
