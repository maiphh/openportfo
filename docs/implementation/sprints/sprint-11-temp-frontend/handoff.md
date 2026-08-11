# Handoff — Sprint 11 — Temp frontend

## Status
- [x] Done

## Location
`frontend-temp/` — Vite + vanilla JS only (no backend changes)

## How to run
See `frontend-temp/README.md`

## Manual QA checklist
- [x] Structure: Health, Me, Holdings, Watchlist, Portfolio, FX, News, History, Admin
- [x] Token paste + sessionStorage (`fake:<userId>`)
- [x] FX fail path surfaces HTTP status + body (previous rates in `body.rates` on 502)
- [ ] Live browser QA against running API (operator)

## Notes
- CORS already allows localhost:5173 from Sprint 00 settings
- Admin requires profile role admin (not settable in UI)
