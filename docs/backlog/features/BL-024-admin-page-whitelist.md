# BL-024 — Admin page (user matrix) + role/settings control + env whitelist

| Field | Value |
|-------|--------|
| **ID** | `BL-024` |
| **Title** | `/admin` page with user matrix; backend user-management API; admin whitelist via env |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | |
| **Requested by** | Product |
| **Related PRD / sprint** | sprint-06; layout ref: Open WebUI admin panel |
| **Created** | 2026-08-23 |
| **Ready date** | 2026-08-23 |
| **Done date** | |

---

## 1. Problem / user value

Admins have no UI to manage users. Roles today are set only via repo internals / debug endpoint. Product wants an **admin page with a user matrix** (Open WebUI admin-panel style) to **control user roles and settings**, with **admins defined by a comma-separated email whitelist in env**.

---

## 2. User story

As an **admin**, I want **a table of all users where I can change roles and edit settings**, so that **I can govern access without touching the database**. As an **operator**, I want **admins declared via env `ADMIN_EMAILS=a@x.com,b@x.com`**, so that **admin access is bootstrapped declaratively**.

---

## 3. Scope

### In scope

**Backend:**
- **Whitelist env**: `ADMIN_EMAILS` (comma-separated, case-insensitive emails) following the existing comma-list env convention (`CORS_ORIGINS`). Semantics: on profile resolution (`get_or_create`/auth), a whitelisted email is ensured `role=admin` (promote); demotion of a whitelisted email is prevented (or re-promoted) — SA decides exact rule + whether whitelist can also demote non-whitelisted admins (recommend: whitelist is authoritative source of admin grants; DB role remains for non-whitelisted admins granted via UI).
- **User management API** (admin-only): `GET /api/admin/users` (list: userId, email, name, role, createdAt, settings slice; simple pagination or full list — SA decides), `PUT /api/admin/users/{userId}/role` (user↔admin; guard: cannot demote self if last admin, cannot demote whitelisted email), `PUT /api/admin/users/{userId}/settings` (admin edits another user's settings incl. avatar fields).
- Both adapters (Dynamo + in-memory) updated where new repo methods are needed.

**Frontend:**
- New route `/admin` (admin-gated: non-admins see 403 UI), Open WebUI admin layout: header + tab strip; **Users tab = user matrix table**: avatar (DiceBear from their seed), name, email, role dropdown (user/admin), created date, row actions (edit settings → drawer/modal with the same fields as the user's own settings).
- Later tabs (chatbot config etc.) live in Settings (BL-025) — keep tab strip extensible.
- Sidebar "Admin" entry visible only when profile.role === 'admin'.

### Out of scope

- User deletion/disable; invites; audit log; per-user permissions beyond role.

---

## 4. Behaviour

### Happy path

1. Whitelisted email signs in → first `/api/auth/me` resolves role=admin (promotion idempotent).
2. Admin opens `/admin` → user matrix loads.
3. Role change via dropdown → API persists → table reflects; demoting a whitelisted admin → 400 with clear message.

### Edge cases / errors

- Non-admin hits `/admin` → 403 panel (no data flash).
- Empty whitelist env → no promotions; existing DB admins keep working.
- Last-admin self-demotion → blocked with message.

---

## 5. Acceptance criteria

- [ ] `ADMIN_EMAILS` env promotes matching emails to admin on sign-in (unit tested, case-insensitive, whitespace-tolerant).
- [ ] `GET /api/admin/users` + role/settings update endpoints work admin-only (403 for user, 401 anonymous) — pytest coverage.
- [ ] `/admin` page renders user matrix for admins; role changes persist; guard rails enforced.
- [ ] Unit tests: BE endpoints + whitelist semantics; FE table render, gating, role change flow.
- [ ] Suites green (pytest + vitest).

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | `UserProfileRepo` (Dynamo/in-memory) + `ADMIN_EMAILS` env |
| New / changed APIs | `GET /api/admin/users`, `PUT /api/admin/users/{id}/role`, `PUT /api/admin/users/{id}/settings` |
| Auth required? | admin |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | new `app/admin/page.tsx`, `components/admin/*`, sidebar admin entry |
| Backend API | `app/api/admin.py` (+ new user routes), `app/core/config.py` (ADMIN_EMAILS), role resolution in `get_current_user`/`get_or_create` path |
| Domain / services | `UserProfile` extension if needed; whitelist helper |
| Docs / tests | pytest: whitelist + admin users API; vitest: admin page |

---

## 8. Dependencies & risks

- Depends on: BL-020 (sidebar admin entry), BL-023 (settings field contracts incl. avatar).
- Risks: role-promotion race on sign-in (idempotent upsert mitigates); Dynamo adapter update complexity.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Whitelist demotion policy | open | SA decision |
| 2 | Pagination for users list | open | SA decision |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-23 | Batch created | — |
