# Handoff — Sprint 02 — Auth

## Status
- [x] Not started
- [x] In progress
- [x] Done

## Ports / modules added
- `backend/app/ports/auth.py` — `Claims`, `TokenVerifier` Protocol, `UnauthorizedError`
- `backend/app/ports/users.py` — `UserProfile`, `UserProfileRepo` Protocol, `Role`
- `backend/app/adapters/cognito/jwt_verifier.py` — `CognitoJwtVerifier` (RS256 + JWKS; injectable `jwks_fetcher` for unit tests)
- `backend/app/adapters/cognito/__init__.py`
- `backend/tests/fakes/auth.py` — `FakeTokenVerifier`
- `backend/tests/fakes/users.py` — `InMemoryUserProfileRepo`
- `backend/app/services/auth_service.py` — `AuthService` (verify + bootstrap + settings)
- `backend/app/api/auth.py` — routes + camelCase profile serialization
- `backend/tests/unit/api/test_auth.py` — unit + API + Cognito mock JWKS tests

## Fake token format (locked for S11)
| Rule | Value |
|------|--------|
| Form | `fake:<userId>` |
| Example | `Authorization: Bearer fake:alice` → `Claims(sub="alice")` |
| Reject | empty string, missing `fake:` prefix, `fake:` with empty userId → `UnauthorizedError` |
| Optional maps | `FakeTokenVerifier(emails={userId: ...}, names={userId: ...})` |
| **Role** | **Always** from `UserProfileRepo`, never from token string |
| Admin seed | `repo.set_role(user_id, "admin")` after profile exists |

## Profile JSON shape (API)
```json
{
  "userId": "alice",
  "email": "alice@example.com",
  "name": "Alice",
  "role": "user",
  "newsKeywords": [],
  "emailOptIn": false,
  "preferredCurrency": "USD",
  "createdAt": "2026-08-09T12:00:00+00:00",
  "updatedAt": "2026-08-09T12:00:00+00:00"
}
```
Defaults on first `get_or_create`: `role=user`, `newsKeywords=[]`, `emailOptIn=false`, `preferredCurrency=USD`.

## API routes added
| Method | Path | Auth | Behaviour |
|--------|------|------|-----------|
| GET | `/api/auth/me` | Bearer | Bootstrap profile if missing; return profile JSON |
| PUT | `/api/settings` | Bearer | Body (partial, camelCase): `newsKeywords`, `emailOptIn`, `preferredCurrency` |

Errors: `401` / `403` with `{"detail":"..."}`.  
**No** `POST /auth/register` or `POST /auth/login`.

## AUTH_MODE wiring
| `AUTH_MODE` | TokenVerifier | UserProfileRepo (current) |
|-------------|---------------|---------------------------|
| `fake` (default) | `FakeTokenVerifier` from `tests.fakes.auth` | Process-local `InMemoryUserProfileRepo` |
| `cognito` | `CognitoJwtVerifier` (region + pool_id + client_id) | Same in-memory until Dynamo sprint |

Factory: `get_token_verifier()` / `get_user_profile_repo()` in `app/core/deps.py`.  
Deps: `get_current_user` (Bearer → claims → `get_or_create`), `require_admin` (403 if `role != admin`).  
Test hook: `set_user_profile_repo(repo | None)` to isolate store.

Cognito checks: issuer `https://cognito-idp.{region}.amazonaws.com/{pool_id}`, JWKS at `{issuer}/.well-known/jwks.json`, RS256, `aud=client_id`, `exp`, prefer `token_use == "id"`.

## Env vars (already in Settings; used now)
| Var | Default | Notes |
|-----|---------|--------|
| AUTH_MODE | fake | `fake` \| `cognito` |
| COGNITO_REGION | us-east-1 | |
| COGNITO_USER_POOL_ID | empty | required when cognito |
| COGNITO_APP_CLIENT_ID | empty | aud claim |

## Shared files touched
- `backend/app/core/deps.py` — appended: verifier factory, profile repo, `get_current_user`, `require_admin`, `set_user_profile_repo`
- `backend/app/main.py` — `include_router(auth_router)`
- `backend/requirements.txt` — `PyJWT[crypto]>=2.9.0`

## How to get admin in tests
```python
from tests.fakes.users import InMemoryUserProfileRepo
from app.core.deps import set_user_profile_repo, get_user_profile_repo

repo = InMemoryUserProfileRepo()
set_user_profile_repo(repo)
# ... client.get("/api/auth/me", headers={"Authorization": "Bearer fake:u1"})
repo.set_role("u1", "admin")
# require_admin now passes for Bearer fake:u1
```

## Tests
- Command (Windows):
  ```
  cd D:\rmit\cloud\a3\backend
  .\.venv\Scripts\python.exe -m pytest -q
  ```
- Result: **40 passed** (18 prior S00+S01 + 22 Sprint 02 auth)
- Coverage: FakeTokenVerifier, InMemory get_or_create/set_role/settings, API 401/me/settings, require_admin 403/200, CognitoJwtVerifier with mocked JWKS (valid id, reject access/wrong aud/expired)

## Known gaps / deferred
- DynamoDB `UserProfileRepo` adapter (later deploy sprint) — local still uses in-memory
- `FakeTokenVerifier` / `InMemoryUserProfileRepo` imported from `tests.fakes` in `deps` for AUTH_MODE=fake (fine for lab; can move to `app.adapters.memory` later)
- Cognito Hosted UI / Google IdP are console/frontend only (documented in PRD)
- No password hashing / custom register-login (by design)

## Next sprint needs
- Sprint 03 (Holdings): use `get_current_user` / `user.user_id` for ownership; override repo in tests via `set_user_profile_repo` or `dependency_overrides`
- Fake token: always `Bearer fake:<userId>`
- Admin routes (S09): depend on `require_admin`
