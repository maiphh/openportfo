# BL-028 — RSS source news completion

| Field | Value |
|-------|--------|
| **ID** | `BL-028` |
| **Title** | RSS source management and reliable news ingestion |
| **Priority** | `P0` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Implementer |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | FR-N1–N4, FR-AD2–AD5; S08/S10/S12 follow-on |
| **Created** | 2026-08-28 |
| **Ready date** | 2026-08-28 |
| **Done date** | 2026-08-28 |

## 1. Problem / user value

The repository can read news and contains RSS/job foundations, but admins cannot manage RSS sources in the product and the ingest path misclassifies some failures, stores no symbol tags, and ingests nothing when no user has matching needles. Complete the existing path so administrators can configure sources and users receive reliable, relevant news.

## 2. User stories

- As an admin, I can manage enabled RSS sources and inspect news-job results without redeploying.
- As an investor, I receive real, bounded RSS news through the existing authenticated news UI.

## 3. Scope

### In scope

- Admin RSS list/create/edit/enable/disable/delete UI on `/admin`.
- Admin news job toggle and recent JobRuns panel.
- Consistent public HTTP(S) URL validation in memory and DynamoDB repositories.
- Typed RSS transport failures, redirect safety, UTC dates, and source isolation.
- Bounded ingestion even when the global user needle set is empty.
- Deterministic dedupe and matched asset-symbol tags without persisting personal keywords.
- Existing `/api/news` and Top Stories end-to-end behavior.

### Out of scope

- Deploying Lambda/EventBridge (BL-029), manual browser job trigger, SES, NLP, API Gateway, public unauthenticated news, deleting real AWS resources, or changing the static-CSR/FastAPI split.

## 4. Behaviour

1. Admin adds or enables a safe RSS source and enables the news job.
2. The job fetches every enabled source independently, takes a bounded recent slice, tags known asset-symbol matches, writes deterministic News rows, and persists one aggregate JobRun.
3. A failed source yields `partial` when another succeeds; disabled sources are never fetched.
4. Signed-in users read relevant items from `/api/news`; users with no needles receive recent bounded items.
5. The admin page shows source state and recent run status/counts with loading, empty, validation, conflict, and failure states.

## 5. Acceptance criteria

- [ ] AC1 Admins can list/create/update/enable/disable/delete RSS sources; non-admin access remains forbidden.
- [ ] AC2 Malformed, loopback, private/link-local/reserved hosts and unsafe redirect targets are rejected consistently; transport/non-2xx/redirect exhaustion is observable as a source failure.
- [ ] AC3 Only enabled sources are fetched; one source failure does not stop healthy sources and one aggregate JobRun reports success/partial/error/skipped with accurate counts.
- [ ] AC4 A bounded recent set is ingested even with no user keywords, holdings, or watchlist; repeated ingestion is deterministic and does not create duplicate logical articles.
- [ ] AC5 Matching known holding/watchlist symbols are stored in `symbols`; private `newsKeywords` are never persisted in shared News rows.
- [ ] AC6 Existing authenticated `/api/news` and Top Stories render real source/title/link/date/symbol data, including loading, empty, auth, and retry behavior without mock fallback.
- [ ] AC7 The `/admin` UI exposes the news job toggle and recent sanitized JobRuns, handles settings version conflicts by reloading, and provides accessible desktop/mobile controls.
- [ ] AC8 Focused pytest/Vitest/Playwright tests, LocalStack DynamoDB evidence, production build, and `.workflows/verify.ps1 -Profile full` pass.

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | DynamoDB RSS, News, Settings, JobRuns |
| APIs | Reuse `/api/admin/rss-sources`, `/api/admin/settings`, `/api/admin/job-runs`, `/api/news` |
| Auth | Admin for configuration/status; signed-in user for news |
| Freshness | Scheduled by BL-029; bounded items per source/invocation |
| Privacy | Match personal keywords in memory only; never store them on shared rows |

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `frontend/lib/admin-api.ts`, new admin RSS/jobs panels, `AdminPageClient.tsx`, i18n, tests/e2e |
| Backend | RSS port/adapter, memory admin adapter, news job, focused tests |
| Data | Existing RSS/News/Settings/JobRuns tables; no key change |
| Docs | BL/design/review/handoff |

## 8. Dependencies & risks

- Depends on the existing S08/S10/S12 news, admin, and adapter foundations.
- DNS rebinding cannot be eliminated by pre-resolution alone; validate every redirect and keep Lambda network/IAM scope narrow.
- DynamoDB News still scans at demo scale; no index redesign in this feature.
- External feed quality and timestamps are best effort; isolate and report sources.

## 9. Open questions

None blocking. Deployment and scheduling are explicitly BL-029.

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-28 | What happens with no user needles? | Ingest a bounded recent slice; personalize at read time. |
| 2026-08-28 | Where are job controls exposed? | Existing `/admin`, no new route or public trigger. |

## 11. Implementation notes

- Approach: test-first, preserve ports/adapters isolation and current API contracts.
- Branch: `feat/BL-028-rss-news`; worktree `D:\rmit\cloud\a3-wt-bl028`.
- Verification: pytest 543 passed; vitest 408; Playwright 4; LocalStack probe+Dynamo evidence pass; SA review `approve` (`docs/orchestration/reviews/BL-028-rss-news-review.md`). Not merged pending user authorization.
