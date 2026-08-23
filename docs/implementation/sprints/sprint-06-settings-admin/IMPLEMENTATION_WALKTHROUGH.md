# Sprint 06 settings/admin implementation walkthrough

Status: implementation complete and Solution Architect approved. BL-023 through BL-026 are `done` as of 2026-08-23; no commit or merge was performed.

## Files changed, added, and deleted

Backend contracts, services, adapters, and APIs:

- Extended `app/ports/users.py`, `app/ports/admin.py`, and `app/ports/llm.py` with profile/avatar patches, versioned system settings, and `top_p` runtime parameters.
- Added `app/services/user_settings.py`, `app/services/admin_user_service.py`, and `app/services/chat_settings_service.py` for shared validation, grant-only administration, role guardrails, cursor paging, optimistic settings, and chat runtime resolution.
- Updated memory and DynamoDB user/settings adapters, including nullable avatar/chat mappings, field-only profile writes, strong reads, optimistic versions, and the DynamoDB transaction guard for role changes.
- Updated `app/core/config.py`, `app/core/deps.py`, `app/api/auth.py`, and `app/api/admin.py` for `ADMIN_EMAILS`, full profile responses, paged admin users, role/settings mutations, and per-request chat settings.
- Updated LLM fallback/OpenAI-compatible adapters, orchestrator, chat service, and test fakes to forward `top_p` and immutable/runtime prompt composition.
- Added/updated backend tests in `tests/unit/services/{test_user_settings,test_admin_user_service,test_chat_settings_service}.py`, `tests/unit/api/test_admin_users.py`, and `tests/unit/adapters/test_users_repo.py`, plus the existing auth/admin/settings/mapper tests.

Frontend routes and state:

- Added static Suspense routes `app/settings/page.tsx` and `app/admin/page.tsx`.
- Added settings UI/API files: `components/settings/{SettingsPageClient,SettingsPageSkeleton,GeneralTab,AvatarTab,FxTab,ChatbotTab}.tsx` and `lib/settings-api.ts`.
- Added admin UI/API files: `components/admin/{AdminPageClient,AdminUserEditor}.tsx` and `lib/admin-api.ts`.
- Added `components/auth/AuthProfileProvider.tsx`, `lib/auth-profile-context.ts`, and shared profile fields/provider propagation in `lib/auth.ts`, `lib/use-auth-profile.ts`, `components/Providers.tsx`, `components/AppShell.tsx`, and `components/chat/ChatWidget.tsx`.
- Added `lib/user-settings-schema.ts`; extended `UserAvatar.tsx`, sidebar desktop/mobile navigation, i18n, and quick settings. Quick settings now links to `/settings` and `/settings?tab=fx` and no longer owns FX rendering.
- Deleted `components/currency/FxRatesPanel.tsx` and its obsolete test. Added focused tests for the provider, settings route/tabs/schema/chatbot, admin page, and FX behavior.

Deployment and documentation:

- Added `ADMIN_EMAILS` and optional LLM defaults to `backend/.env.example` and deployment docs.
- Added `dynamodb:TransactWriteItems` to the EB policy/template and documented the required lab instance-profile permission.
- Updated the sprint brief/backlog metadata and sprint-12 runbook without changing item status.

## Behavior walkthrough

1. A verified auth request bootstraps or refreshes only identity fields. User settings patches validate keyword, currency, avatar style/seed/color, and explicit null clearing; DynamoDB updates are field-only so a settings write cannot overwrite a role. Missing legacy avatar attributes map to null.
2. `ADMIN_EMAILS` is parsed case-insensitively and used only as a grant-only promotion source. Admin users are returned through opaque, bounded cursors. User/admin role changes preserve self/whitelist/last-admin rules; the Dynamo adapter uses a settings guard item and conditional transaction with one conflict retry.
3. `SystemSettings` carries a version and nullable chat overrides. Writes require the expected version. Each chat request resolves a snapshot from stored overrides over environment defaults, distinguishes null fallbacks from an explicit empty list, validates the free-model floor, and forwards temperature/top-p/max-tokens/prompt suffix without exposing secrets or the immutable base prompt.
4. `AuthProfileProvider` is the single profile source for shell, sidebar, settings/admin pages, quick settings, and `ChatWidget`. It supports forced same-token reloads, aborts stale requests, clears 401/403 state, and lets successful settings/admin responses replace the shared profile immediately. `UserAvatar` uses the approved eight-style DiceBear set, deterministic seeds/colors, and resets image-error fallback when its effective URL changes.
5. `/settings` remains static-exported. Only the client subtree reads query parameters inside the page-level Suspense boundary. Valid tab changes use `router.push` without scroll; invalid/default/unauthorized values canonicalize with `router.replace`. Hydration and signed-out states show stable non-requesting UI. General and Avatar forms preserve edits on failure, save explicit patches, and Reset rehydrates the latest shared profile. FX reuses CurrencyProvider data and retains the prior table on refresh 502. Chatbot shows raw/default/effective values and preserves null versus `[]` semantics, with 409 reload handling.
6. `/admin` is static-exported and gates requests by the shared role. It shows hydration/sign-in/403 states without data flashes, supports deduplicated cursor paging, environment-managed role locks, safe role error messages, and an in-flow settings editor with focus return. Current-user mutations replace the shared profile.
7. The old nested FX dialog/panel and duplicate ownership were removed; the quick modal retains only quick account/theme/language/currency controls plus settings links.

## Key decisions and deviations

- The Sprint 05 canonical-only decision is preserved: this work adds no pre-hydration bootstrap, legacy browser-storage migration, former-name reads, or `verify:static-bootstrap` gate.
- Static export uses the supported Next 15 pattern: a Server Component page, a minimal client subtree, and `useSearchParams()` only below Suspense. No dynamic route, middleware, request-time search-param prop, or dependency was added.
- Profile and settings updates intentionally use explicit nullable patches. The UI keeps environment-default and no-fallback choices distinct instead of collapsing both to an empty value.
- `AuthProfileController.reloadProfile` and `replaceProfile` are required in the shared type; every production provider/fixture supplies both so profile replacement and auth recovery cannot silently no-op.
- Avatar settings now separate “Use default” (explicit null style/seed/color) from “Revert edits” (restore the latest profile values); both paths are covered by `SettingsTabs.test.tsx`.
- No interactive browser runner is installed in the repository (`npm ls @playwright/test playwright puppeteer cypress` is empty and no local browser command was available). DOM tests and emitted static HTML checks were strengthened; deployed-browser smokes remain a release follow-up.

## Verification

### Remediation cycle 1 (R1-R8)

- **R1/R2:** `DynamoUserProfileRepo` now uses strong reads, conditional first-auth creation, conditional existing-item mutations, and low-level `TypeSerializer` values/keys for the demotion transaction. Conditional cancellation is the only retry path; unrelated AWS errors propagate. Botocore Stubber/service-model tests cover the exact transaction shape, success, first-conflict retry, second conflict, target-role change, last-admin, AccessDenied, absent targets, and create races (`tests/unit/adapters/test_users_repo.py`).
- **R3:** EB-only `AdminRoleTransactions` statements are limited to `TransactWriteItems` on UsersTable and SettingsTable; the Lambda/general-table statements do not receive that action. Structural CloudFormation/IAM tests cover the separation (`tests/unit/test_admin_infrastructure.py`).
- **R4:** Chat patches merge with the strongly-read current singleton before full effective/free-only validation. Bounds, integer/control, model/fallback de-duplication, non-finite values, prompt suffix limits, version-0 conditions, and non-conflict Dynamo errors are covered. Runtime snapshots are rebuilt per request while existing services retain their snapshot; fallback and OpenAI-compatible adapters assert exact sampling/token forwarding.
- **R5:** Avatar “Use default” saves explicit null style/seed/color, while “Revert edits” restores the current profile. The real admin editor maps a blank keyword field to `[]`, supports explicit clears, preserves errors, and returns focus. Avatar/admin/settings component tests cover these paths.
- **R6:** FX renders localized fresh/stale/missing status; refresh catches transport failures, retains prior data, clears busy state in `finally`, deduplicates clicks, and reloads auth only for 401/403 results. Focused tests cover fresh/stale/missing, thrown failure, retained 502 data, auth responses, and duplicate refresh boundaries.
- **R7:** Chatbot now renders raw/default/effective values for all six fields, preserves null versus `[]`/empty suffix semantics, warns about provider support, validates client ranges/integer/control/duplicate inputs, associates errors, blocks duplicate/invalid saves, and preserves edits on conflict. The real-child non-admin deep-link test proves no admin request.
- **R8:** Auth/admin settings request models accept raw patch values so malformed field values reach the shared normalizers and return 400 `validation_error` maps; profile controller methods are required; form errors use `aria-invalid`/`aria-describedby`; non-admin chatbot selection is clamped synchronously before rendering.

Initial verification snapshot (superseded by the final remediation gate results below):

- Backend: `backend\.venv\Scripts\python.exe -m pytest -q` — **480 passed, 4 skipped, 5 warnings in 13.20s**.
- Frontend focused additions: provider/schema, settings route/tabs/chatbot, admin page, and FX tests all passed.
- Frontend: `npm test` — **50 test files passed, 337 tests passed** (17.95s).
- Frontend typecheck: `npx tsc --noEmit` — passed.
- Frontend production export: `npm run build` — passed; `/admin` and `/settings` are listed as static routes and `out/admin/index.html` plus `out/settings/index.html` were emitted. The emitted HTML contains the expected static Suspense fallback (`aria-busy="true"`; settings includes Next's client-rendering bailout marker), not a request-time route.
- `git diff --check` — clean apart from normal Git LF/CRLF working-copy notices.
- Lockfiles — no package or dependency changes.
- Close-out search: `rg "FxRatesPanel" frontend` returned no matches. The Sprint 06 source contains no new bootstrap/migration/verify-static-bootstrap implementation; existing unrelated legacy compatibility comments/routes remain untouched. `Test-Path backend/AGENTS.md` is verified false after the final backend run.

The frontend test runner reports its existing Vite `configLoader: "native"` warning and jsdom's expected “navigation to another Document” notices. The build reports only the pre-existing `PortfolioDashboard` `useMemo` dependency warning. Backend warnings are the existing unknown `asyncio_mode`, Starlette/httpx deprecation, Vnstock/Vnai update notices, and pytest-cache permission warning.

### Final remediation gate results

The earlier baseline counts above are retained for traceability; the final remediation run supersedes them:

- **R4-S2:** `DynamoSettingsRepo.save` now uses an atomic version-0 condition that permits only an absent singleton, a legacy item without `version`, or an existing version 0. Positive expected versions require existing `pk`/`sk` and an exact version, so a delete-after-read cannot recreate settings. The seven-case settings adapter matrix uses a botocore Stubber for exact resource request parameters plus stateful race/delete semantics.
- **R4-S3:** Added an OpenAI-compatible `httpx.MockTransport` regression test proving null `max_tokens`, `temperature`, and `top_p` are omitted from the request JSON.
- Backend `backend/.venv/Scripts/python.exe -m pytest -q`: **512 passed, 4 skipped, 5 warnings in 13.48s**.
- Backend focused R4 set (`test_settings_repo.py`, OpenAI-compatible adapter, chat settings, runtime): **27 passed**.
- Frontend `npm test -- --reporter=dot`: **52 test files passed, 346 tests passed** (9.07s).
- Frontend `npx tsc --noEmit`: passed.
- Frontend `npm run build`: passed. `/admin` and `/settings` are static routes; `out/admin/index.html` is 22,889 bytes and `out/settings/index.html` is 23,264 bytes. A post-build check confirmed both contain the static shell and `aria-busy="true"`; settings also contains Next's client-rendering bailout marker.
- `git diff --check`: clean apart from normal LF/CRLF working-copy notices. No lockfile changed. `rg "FxRatesPanel" frontend`: no matches.
- `backend/AGENTS.md` was generated by the backend test tooling and removed after the final backend run; it is not product code.

## Known limitations and reviewer focus

Manual deployed-browser validation is still needed for static-host query deep links/history, Cognito return URLs, responsive mobile tab/table layouts, focus behavior, DiceBear network success/failure, and real AWS 502/admin transaction flows. Architect review should focus on DynamoDB conditional transaction/guard semantics and IAM scope, whitelist grant-only behavior, shared profile replacement and chat-session ownership, static Suspense/canonicalization, nullable chat override resolution, and FX retained-data error rendering.
