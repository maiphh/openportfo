# Sprint 06 — settings, administration, chatbot controls, and FX

**Scope:** BL-023, BL-024, BL-025, BL-026 only  
**Architecture status:** approved for implementation subject to the authoritative `ARCHITECT_HANDOFF.md`  
**Backlog status:** do not change `ready` until implementation starts  
**Baseline:** frontend 44 files / 317 tests plus typecheck and static build; backend 435 passed / 4 skipped

## Outcome

Deliver two static frontend routes and the backend contracts they need:

- `/settings`: signed-in account settings with General, Avatar, FX, and admin-only Chatbot tabs;
- `/admin`: admin-only user matrix with paged listing, role control, and user-settings editing;
- profile-backed avatar preferences shared by sidebar and chat;
- `ADMIN_EMAILS` bootstrap grants with concurrency-safe demotion guardrails;
- versioned SystemSettings chat overrides resolved for each new chat request;
- retirement of the nested FX modal after the page tab reaches parity.

No bootstrap or legacy storage migration is to be reintroduced. The current canonical-only S05 behavior is a deliberate product decision.

## Dependency order

1. **Shared backend contracts:** profile patch/avatar fields, serializers, both user adapters, validation, tests.
2. **Admin authority:** normalized whitelist, auth-time promotion, paged users port, guarded role service, IAM/deployment docs, endpoint tests.
3. **System chat settings:** versioned schema/adapters, merge service, provider pass-through, admin settings response/update, tests.
4. **Shared frontend infrastructure:** authenticated profile context, API clients/types, sidebar Settings/Admin entries, i18n keys.
5. **Settings route:** static Suspense/query shell, General and Avatar tabs, then Chatbot and FX tabs.
6. **Admin route:** gate, paged matrix, role mutation, shared user-settings editor.
7. **Cleanup/integration:** remove `FxRatesPanel` and nested modal entry after parity; full suites, typecheck, build, generated-route and stale-copy checks.

Each slice begins with failing focused tests and ends green. Backend contracts land before frontend consumers; FX cleanup lands last.

## File ownership

### Backend

- `app/ports/users.py`, `adapters/{memory,dynamodb}/users.py`: avatar schema, explicit patch semantics, cursor page, field-only writes.
- `app/services/admin_user_service.py` (new): whitelist promotion and protected role changes; memory/Dynamo collaborators stay behind ports.
- `app/core/config.py`, `core/deps.py`: parsed `ADMIN_EMAILS`, auth promotion, chat runtime composition.
- `app/ports/admin.py`, `adapters/memory/admin.py`, `adapters/dynamodb/settings.py`: versioned nullable chat overrides.
- `app/services/chat_settings_service.py` (new): validation, defaults/effective merge, model list.
- `app/ports/llm.py`, `adapters/llm/{openai_compat,fallback,factory}.py`, `services/llm/{chat_service,orchestrator}.py`: runtime model/fallback/parameter threading.
- `app/api/auth.py`, `app/api/admin.py`: exact public contracts in the handoff.
- corresponding fake and unit-test modules.

### Frontend

- `components/auth/AuthProfileProvider.tsx` (new), `lib/use-auth-profile.ts`, `components/Providers.tsx`, `AppShell.tsx`, `ChatWidget.tsx`: one profile controller and immediate saved-profile propagation.
- `lib/settings-api.ts`, `lib/admin-api.ts` (new): authenticated typed clients and error normalization.
- `app/settings/page.tsx`, `components/settings/*`: static settings route and four tabs.
- `app/admin/page.tsx`, `components/admin/*`: admin gate/matrix/editor.
- `components/sidebar/*`, `lib/i18n.ts`: navigation gates and translated chrome.
- `UserSettingsModal.tsx`: quick local Appearance/Language controls plus link to `/settings`; remove Currency/FX ownership.
- `components/currency/FxRatesPanel.tsx` and its test: delete only after `settings/FxTab` parity tests pass.

### Deployment/docs

- `backend/.env.example`, `deploy/eb-deploy.md`, sprint-12 `RUNBOOK.md`: `ADMIN_EMAILS` and optional LLM defaults.
- `infra/cloudformation.yml`, `infra/iam/eb-instance-policy.json`: EB `dynamodb:TransactWriteItems` permission.
- `infra/cloudformation-lab.yml` needs no resource/schema change; document its external `LabInstanceProfile` permission requirement.

## Cross-slice gates

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q

Set-Location ..\frontend
npm test
npx tsc --noEmit
npm run build
Test-Path out/settings/index.html
Test-Path out/admin/index.html
```

Also run `git diff --check`, ensure test counts do not fall accidentally, inspect the lockfile for unintended dependency churn, and search for removed `FxRatesPanel` imports and any reintroduced bootstrap/legacy-migration code.

## Acceptance map

| Item | Required evidence |
|---|---|
| BL-023 | static query-tab shell; signed-out state; General/avatar round trips; both adapter mappings; shared avatar update |
| BL-024 | whitelist parsing/promotion; 401/403; opaque pagination; role/settings mutations; whitelist/self/last-admin/concurrency guards; admin UI gate |
| BL-025 | versioned raw/default/effective settings; null fallback; validation; next-request behavior; provider parameter tests; admin tab |
| BL-026 | user/admin FX views; retained-data 502 behavior; refresh success; old modal and entry point removed |

## Non-goals

No user deletion, disable/invite/audit log, uploaded avatar, live provider-model enumeration, per-user LLM parameters, prompt playground, new FX API/history/schedule, searchable/sorted Dynamo user directory, server-rendered auth, Next middleware, storage migration, feature dependency, commit, merge, or backlog status update.

Detailed contracts, error shapes, concurrency rules, accessibility behavior, and the test matrix are authoritative in `ARCHITECT_HANDOFF.md`. Research evidence and consequences are in `RESEARCH.md`.
