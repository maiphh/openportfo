# BL-022 — DiceBear avatars

| Field | Value |
|-------|--------|
| **ID** | `BL-022` |
| **Title** | Generate user avatars with DiceBear |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Luna implementer |
| **Requested by** | Product |
| **Related PRD / sprint** | sprint-05; feeds BL-020 (sidebar avatar) and BL-021 (modal trigger) |
| **Created** | 2026-08-23 |
| **Ready date** | 2026-08-23 |
| **Done date** | 2026-08-23 |

---

## 1. Problem / user value

Users currently get an initials-only fallback avatar. Product wants fun, unique, deterministic avatars via **DiceBear** (https://www.dicebear.com/) — same user → same avatar every time.

---

## 2. User story

As a **user**, I want **a unique generated avatar for my account**, so that **I can recognize myself in the app**.

---

## 3. Scope

### In scope

- `lib/avatar.ts` helper: build DiceBear avatar URL from a seed (`userId` or email — must be stable) using the DiceBear HTTP API (`https://api.dicebear.com/9.x/<style>/svg?seed=…`), with chosen style + tasteful defaults (SA to pick style, e.g. `notionists` or similar neutral style).
- Wire into existing shadcn `Avatar`/`AvatarImage` (currently unused) with **initials fallback** when image fails/offline (guest users, network errors).
- Used by: sidebar avatar (BL-020) and settings modal trigger.
- Static-export safe (plain `<img>` via AvatarImage, `unoptimized` — no next/image involvement).

### Out of scope

- User-uploaded photos; style picker UI for end users; backend avatar storage.

---

## 4. Behaviour

### Happy path

1. Signed-in user → avatar URL `https://api.dicebear.com/9.x/<style>/svg?seed=<userId>` renders in sidebar.
2. Same user always gets identical avatar.

### Edge cases / errors

- Signed out → generic guest seed or initials fallback.
- DiceBear unreachable → `AvatarImage` onError falls back to initials circle (existing AvatarFallback).

---

## 5. Acceptance criteria

- [ ] Signed-in users see a deterministic DiceBear avatar keyed by stable identity.
- [ ] Graceful fallback to initials when signed out or on image load failure.
- [ ] Unit tests: URL builder determinism/params, fallback rendering.
- [ ] Suite green.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | DiceBear HTTP API (v9), no API key |
| New / changed APIs | none |
| Auth required? | no |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | new `lib/avatar.ts` (+ test), `components/ui/avatar.tsx` usage, Sidebar (BL-020) |
| Backend API | none |
| Docs / tests | avatar tests |

---

## 8. Dependencies & risks

- Depends on: none (do early — BL-020 consumes it).
- Risks: external network dependency mitigated by initials fallback; style choice subjective.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Seed = userId or email? | open | SA decision (userId preferred if populated pre-profile-fetch; email always present) |
| 2 | Style | open | SA decision |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-23 | Batch created | — |
