# Sprint 02 — Detailed Plan: Auth (Cognito port) + profile

| | |
|--|--|
| **ID** | S02 |
| **Depends on** | S00 (S01 soft) |
| **Unblocks** | S03–S11 authenticated APIs |
| **PRD** | FR-A1–A9, D1 Cognito; `docs/prd/auth-cognito.md` |

---

## 1. Objective

Authenticate API requests via **Bearer JWT** through `TokenVerifier` port (Cognito JWKS in prod, fake in test/local). Bootstrap app **profile** via `UserProfileRepo` (in-memory fake first).

**No** custom password register/login endpoints.

---

## 2. In / out

### In
- Ports: `TokenVerifier`, `UserProfileRepo`
- Fakes: `FakeTokenVerifier`, `InMemoryUserProfileRepo`
- Adapter: `CognitoJwtVerifier` (mock JWKS in unit tests OK)
- `GET /api/auth/me`, `PUT /api/settings`
- `get_current_user`, `require_admin`
- `AUTH_MODE=fake|cognito` wiring

### Out
- POST /auth/register, /auth/login  
- Google IdP console setup (document only)  
- Holdings routes  

---

## 3. File ownership

| Path | Action |
|------|--------|
| `app/ports/auth.py`, `users.py` | Create |
| `app/adapters/cognito/jwt_verifier.py` | Create |
| `tests/fakes/auth.py`, `users.py` | Create |
| `app/services/auth_service.py` | Create |
| `app/api/auth.py` | Create |
| `app/core/deps.py`, `main.py` | **Append** only |
| `tests/unit/api/test_auth.py` | Create |

---

## 4. Port contracts

### Claims
`sub`, `email?`, `name?`, `token_use?` (prefer id token)

### TokenVerifier
`verify(token: str) -> Claims` — raises `UnauthorizedError` if invalid

### UserProfile
`user_id` (= sub), email, name, `role` (user|admin), `news_keywords`, `email_opt_in`, `preferred_currency`, timestamps

### UserProfileRepo
`get`, `get_or_create` (default role=user), `update_settings`, `set_role`

---

## 5. Fake auth convention (lock for S11)

| Mechanism | Rule |
|-----------|------|
| Token form | Document in handoff (e.g. any non-empty maps via Fake claims map) |
| Roles | Role always from **profile repo**, not token string alone |
| Admin seed | Tests call `set_role(id, "admin")` |

Recommended FakeTokenVerifier: token `fake:<userId>` → sub=userId; reject empty/invalid prefix.

---

## 6. API contracts

| Method | Path | Auth | Result |
|--------|------|------|--------|
| GET | /api/auth/me | Bearer | Profile JSON; bootstrap on first call |
| PUT | /api/settings | Bearer | Update keywords, emailOptIn, preferredCurrency |

Errors: `{"detail":"..."}` with 401/403.

---

## 7. Cognito adapter

- Issuer: `https://cognito-idp.{region}.amazonaws.com/{pool_id}`
- JWKS: `{issuer}/.well-known/jwks.json`
- Validate RS256, iss, aud=client_id, exp
- Prefer ID token (`token_use == "id"`)
- Cache JWKS with short TTL

---

## 8. TDD sequence

1. FakeTokenVerifier unit  
2. InMemory profile get_or_create  
3. API 401 without header  
4. me creates profile  
5. me idempotent  
6. PUT settings  
7. require_admin 403/200  

---

## 9. Exit criteria

- [ ] Auth tests green with fakes  
- [ ] No password hashing  
- [ ] AUTH_MODE selectable  
- [ ] handoff: fake token format + profile JSON  

---

## 10. Agent prompt

```
Sprint 02 ONLY. Ports TokenVerifier + UserProfileRepo. Fake for tests.
Routes: GET /api/auth/me, PUT /api/settings. No register/login.
Read docs/prd/auth-cognito.md. Fill handoff.
```
