# Sprint 09 — Detailed Plan: Admin settings, RSS, job runs

| | |
|--|--|
| **ID** | S09 |
| **Depends on** | S02 |
| **Parallel with** | S07, S08 |
| **PRD** | M10, FR-AD1–5 (FX refresh is S06 — do not reimplement) |

---

## 1. Objective

Admin-only APIs for **system settings**, **RSS source CRUD**, and **job run listing**. Flags/TTL consumed by S10 jobs and S04/S05 cache.

---

## 2. Ports

### SettingsRepo (singleton SETTINGS/GLOBAL)
| Field | Purpose |
|-------|---------|
| email_time | HH:MM for stretch email window |
| timezone | e.g. Asia/Ho_Chi_Minh |
| email_enabled | global kill switch |
| price_cache_ttl_minutes | cache freshness |
| jobs.news / jobs.snapshot / jobs.email | booleans |
| default_display_currency | USD/VND |

### RssSourcesRepo
CRUD: `source_id`, `name`, `url`, `enabled`  
Validate URL scheme http(s) only; **do not fetch** feed here

### JobRunsRepo
`list_recent(job_type?, limit)` — writes in S10; may return empty now

---

## 3. API (all `require_admin`)

| Method | Path |
|--------|------|
| GET, PUT | /api/admin/settings |
| GET, POST | /api/admin/rss-sources |
| PUT, DELETE | /api/admin/rss-sources/{id} |
| GET | /api/admin/job-runs |

Non-admin → **403**.

FX: `GET /api/fx/rates`, `POST /api/admin/fx/refresh` already S06 — link only in admin UI later.

---

## 4. TDD sequence

1. User → 403 on admin routes  
2. Admin GET/PUT settings  
3. RSS create/list/delete  
4. job-runs returns `[]` with 200  

---

## 5. Agent prompt

```
Sprint 09 ONLY. Admin settings + RSS CRUD + job-runs read.
require_admin everywhere. No FX refresh (S06). No job execution (S10).
```

---

## 6. Exit criteria

- [ ] Admin tests green  
- [ ] handoff: settings JSON schema for S10 job flags  
