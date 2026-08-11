# Sprint 02 — Tests

1. missing Authorization → 401
2. invalid token → 401
3. valid fake user → 200 me; profile created
4. second me → same userId (no dup)
5. PUT settings persists
6. require_admin with user role → 403
7. require_admin with admin role → pass (via dependency test or protected stub route)
