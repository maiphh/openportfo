# Sprint 09 — Components

## SettingsRepo
get_global, put_global (emailTime, timezone, emailEnabled, priceCacheTtlMinutes, jobs flags)

## RssSourcesRepo
CRUD name, url, enabled

## JobRunsRepo
list recent (empty until jobs)

## API
GET/PUT /api/admin/settings  
GET/POST/PUT/DELETE /api/admin/rss-sources  
GET /api/admin/job-runs  

All require admin.
