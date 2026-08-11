# Sprint 02 — Auth (Cognito port) + profile

| **Depends on** | 00, 01 |
| **PRD** | FR-A1–A9 (verify + profile; Cognito adapter) |

## Goal
Token verification port, profile bootstrap, `/api/auth/me`, `/api/settings`, admin dependency.

## Owns
- `ports` for TokenVerifier, UserProfileRepo
- `adapters/cognito` (real JWKS impl OK if tested with mocks)
- `tests/fakes` FakeTokenVerifier, InMemoryUserProfileRepo
- `services/auth`, `api/auth` (or api/routes_auth)
- wire router in main (document handoff)

## Out of scope
Custom password register/login endpoints

## Agent prompt
```
Sprint 02 only. Cognito behind TokenVerifier port; FakeTokenVerifier for tests.
TDD per tests.md. No holdings/portfolio. Fill handoff.
```

## Exit
Auth API tests green with fake verifier; AUTH_MODE=fake works locally.
