# BL-006 — Cognito Hosted UI (replace token paste)

| Field | Value |
|-------|--------|
| **ID** | `BL-006` |
| **Title** | Cognito Hosted UI sign-in / callback / logout |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | `docs/prd/auth-cognito.md`; sprint-02 |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | 2026-08-19 |

---

## 1. Problem / user value

Portfolio (and other gated APIs) currently paste a Bearer token into `artryx.accessToken`. That is a lab gate, not a product. Users need **Sign in / Sign out** via **Cognito Hosted UI** (email + optional Google) and the app must send the **ID token** to FastAPI.

---

## 2. User story

As an **investor**, I want to **sign in with Cognito (and sign out)**, so that **portfolio, watchlist, news, and FX work without pasting JWTs**.

---

## 3. Scope

### In scope

- Follow **`docs/prd/auth-cognito.md` Option A — Hosted UI + PKCE**
- Env (public): `NEXT_PUBLIC_COGNITO_DOMAIN`, `NEXT_PUBLIC_COGNITO_CLIENT_ID`, `NEXT_PUBLIC_COGNITO_REGION`, `NEXT_PUBLIC_APP_URL` (callback origin)
- **Sign in** → Cognito `/oauth2/authorize` (`response_type=code`, `openid email profile`, PKCE S256)
- Static-export-safe **`/auth/callback/`** client page: read `code`, exchange at Cognito `/oauth2/token`, store **ID token** in `artryx.accessToken` (existing key), then `GET /api/auth/me`, redirect home or `?next=`
- **Logout** → clear storage → Cognito `/logout?client_id&logout_uri`
- **UserMenu**: name/email from `/api/auth/me` (not `MOCK_USER`); Sign in vs Logout
- Remove token-paste panel from `/portfolio` when Cognito env is configured
- **Local fallback:** if Cognito public env is missing, keep the existing paste gate (dev without a pool)
- Unit tests for PKCE helper, callback error states, token storage

### Out of scope

- FastAPI register/login (forbidden by PRD)
- Amplify Auth UI kit (Option B)
- Refresh-token silent rotate (nice-to-have: store refresh if returned; not required for MVP if ID token lifetime is enough for demo)
- Changing FastAPI JWT verifier

---

## 4. Behaviour

### Happy path

1. User clicks **Sign in**.
2. Cognito Hosted UI (email or Google).
3. Redirect `/auth/callback/?code=...`.
4. App exchanges code (PKCE), stores ID token, loads profile, lands on `/` or `next`.
5. Authenticated API calls use `Authorization: Bearer <id_token>`.
6. **Logout** clears token and returns to markets.

### Edge cases

| Case | Behaviour |
|------|-----------|
| Missing Cognito env | Local paste fallback; no broken Sign in URL |
| Callback error / denied | Error message + retry Sign in |
| Exchange fails | Do not store token; show error |
| `/api/auth/me` 401 | Clear token; Sign in |
| Static export | Callback is a client page; `trailingSlash` compatible (`/auth/callback/`) |

---

## 5. Acceptance criteria

- [x] **AC1** With Cognito env set, user can complete Hosted UI login and see their profile in UserMenu.
- [x] **AC2** Portfolio loads with the stored ID token (no paste UI).
- [x] **AC3** Logout clears token and Cognito session (Hosted UI logout).
- [x] **AC4** Without Cognito env, paste fallback still works for local/fake auth.
- [x] **AC5** Callback works under `output: "export"` + `trailingSlash`.
- [x] **AC6** PKCE verifier never put in the URL; used only at token exchange.
- [x] **AC7** Unit tests for helpers + callback failure paths.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| IdP | Cognito User Pool Hosted UI |
| Token | ID token in `artryx.accessToken` |
| Profile | `GET /api/auth/me` |
| Backend | Unchanged verifier |

---

## 7. Affected surfaces

| Layer | Paths |
|-------|--------|
| Frontend | `UserMenu`, portfolio auth gate, `lib/auth.ts`, new `lib/cognito.ts`, `app/auth/callback/page.tsx` |
| Backend | None |
| Docs | README env notes |

---

## 8. Dependencies & risks

- Pool/callback URLs must include `http://localhost:3000/auth/callback/` (slash)
- Static export: **no** Next Route Handler for token exchange — browser talks to Cognito token endpoint (CORS is allowed for public clients)

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Hosted UI vs Amplify | resolved | Hosted UI + PKCE (PRD Option A) |
| 2 | Token key | resolved | Keep `artryx.accessToken` (ID token) |
| 3 | No-env local | resolved | Keep paste fallback |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Replace paste | Cognito Hosted UI; fallback if env missing |

---

## 11. Implementation notes

- Approach: Option A Hosted UI + PKCE S256 in the browser. `lib/cognito.ts` builds `/oauth2/authorize` and `/logout`, keeps the verifier in `sessionStorage` (`artryx.pkce`), and exchanges `code` at Cognito `/oauth2/token` (no Next route handler). ID token is written to existing `artryx.accessToken`. Client page `app/auth/callback/page.tsx` reads the query after mount (`trailingSlash` → `/auth/callback/`). `UserMenu` loads name/email from `GET /api/auth/me` (no `MOCK_USER`). `AuthGate` hides paste when Cognito public env is set and keeps the BL-001 paste fallback otherwise.
- PR / branch: `feat/BL-006-cognito-hosted-ui`
- Verification: `cd frontend; npx vitest run lib/cognito.test.ts lib/auth.test.ts app/auth/callback/page.test.tsx components/auth/AuthGate.test.tsx components/UserMenu.test.tsx`. Full `npx vitest run` in `frontend/`.
### Current implementation note (Sprint 05)

The canonical auth/PKCE keys are now `openportfo.accessToken` and
`openportfo.pkce`; historical `artryx.*` references below document the prior
release and its compatibility migration.
