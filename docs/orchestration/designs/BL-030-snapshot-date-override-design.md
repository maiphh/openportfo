# SA Design — BL-030: Snapshot manual date override

| Field | Value |
|-------|-------|
| **ID** | `BL-030` |
| **Title** | Snapshot job accepts manual `date` override |
| **Status** | `ready_for_implementation` |
| **Author (SA)** | SA |
| **Date** | 2026-09-04 |
| **Complexity** | `simple` |
| **Related PRD** | `docs/prd/OpenPortfo_PRD.md#8.9 FR-J4` |
| **Related Arch** | `docs/architecture-design.md#5` (EventBridge → Lambda snapshot) |
| **Feature file** | `docs/backlog/features/BL-030-snapshot-date-override.md` |

---

## 1. Context & constraints

- Problem / user value (1 paragraph, from feature file): snapshot job hardcodes UTC-today so operators cannot backfill yesterday via Lambda console to test BL-014 charts; add optional event `date`.
- Locked stack constraints:
  - No API Gateway for user APIs (Beanstalk FastAPI only)
  - No Next.js SSR (CSR/static export → S3+CloudFront)
  - No browser-direct market APIs (server-side only)
  - Cache-first pricing, on-demand FX only (admin refresh)
  - Cognito JWT verification via JWKS
  - Jobs: ports-only (no `boto3`/`httpx` in `jobs/`); `JobContext` carries repos only.

## 2. Affected surfaces

| Layer | Paths / components | Change type |
|-------|--------------------|-------------|
| Domain / services | — | none |
| Ports | — | none |
| Adapters | — | none |
| Infra / jobs | `backend/app/jobs/snapshot_job.py` | add `date_override: str \| None = None` param + `_resolve_date()` validator |
| Infra / jobs | `backend/app/jobs/handler.py` | extract `date`/`snapshot_date` for snapshot only, fail fast on invalid |
| Infra / jobs | `backend/app/jobs/lambda_entry.py` | docstring event schema update |
| Docs / tests | `backend/tests/unit/jobs/test_jobs.py` | +4 focused tests |
| Docs | `infra/lambda/README.md` | manual invoke example with `date` |

## 3. API & data model deltas

### 3.1 API (Lambda event — not HTTP)

| Method & path | Auth | Request | Response | Notes |
|---------------|------|---------|----------|-------|
| Lambda `{"job":"snapshot"}` | IAM role | unchanged | unchanged | `counts.date` = UTC today |
| Lambda `{"job":"snapshot","date":"YYYY-MM-DD"}` | IAM role | optional `date` (also accept `snapshot_date` alias) | same shape, `counts.date` = override | invalid → `ValueError` |

No FastAPI route changes. No EventBridge input changes (schedules keep sending `{"job":"snapshot"}`).

### 3.2 Data model

```
Entity: Snapshots — PK userId / SK SNAP#<date> / attrs unchanged
```

- DynamoDB: same `snapshot_to_item` path; only `record.date` differs.
- S3 layout: same `snapshot_storage_key(userId, date)`; only date segment differs.
- `payload.date` and `payload.userId` unchanged in shape.

## 4. Sequence (happy path)

```
Operator → Lambda console Test {"job":"snapshot","date":"2026-09-03"}
Lambda lambda_entry.handler → handler(event, ctx)
  → _extract_snapshot_date(event) → "2026-09-03" (validated)
  → run_snapshot_job(ctx, date_override="2026-09-03")
    → settings check → per user get_portfolio → put S3 + SnapshotRepo with date
    → JobRun(job_type=snapshot, counts.date="2026-09-03")
```

ASCII sequence:

```
1. Operator invokes Lambda with date override.
2. handler validates date via date.fromisoformat (strict YYYY-MM-DD).
3. run_snapshot_job re-validates (defense in depth) and uses override for record/S3/counts.
4. Response dict returns counts.date = override.
```

## 5. Decisions (ADR style)

| # | Context | Decision | Consequence | Alternatives rejected |
|---|---------|----------|-------------|-----------------------|
| D1 | Where to validate? | Validate in both `handler` (fail fast, no writes) and `run_snapshot_job` (direct-call safety) via shared `_resolve_snapshot_date()`-equivalent logic | Duplicate 6 lines but safe for both entry points | Handler-only (direct calls bypass) / job-only (handler would write JobRun before failing) |
| D2 | Accept `date` vs `snapshot_date`? | Accept both, `date` primary, `snapshot_date` alias, trimmed; empty string = omitted | Tolerant console UX | Strict single key (brittle for hand-typed events) |
| D3 | Invalid date error type? | `ValueError("event.date must be YYYY-MM-DD")` / `("date_override must be YYYY-MM-DD")` | Matches existing handler `ValueError` contract for bad events | Custom exception (new contract, more churn) |
| D4 | Future dates? | Allow any valid calendar date | Simplest, flexible for testing | Block future (extra logic, no product need) |
| D5 | Disabled-flag interaction? | `jobs.snapshot=False` still returns `skipped` with `counts.date` = requested date | Operator sees which date was skipped | Return today on skipped (confusing) |

## 6. Complexity assessment

- [ ] Requires choosing between ≥2 libs/patterns → Researcher needed
- [ ] Security / auth / cost-critical AWS path
- [ ] No prior port/adapter pattern to reuse
- [ ] Risk to locked decisions

**Verdict:** `simple`

**If complex, research questions:** n/a — `date.fromisoformat` validation + existing idempotent put path.

## 7. Handoff to Implementor

### File ownership

- Allowed to edit: `backend/app/jobs/snapshot_job.py`, `backend/app/jobs/handler.py`, `backend/app/jobs/lambda_entry.py`, `backend/tests/unit/jobs/test_jobs.py`, `infra/lambda/README.md`
- Must NOT edit (owned by other active sprint/BL): `backend/app/adapters/**`, `backend/app/ports/**`, `backend/app/api/**`, `infra/cloudformation*.yml`, frontend

### TDD order

1. Test: `handler({"job":"snapshot","date":"2026-09-03"})` writes `snaps.get("u1","2026-09-03")` + S3 key + `counts.date` (fails: date ignored).
2. Implement: `_resolve` + `date_override` plumbing in `snapshot_job.py` + `handler.py`.
3. Test: invalid date (`"not-a-date"`, `"2026-13-01"`) raises `ValueError`, zero storage/snapshot writes.
4. Test: omitted date keeps today behavior; `snapshot_date` alias works.
5. Docs: `lambda_entry` docstring + `infra/lambda/README` example.

### Out-of-scope guardrails

- No `boto3`/`httpx` in jobs; no adapter/port changes.
- No new HTTP route; no CloudFormation change; no frontend change.
- Keep `force_refresh=False`; keep per-user isolation + single aggregate JobRun.

## 8. Acceptance criteria checklist (copy from feature file)

- [ ] AC1: `handler({"job":"snapshot","date":"<valid>"}, ctx)` writes Dynamo + S3 for that date; `counts.date` and payload `date` match override.
- [ ] AC2: Invalid `date` raises `ValueError` with `YYYY-MM-DD` message and writes nothing.
- [ ] AC3: Omitted `date` keeps UTC-today behavior; scheduled `{"job":"snapshot"}` unaffected.
- [ ] AC4: Focused + full backend suites pass.

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Manual override clobbers prod day | Same idempotent overwrite as retry; schedules never send `date`; document as operator-only |
| Timezone confusion (UTC vs ICT) | Document: override is literal `YYYY-MM-DD` string, no TZ conversion; job `started_at` stays UTC now |

## 10. Research linkage (if any)

- Research doc: n/a (simple)

---

**SA sign-off:** _ready_for_implementation_ when checklist + TDD order complete.
