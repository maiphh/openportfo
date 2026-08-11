# Handoff — Sprint 09 — Admin

## Status
- [x] Done

## Settings JSON schema (for S10)
```json
{
  "emailTime": "08:00",
  "timezone": "Asia/Ho_Chi_Minh",
  "emailEnabled": false,
  "priceCacheTtlMinutes": 10,
  "jobs": { "news": true, "snapshot": true, "email": false },
  "defaultDisplayCurrency": "USD"
}
```

## API (all require_admin)
- GET/PUT `/api/admin/settings`
- GET/POST `/api/admin/rss-sources`
- PUT/DELETE `/api/admin/rss-sources/{id}`
- GET `/api/admin/job-runs`

## Notes
FX refresh remains S06 (`POST /api/admin/fx/refresh`). Job execution is S10.
