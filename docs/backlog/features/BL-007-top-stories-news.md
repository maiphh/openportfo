# BL-007 — TopStories from real news API (no mock)

| Field | Value |
|-------|--------|
| **ID** | `BL-007` |
| **Title** | Markets Top Stories uses `GET /api/news` |
| **Priority** | `P1` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | BL-004 deferred mock headlines; sprint-08 news |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |

---

## 1. Problem / user value

`TopStories` still renders `TOP_STORIES` from `mock-data.ts` on `/markets/*`. Users should see **real headlines** from the news service (RSS job → `GET /api/news`).

---

## 2. User story

As a **signed-in investor**, I want **live news next to the quote board**, so that **I am not reading demo headlines**.

---

## 3. Scope

### In scope

- `TopStories` fetches `GET /api/news?limit=…` (auth required today)
- Map API fields: `title`, `url`, `source`, `publishedAt`, `symbols[]`
- Tagged symbols → `AssetLink` (assetType: infer stock if 3–4 letter uppercase VN ticker else crypto if known; if unknown, skip link)
- Skeleton while loading; error + retry
- Unauthenticated: **no mock** — empty state “Sign in to see news” (or Sign in CTA after BL-006)
- Remove `TOP_STORIES` mock export once unused
- External headline opens `url` in a new tab (`rel="noopener noreferrer"`)
- Unit tests for mapping + empty/error

### Out of scope

- New public unauthenticated news API (unless FE is blocked — prefer sign-in empty state)
- Admin RSS source UI
- Changing the news job

---

## 4. Behaviour

### Happy path

1. Signed-in user on `/markets/stock` or `/crypto`.
2. Top Stories skeleton → list of real items, newest first.
3. Click headline → source URL; click symbol → detail.

### Edge cases

| Case | Behaviour |
|------|-----------|
| 401 | Sign-in empty state; **not** mock |
| Empty list | “No stories yet” |
| Missing url | Render title as text, not a broken link |

---

## 5. Acceptance criteria

- [ ] **AC1** Authenticated markets page loads news from `/api/news`, not `TOP_STORIES`.
- [ ] **AC2** Unauthenticated: no mock headlines.
- [ ] **AC3** Skeleton then live list; error + Retry.
- [ ] **AC4** `TOP_STORIES` removed if unreferenced.
- [ ] **AC5** Symbols use `AssetLink` when type can be inferred; otherwise title-only.
- [ ] **AC6** Tests cover client mapping and 401 empty path.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| API | `GET /api/news` |
| Auth | Required; 401 → empty CTA |
| Cache | Optional short session cache; not required |

---

## 7. Affected surfaces

| Layer | Paths |
|-------|--------|
| Frontend | `TopStories.tsx`, `lib/news.ts`, `mock-data.ts`, tests |
| Backend | None required |

---

## 8. Dependencies & risks

- News job must have ingested items in deployed env; local may be empty — empty state OK
- Overlap with BL-006 sign-in CTA copy

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Public news? | resolved | No; sign-in empty if 401 |
| 2 | Mock allowed? | resolved | Never |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Replace mock TopStories | Live `/api/news` |

---

## 11. Implementation notes

- Branch: `feat/BL-007-top-stories-news`
