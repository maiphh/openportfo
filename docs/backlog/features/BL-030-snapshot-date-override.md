# BL-030 — Snapshot manual date override for testing

| Field | Value |
|-------|-------|
| **ID** | `BL-030` |
| **Title** | Snapshot job accepts manual `date` override (today/yesterday via Lambda console) |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Implementer |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | FR-J4 snapshot job; BL-014 charts (needs history); sprint-10-jobs, sprint-12-deploy |
| **Created** | 2026-09-04 |
| **Ready date** | 2026-09-04 |
| **Done date** | 2026-09-04 |

---

## 1. Problem / user value

Daily snapshots hardcode `date = UTC today`, so manual QA cannot backfill yesterday/history to exercise the BL-014 chart + daily-PnL heatmap. AWS console Test only creates today.

---

## 2. User story

As an **operator testing deploys**, I want **to invoke `{"job":"snapshot","date":"YYYY-MM-DD"}` from Lambda console/CLI**, so that **I can create today or yesterday snapshots on demand**.

---

## 3. Scope

### In scope

- `handler({"job":"snapshot","date":"YYYY-MM-DD"})` → snapshot for that date.
- `run_snapshot_job(ctx, date_override="YYYY-MM-DD")` param.
- Strict `YYYY-MM-DD` validation; invalid → clear `ValueError`, no writes.
- Omitted/empty `date` → existing behavior (UTC today); existing EventBridge `{"job":"snapshot"}` unchanged.
- Docs: `lambda_entry` docstring + `infra/lambda/README` manual invoke example.

### Out of scope

- Admin UI button / `POST /api/admin/jobs/snapshot/run`.
- News/price job date overrides.
- Future-date blocking (allow any valid calendar date for test flexibility).
- Changing scheduled cron expressions.

---

## 4. Behaviour

### Happy path

1. Operator invokes Lambda with `{"job":"snapshot","date":"2026-09-03"}`.
2. Job writes per-user `SnapshotRecord(date="2026-09-03")` → Dynamo `sk=SNAP#2026-09-03` + `S3 snapshots/userId={id}/dt=2026-09-03/part.json` with `payload.date` matching.
3. `JobRun.counts.date` equals override; response dict carries it.

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| No `date` / empty | UTC today (current behavior) |
| `date: "2026-13-40"` / `"yesterday"` / non-string | `ValueError("event.date must be YYYY-MM-DD")`, no snapshot/S3/JobRun writes from handler path (fail fast before `run_snapshot_job`) |
| `run_snapshot_job(ctx, date_override="bad")` direct | Same `ValueError`, no writes |
| Disabled `jobs.snapshot` + override | Still `skipped`, counts.date = requested date |
| Retry same date | Idempotent overwrite (existing semantics) |

---

## 5. Acceptance criteria

- [ ] **AC1** `handler({"job":"snapshot","date":"<valid>"}, ctx)` writes Dynamo + S3 for that date; `counts.date` and payload `date` match override.
- [ ] **AC2** Invalid `date` raises `ValueError` with `YYYY-MM-DD` message and writes nothing.
- [ ] **AC3** Omitted `date` keeps UTC-today behavior; scheduled `{"job":"snapshot"}` unaffected.
- [ ] **AC4** Focused + full backend suites pass.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | Dynamo `openportfo-snapshots` (`userId` / `SNAP#date`) + S3 `snapshots/userId={id}/dt={date}/part.json` — same keys, date param only |
| New / changed APIs | None (Lambda event shape only) |
| Auth required? | N/A (jobs use `AUTH_MODE=fake` + IAM role) |
| Caching / freshness | `force_refresh=False` unchanged |
| Jobs / schedules | EventBridge inputs unchanged; manual invoke adds optional `date` |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Infra / jobs | `backend/app/jobs/snapshot_job.py`, `backend/app/jobs/handler.py`, `backend/app/jobs/lambda_entry.py` (docstring) |
| Docs / tests | `backend/tests/unit/jobs/test_jobs.py`, `infra/lambda/README.md` |

---

## 8. Dependencies & risks

- Depends on: existing snapshot job + Dynamo/S3 adapters.
- Risk: manual override overwrites a real day — accepted (same idempotent overwrite as retry); schedules never send `date`.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Block future dates? | resolved | No — allow any valid `YYYY-MM-DD` for flexibility |
| 2 | Admin UI button? | resolved | Out of scope; Lambda console/CLI only |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-09-04 | `apply this` date-override request | Allocated BL-030, Lambda-event-only scope |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach:
- PR / branch:
- Verification:
