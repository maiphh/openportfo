# Sprint 02 — Components

## Port TokenVerifier
`verify(token: str) -> Claims(sub, email, name: str|None)` raise Unauthorized

## Adapter CognitoJwtVerifier
JWKS URL from pool id/region; validate iss, aud=client_id, exp, RS256

## FakeTokenVerifier
e.g. token `user-<id>` or `admin-<id>` → claims; else reject

## Port UserProfileRepo
get, get_or_create(sub, email, name), update_settings, set_role

## Service
resolve user from Authorization header; bootstrap profile role=user default

## API
- GET /api/auth/me
- PUT /api/settings { newsKeywords, emailOptIn, preferredCurrency }

## Deps
get_current_user, require_admin
