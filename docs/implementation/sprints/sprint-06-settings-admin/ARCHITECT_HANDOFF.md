# Sprint 06 — authoritative architect handoff

**Scope:** BL-023, BL-024, BL-025, BL-026 only  
**Verdict:** **APPROVED FOR IMPLEMENTATION**  
**Authority:** this handoff overrides examples or recommendations in the four backlog files and `PLAN.md` where they differ.  
**Current-state constraint:** do not add a startup bootstrap, old-name compatibility, or storage migration. The canonical-only S05 implementation is the product decision.

## 1. Repository facts and boundaries

- Frontend is Next 15.5/React 19/Tailwind 4 with strict TypeScript, Vitest/jsdom, `output: "export"`, and `trailingSlash: true`.
- `AppShell` currently owns one auth controller, but `ChatWidget` owns a duplicate profile request. Account pages need one shared provider so an avatar/role/settings response updates every surface immediately.
- The accepted quick-settings modal owns local theme/language/currency and nests `components/currency/FxRatesPanel.tsx`. Preserve quick preference access, but move FX to the page and reconcile signed-in currency with the profile.
- Backend already has UserProfile and SystemSettings memory/Dynamo adapters, admin settings APIs, auth dependencies, a cached env-built fallback provider, and scan iterators. Extend those seams; do not create a parallel persistence stack.
- Existing Dynamo items have no avatar/chat/version fields. This batch is lazy/backward-compatible; no table recreation or bulk migration is required.

## 2. Final product decisions

| Question | Decision |
|---|---|
| Avatar fields/styles | Raw nullable `avatarStyle`, `avatarSeed`, `avatarColor`; exact existing eight-style allowlist |
| Quick-settings fate | Retain account/theme/language/currency quick access; replace nested FX with links to `/settings`; signed-in currency writes profile API |
| Whitelist authority | Grant-only. Matching JWT email is promoted; non-matching DB admins are not auto-demoted; whitelisted users cannot be demoted |
| User pagination | Forward opaque cursor over Dynamo Scan, `limit` 1..100, no sort/snapshot promise |
| Chat parameters | primary model, fallback models, temperature, top-p, max tokens, system-prompt suffix only |
| Models source | env default/fallbacks plus stored effective values; no new live-list endpoint |
| FX system currency | Do not surface `defaultDisplayCurrency`; keep backend compatibility. User currency belongs General/quick preferences |
| FX modal | Delete after the page tab reaches tested parity |

## 3. User profile and patch contract

### 3.1 Domain and storage schema

Extend `UserProfile` with nullable raw preferences:

```py
avatar_style: Optional[str] = None
avatar_seed: Optional[str] = None
avatar_color: Optional[str] = None
```

API and Dynamo names are `avatarStyle`, `avatarSeed`, `avatarColor`. Both `profile_to_item` and `item_to_profile`, and both memory/Dynamo adapters, map all fields. Missing legacy attributes map to `None`; full item serialization omits `None`; explicit clearing uses Dynamo `REMOVE` rather than storing empty strings or Dynamo nulls.

`GET /api/auth/me` and successful settings mutations return the full profile including the three fields. `GET /api/settings` returns:

```json
{
  "newsKeywords": [],
  "emailOptIn": false,
  "preferredCurrency": null,
  "avatarStyle": null,
  "avatarSeed": null,
  "avatarColor": null
}
```

### 3.2 Explicit patch semantics

Replace the current optional-argument ambiguity with a typed `UserSettingsPatch` and an `UNSET` sentinel. Omitted means unchanged; JSON `null` clears only nullable `preferredCurrency` and avatar fields; `newsKeywords: null` and `emailOptIn: null` are invalid. The repo accepts the patch object and performs field-only updates, never a read/whole-item `PutItem` that can overwrite a concurrent role change.

Validation/normalization is shared by self-service and admin-service endpoints:

- `newsKeywords`: array, maximum 20; NFKC + trim each; 1..50 characters; reject controls; case-insensitive de-duplicate preserving first spelling; `[]` clears.
- `emailOptIn`: boolean.
- `preferredCurrency`: null or existing supported `USD|VND|EUR` normalization.
- `avatarStyle`: null or one of `notionists`, `notionists-neutral`, `adventurer-neutral`, `big-smile`, `lorelei`, `bottts`, `thumbs`, `shapes`.
- `avatarSeed`: null or NFKC/trimmed 1..64 characters, rejecting controls. Randomize in the browser with Web Crypto and save the generated text; never persist locally.
- `avatarColor`: null or `RGB`, `#RGB`, `RRGGBB`, or `#RRGGBB`; persist lowercase six-digit hex without `#` (expand three-digit form).

Malformed settings return HTTP 400 with `detail.code="validation_error"` and a field-to-message `detail.errors` object. Do not leak an input value in server logs/errors.

### 3.3 Avatar rendering

Extend frontend `AuthProfile` with the nullable camelCase fields. `UserAvatar` receives the profile directly; saved values override its current aliases. Effective fallback remains style `notionists`, seed `userId` then email, no color. Preserve the S05 URL allowlist and explicit image-error/guest fallback. A profile replacement must reset/retry the image when the effective URL changes.

## 4. Shared frontend authentication/profile state

Move the state machine from a privately instantiated hook into `components/auth/AuthProfileProvider.tsx`, mounted once inside `Providers`. `useAuthProfile()` becomes a context consumer. Add:

```ts
replaceProfile(profile: AuthProfile): void;
reloadProfile(): Promise<AuthProfile | null>;
```

`reloadProfile` must issue a request even when the token string is unchanged, abort/supersede stale work, and retain the existing 401/403 token clearing. `replaceProfile` is used after any self/admin response affecting the current user. `AppShell`, sidebar, Settings/Admin pages, quick settings, and `ChatWidget` consume the same controller. Remove ChatWidget's duplicate token/profile fetch and pass/consume the controller without changing chat-session ownership.

Add a small profile-currency synchronizer below both Auth and Currency providers. After a signed-in profile first loads or changes, a non-null `preferredCurrency` updates `CurrencyProvider` and canonical local preference. It never writes the API from an effect. Self-service saves update the returned profile and CurrencyProvider explicitly.

## 5. `/settings` static route and tabs

### 5.1 Static/export design

`app/settings/page.tsx` is a Server Component containing:

```tsx
<Suspense fallback={<SettingsPageSkeleton />}>
  <SettingsPageClient />
</Suspense>
```

Only `SettingsPageClient` calls `useSearchParams()` and `useRouter()`. Do not accept the page `searchParams` prop, call `connection()`, add middleware/route handlers, or opt into dynamic rendering. User tab clicks use `router.push('/settings?tab=...', {scroll:false})`; canonical correction uses `router.replace`. Default `general` canonicalizes to `/settings` (no query). Valid identifiers are `general`, `avatar`, `fx`, `chatbot`.

During auth hydration render a stable skeleton. Signed out renders a sign-in prompt and calls `auth.signIn('/settings' + currentSearch)`; the existing `safeNextPath` preserves a same-origin query. No protected request/form content flashes. Authenticated non-admin deep-linking `?tab=chatbot` falls back to General and replaces the URL; it never requests admin settings.

Acceptance requires a production build and `out/settings/index.html`.

### 5.2 Tab semantics and layout

At `sm+`, use a left vertical tablist and right panel. Below `sm`, the tablist becomes horizontally scrollable. Tabs are real buttons with `role=tab`, `aria-selected`, `aria-controls`, and roving `tabIndex`; panels use `role=tabpanel` and `aria-labelledby`. Arrow Up/Left and Down/Right, Home, and End move/focus tabs. Mouse selection does not steal focus elsewhere; URL hydration does not unexpectedly focus a tab.

All new shell/form/status strings go into both EN and VI dictionaries and remain covered by dictionary-completeness tests. Inline errors use `role=alert`; success uses `role=status`; forms set `aria-busy`, disable duplicate saves, associate errors/descriptions, and preserve dirty input on failure.

### 5.3 General tab

Initialize from the shared profile; fields are preferred currency, email opt-in, and keyword editor. Save one explicit patch to `PUT /api/settings`. On success call `replaceProfile(response)` and set CurrencyProvider from the returned non-null currency. On failure preserve form state. Disable Save until dirty and valid. A reset rehydrates from the latest shared profile.

The quick-settings modal remains for the accepted S05 workflow:

- theme and language remain local and immediate;
- signed-out currency remains local;
- signed-in currency is optimistic locally, calls `PUT /api/settings`, replaces the returned profile, and rolls back/show an inline error if it fails;
- remove the nested FX trigger and `FxRatesPanel` import;
- add “All settings” and “FX rates” links to `/settings` and `/settings?tab=fx`, closing the modal before navigation.

### 5.4 Avatar tab

Use the existing avatar helper/allowlist. Controls are an accessible style radio/grid, a text seed input, Web-Crypto Randomize button, optional color input plus Clear, live `UserAvatar` preview, Reset (raw nulls), and Save. Preview state is local until save. A failed save retains it. Success replaces the shared profile so sidebar, mobile topbar, quick settings, and chat update without reload.

### 5.5 FX and Chatbot visibility

FX is visible to every signed-in user. Chatbot is rendered and fetches only for `profile.role === 'admin'`. Client visibility is convenience only; backend authorization remains mandatory.

## 6. `ADMIN_EMAILS` and admin user service

### 6.1 Parsing and promotion

Add `admin_emails: str = Field(default="", alias="ADMIN_EMAILS")` and an `admin_email_set` property/helper. Split on comma, trim, casefold, discard empty segments, and de-duplicate. Every non-empty token must contain exactly one `@`, non-empty local/domain parts, and no whitespace/control characters. Invalid configuration fails Settings construction/runtime validation naming only `ADMIN_EMAILS`, never its contents.

After JWT verification and `get_or_create`, compare the verified claim email (not stale stored email). Matching profiles are atomically/idempotently promoted before `get_current_user` returns, so the first `/api/auth/me` is admin. Refresh stored verified email/name when changed. The whitelist is grant-only:

- matching users are always admin and UI/API demotion returns 400 `whitelist_admin`;
- removing an email from env does not auto-demote its DB admin role;
- UI-promoted non-whitelist admins persist;
- empty env performs no promotions;
- never return the whitelist itself to the frontend.

### 6.2 Paged list contract

`GET /api/admin/users?limit=25&cursor=...` is admin-only; limit range is 1..100. Response:

```json
{
  "items": [{
    "userId": "...", "email": "...", "name": "...", "role": "admin",
    "createdAt": "...", "updatedAt": "...",
    "newsKeywords": [], "emailOptIn": false, "preferredCurrency": null,
    "avatarStyle": null, "avatarSeed": null, "avatarColor": null,
    "roleManagedByEnv": true, "isCurrentUser": true
  }],
  "nextCursor": null
}
```

The cursor is unpadded base64url of canonical UTF-8 JSON `{ "v":1, "key":{"userId":"..."} }`. Decode strictly: maximum encoded length 2048, exact keys/version/types, non-empty userId, no extra fields; invalid returns 400 `invalid_cursor`. It wraps Dynamo `LastEvaluatedKey`/`ExclusiveStartKey`; request uses `Limit` and `ConsistentRead=True`. Promise no ordering, total count, offsets, or cross-page snapshot. In-memory mirrors forward continuation deterministically. The frontend appends pages via “Load more” and handles duplicates by `userId` defensively.

### 6.3 Mutation endpoints

- `PUT /api/admin/users/{userId}/role`, body `{ "role":"user|admin" }`, returns the full admin-list row.
- `PUT /api/admin/users/{userId}/settings`, body identical to the explicit user settings patch, returns the full row.

Unknown target is 404. Anonymous is 401 and non-admin is 403 through existing dependencies. Admin settings edits cannot mutate userId/email/name/role. If target equals current user, the frontend also calls `replaceProfile` with the returned profile portion.

### 6.4 Last-admin/self/concurrency guard

Self-demotion is allowed only when another DB admin remains. Any attempted demotion that would leave zero admins is rejected, whether self or another target. The backend is authoritative; frontend disablement is advisory.

For memory, perform count/check/mutation under one `RLock`. For Dynamo:

1. Strongly scan/project all user roles and count admins.
2. Read a dedicated Settings-table item `pk="ADMIN_ROLE_GUARD", sk="GLOBAL"` strongly; missing means version 0.
3. If count is one, return 409 `last_admin`.
4. `TransactWriteItems`: conditionally update target only if role is still admin; conditionally increment/create the guard only if its version is unchanged.
5. On transaction cancellation/conflict, re-read/recount once. Retry only with the new guard version if still safe; otherwise return `last_admin`. A second conflict returns 409 `role_conflict`.

Promotions and whitelist grants use field-only conditional/idempotent UpdateItem; all user settings writes are also field-only so they cannot overwrite roles. Add EB `dynamodb:TransactWriteItems` permission for the Users and Settings ARNs in `infra/cloudformation.yml` and `infra/iam/eb-instance-policy.json`. The lab stack has no IAM resources; deployment docs must require the equivalent existing-profile permission.

## 7. `/admin` frontend

The route is statically exported to `out/admin/index.html`. During auth hydration show a skeleton. Signed out shows sign-in; signed-in non-admin shows a 403 panel and never calls the users endpoint. Admin shows a labelled Users view with an overflow-safe semantic table: avatar, name/email, role control, created date, and Edit settings.

Keep editing as a non-modal, responsive in-flow drawer/pane associated with the row button using `aria-expanded`/`aria-controls`; on open focus its heading, on close return focus to its row button. This avoids competing with AppShell's overlay/focus/body-lock ownership. Reuse the same `UserSettingsForm` field schema/validation as Settings General+Avatar; do not duplicate rules. Row mutations have per-row busy/error states, suppress duplicate calls, update only after success, and reload/reconcile on 409. Show `roleManagedByEnv`; disable its demotion control. Localize known error codes rather than echoing arbitrary server/provider details.

Sidebar Settings is always visible. Admin is visible only when the shared profile role is admin. Add `isAdmin` to the declarative SidebarNav contract and pass it in both desktop and mobile drawer paths. Route/API enforcement must remain correct if markup is manipulated.

## 8. Versioned SystemSettings chat overrides

### 8.1 Stored schema

Add `version: int = 0` and these nullable raw fields to `SystemSettings`:

```py
chat_model: Optional[str] = None
chat_fallback_models: Optional[list[str]] = None
chat_temperature: Optional[float] = None
chat_top_p: Optional[float] = None
chat_max_tokens: Optional[int] = None
chat_system_prompt_extra: Optional[str] = None
```

Dynamo attributes are camelCase equivalents. Missing legacy fields/version map to null/version 0. `[]` for fallbacks is a meaningful explicit “no fallback”; null means env fallback. `SettingsRepo.save(settings, expected_version=...)` is optimistic: successful save increments version and conditional failure raises a typed conflict. Dynamo `get` uses `ConsistentRead=True`; legacy version-0 save condition accepts a missing version. Memory applies the same contract under a lock.

### 8.2 Environment defaults and validation

Existing env defaults remain model/fallback/max tokens. Add optional `LLM_TEMPERATURE`, `LLM_TOP_P`, and `LLM_SYSTEM_PROMPT_EXTRA`; blank means provider/no suffix. Never store/expose provider, base URL, credentials, retry/timeout, free-only, tool rounds, or immutable base prompts.

- model/fallback id: trimmed 1..200 characters, reject whitespace/control; fallbacks max 8, stable de-duplicate, remove primary duplicates.
- temperature: null or 0..2 inclusive.
- top-p: null or 0..1 inclusive.
- max tokens: null or integer 1..32768; this is an application ceiling, not a model capability promise.
- prompt suffix: null or trimmed 1..4000; blank form normalizes to null; reject controls except newline/tab.
- when `LLM_FREE_ONLY=true`, all effective primary/fallback IDs must pass the existing free-model policy; reject the save otherwise.

### 8.3 Admin API response and update

`GET /api/admin/settings` keeps every current top-level field and adds:

```json
{
  "version": 3,
  "chat": {
    "overrides": {
      "model": null, "fallbackModels": null, "temperature": null,
      "topP": null, "maxTokens": null, "systemPromptExtra": null
    },
    "defaults": {
      "model": "openrouter/free", "fallbackModels": [], "temperature": null,
      "topP": null, "maxTokens": 2048, "systemPromptExtra": null
    },
    "effective": {
      "model": "openrouter/free", "fallbackModels": [], "temperature": null,
      "topP": null, "maxTokens": 2048, "systemPromptExtra": null
    },
    "availableModels": ["openrouter/free"]
  }
}
```

`availableModels` is stable de-duplicated env default + env fallbacks + raw/effective stored IDs, filtered by the free-only floor. Do not add `/api/admin/chat/models` and do not call the provider model-list API.

`PUT /api/admin/settings` now requires top-level `version` on every write and accepts existing fields plus a nested `chat` patch. Nested omitted fields stay unchanged; explicit null clears; fallback `[]` stays explicit. It returns the same full response. A stale version returns 409 `settings_conflict`; validation returns 400 with field errors. This intentional internal API evolution updates all existing tests/callers together.

### 8.4 Runtime resolution and cache/concurrency

Create immutable `ChatRuntimeConfig`. For every new `/api/chat` request, `get_chat_service()` strongly reads SystemSettings, resolves DB raw override > env default, snapshots it, and builds the request service. Do **not** cache the merged effective config in process memory. The base authenticated HTTP provider may remain cached, but construct a lightweight `FallbackProvider` per request using effective primary/fallbacks.

Result:

- a successful settings PUT is visible to the next request across workers without process-local invalidation;
- an in-flight request keeps its immutable old snapshot;
- failed/conflicting saves change nothing;
- `set_settings_repo` clears any test-only dependency objects, but correctness does not depend on `set_market_service(None)` or cache invalidation.

Precedence is explicit request model (subject to free-only policy) > effective system primary > env primary. Effective fallback list applies to all provider calls. Extend `LlmProvider.complete`, fake providers, FallbackProvider, and OpenAI-compatible request serialization with optional `top_p`; omit null sampling fields. Runtime temperature/top-p/max-token/suffix apply to `ChatOrchestrator` calls. Append the suffix after the immutable `ORCHESTRATOR_SYSTEM` with a fixed delimiter; it never replaces the base. `AnalystAgent` retains its specialized prompt, 0.3 temperature, and 700-token bound. Provider/model rejection is sanitized and surfaced; do not silently mutate/fallback the stored config beyond the configured fallback provider behavior.

## 9. Chatbot and FX tabs

### Chatbot

Admin-only tab loads `/api/admin/settings`, shows raw overrides separately from effective/default values, uses a select/multi-select over `availableModels`, numeric inputs with range text, and prompt textarea. “Use environment default” writes null; “No fallbacks” writes `[]`. Warn that provider/model support varies and suggest changing temperature or top-p rather than both. Save includes version; on 409 preserve edits, announce conflict, and offer Reload. Never display secrets or the immutable base prompt.

### FX

Extract the non-dialog rendering into `components/settings/FxTab.tsx` while reusing `CurrencyProvider` state and `lib/fx.ts` clients. Do not create a second mount-time fetch if the provider already has data/loading. Render stored rates, `asOf`, provider, stale/error state. Only admin renders Refresh. On refresh success replace shared rates; on 502 render the response's previous rates and error while retaining the table. On 401/403 sync/reload auth; do not show an admin button to users.

After parity tests, delete `components/currency/FxRatesPanel.tsx`, its test, all imports, nested overlay state, and obsolete FX trigger copy. Do not move `defaultDisplayCurrency` into this tab; retain that existing backend field/API for compatibility only.

## 10. TDD and verification matrix

### Backend required tests

- Avatar/profile mappings: missing, set, clear, normalization in both adapters; field-only update cannot overwrite concurrent role.
- Patch matrix: omitted/null/empty/invalid for every settings field; self and admin endpoints share results.
- Whitelist: commas/whitespace/case/de-dupe/empty/invalid; first-request promotion; idempotence; claim email change; no auto-demotion; whitelist demotion blocked.
- Admin auth: anonymous 401, user 403, missing target 404; list schema and limit bounds.
- Cursor: first/middle/final/empty page; malformed base64/JSON/version/extra/oversize; exact LEK round trip; memory parity; no sort assumption.
- Roles: promote; safe self/non-self demote; last-admin block; two concurrent demotions; transaction conflict retry; settings write/role write interleaving.
- SystemSettings mapper: legacy missing fields/version, null, `[]`, Decimal float conversion, optimistic success/conflict.
- Chat validation: every boundary; null-to-env; raw/default/effective/available response; free-only rejection; no secrets.
- Runtime: DB > env, request model precedence, empty fallback override, next request sees save, in-flight snapshot unchanged, conflict unchanged.
- LLM port/adapters/fakes: top-p and non-null fields forwarded through fallback attempts; null omitted from HTTP JSON; specialist fixed settings preserved.
- Deployment policy assertion includes `TransactWriteItems` only where required.

### Frontend required tests

- Settings Suspense route, valid/invalid/default/admin/unauthorized deep links, push/replace calls, signed-out/hydrating no-fetch states, generated static route.
- Tab ARIA/keyboard/responsive classes; EN/VI key completeness.
- General initial/dirty/validation/save/success/error/reset; currency provider/profile propagation.
- Avatar allowlist, custom/random/reset preview, canonical payload, save/error, image URL/fallback reset, sidebar/chat immediate update.
- Shared auth provider: single `/auth/me` across shell/chat/page, forced reload, stale abort, replaceProfile, 401/403.
- Quick modal signed-in currency success/rollback, signed-out local behavior, links close modal, no nested FX.
- Admin gate/no data flash, cursor load-more/dedupe/retry, semantic rows, whitelist lock, role success/errors/409, in-flow editor focus return and shared validation.
- Chatbot raw/effective/default display, null vs `[]`, validation, save/version conflict/reload, admin-only no-fetch.
- FX user/admin render, no duplicate fetch, refresh success, 502 retained table/error, auth failure, no default system currency.
- Sidebar Settings always/Admin gated in desktop and mobile.

### Full gates and review

Run the commands in `PLAN.md`, inspect generated `/settings` and `/admin` HTML, and ensure frontend tests are not reduced merely by deleting the FX modal test. Manual deployed-browser smoke remains required before release for query deep links on the static host, Cognito return URL, mobile tab/table layouts, focus behavior, DiceBear success/failure, and real 502/admin workflows.

## 11. Acceptance mapping

| Backlog | Definition-of-done evidence |
|---|---|
| BL-023 | Sections 3–5 contracts, both adapters, shared profile propagation, static `/settings`, tab/form/avatar tests |
| BL-024 | Section 6–7 authority, pagination, transaction/IAM, APIs, route gating, concurrency tests |
| BL-025 | Section 8–9 versioned settings, effective merge, next-request semantics, provider pass-through, Chatbot UI/tests |
| BL-026 | Section 9 FX parity, user/admin/502 tests, old modal/entry removal |

## 12. Risks, non-goals, and blockers

Highest risks are whole-item Dynamo writes overwriting roles, concurrent last-admin demotion, duplicate auth/profile sources, stale multi-worker chat configuration, and static query handling without Suspense. The contracts above directly gate each risk.

No unresolved product or technical blocker remains. External research used is bounded and recorded in `RESEARCH.md`. Do not implement user deletion/disable/invites/audit, uploaded avatars, per-user LLM settings, live model enumeration, FX history/scheduling, Dynamo indexes/sorting/search, SSR auth, legacy migrations, new dependencies, or unrelated S05 cleanup. Do not change backlog status until implementation/review.
