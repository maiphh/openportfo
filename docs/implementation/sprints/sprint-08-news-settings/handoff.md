# Handoff — Sprint 08 — News read

## Status
- [x] Done

## Filter rules (locked)
1. Load `user.news_keywords`
2. Optionally append symbols from holdings + watchlist
3. Keep item if needle in title (case-insensitive) OR item.symbols OR item.keywords
4. If no keywords and no symbols → return recent **unfiltered**

## API
`GET /api/news?limit=50` — auth required

## No RSS HTTP in this sprint (ingest = S10)
