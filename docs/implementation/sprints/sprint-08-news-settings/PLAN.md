# Sprint 08 — Detailed Plan: News read + keyword filter

| | |
|--|--|
| **ID** | S08 |
| **Depends on** | S02 (S03 optional for symbol filter) |
| **Parallel with** | S07, S09 |
| **PRD** | M8, FR-N1–N2 (ingest = S10) |

---

## 1. Objective

Read news from NewsRepo; filter by user keywords and optionally holding/watchlist symbols. **No RSS HTTP** in this sprint (seed via fake/repo for tests).

---

## 2. Port NewsRepo

```
list_recent(limit: int) -> list[NewsItem]
put(item: NewsItem) -> None
```

### NewsItem fields
`id`/`hash`, `title`, `url`, `source`, `published_at`, `symbols[]`, `keywords[]`, `date` (YYYY-MM-DD)

---

## 3. API

`GET /api/news?limit=50`  
- Auth required  
- Filtered list for current user  

### Filter algorithm (locked)

1. Load `user.news_keywords`  
2. Optionally load symbols from holdings + watchlist (if repos available)  
3. Keep item if keyword/symbol appears in title (case-insensitive) OR in item.symbols  
4. If user has **no** keywords and **no** symbols → return **recent unfiltered** (better demo)  

---

## 4. TDD sequence

1. Seed 3 items; keyword filter keeps matches  
2. No keywords → recent unfiltered  
3. 401 without auth  

---

## 5. Out of scope

- RSS fetch, Lambda, feedparser (S10)  
- Admin RSS CRUD (S09)  

---

## 6. Agent prompt

```
Sprint 08 ONLY. News read + filter. No RSS HTTP. Seed in tests.
Do not implement Lambda jobs (S10). Fill handoff filter rules.
```

---

## 7. Exit criteria

- [ ] News API tests green  
- [ ] Filter rules documented in handoff  
