# SA Review — BL-030: Snapshot manual date override

| Field | Value |
|-------|-------|
| **ID** | `BL-030` |
| **Reviewer (SA)** | SA |
| **Date** | 2026-09-04 |
| **Walkthrough** | n/a (small change; diff + tests below) |
| **Verdict** | `approve` |

---

## 1. AC verification

| AC | Satisfied? | Evidence (file:line or test) | Note |
|----|------------|------------------------------|------|
| AC1 override writes requested date | yes | `backend/app/jobs/snapshot_job.py:_resolve_snapshot_date` + `run_snapshot_job(ctx,date_override)`; `backend/app/jobs/handler.py:_extract_snapshot_date`; tests `test_snapshot_date_override_writes_requested_date`, `test_handler_snapshot_date_override`, `test_handler_snapshot_date_alias_snapshot_date` in `backend/tests/unit/jobs/test_jobs.py:771+` | Dynamo `SNAP#date` + S3 `snapshots/userId={id}/dt={date}/part.json`, `counts.date` matches |
| AC2 invalid date fails fast, no writes | yes | `test_snapshot_date_override_invalid_raises_and_writes_nothing` — `ValueError YYYY-MM-DD`, zero S3 keys, zero JobRuns | Both direct + handler paths |
| AC3 omitted date = today, schedules unaffected | yes | `_resolve_snapshot_date(None)` → UTC today; `_extract_snapshot_date` returns None on missing/empty; existing `{"job":"snapshot"}` tests still pass | EventBridge inputs unchanged |
| AC4 suites pass | yes | `554 passed, 5 skipped` backend; `411 passed` frontend; `frontend-build pass`; `playwright 4 passed`; `localstack-contract pass` (`.workflows/runs/latest.json`) | `ports-isolation` gate fails only on missing `rg` binary (pre-existing env, same as baseline); manual python grep shows no `boto3/httpx` in jobs/services/domain |

## 2. Architecture checks

- [x] Ports isolation (`boto3`/`httpx` only in `adapters/`)? manual python scan of `backend/app/jobs,services,domain` → `none`
- [x] Locked decisions intact (no API GW, no SSR, cache-first, Cognito JWKS)? No API/CFN/frontend change; `force_refresh=False` kept
- [x] Cost/budget impact ≤$50 narrative respected? Zero new AWS resources; same put volume per manual invoke
- [x] Security (no secrets in frontend/Git, no presigned leak)? IAM-role path unchanged; date is plain `YYYY-MM-DD` string

## 3. Code quality

- [x] Tests green + meaningful (not just `assert True`)? 4 new tests assert Dynamo row + S3 object + payload date + counts + no-write on error
- [x] File ownership respected (no edit of other BL's files)? Edited only `jobs/snapshot_job.py`, `jobs/handler.py`, `jobs/lambda_entry.py` (docstring), `tests/unit/jobs/test_jobs.py`, `infra/lambda/README.md`
- [x] Error model `{detail: ...}` + correct HTTP codes? n/a (Lambda `ValueError`, matches existing handler contract)

## 4. Issues (if request_changes)

| # | File:line | Issue | Required fix |
|---|-----------|-------|--------------|
| — | — | none | — |

## 5. Decision

- **approve:** Orchestrator may keep on `main` (small change, already on shared branch), mark backlog `done`.

## 6. Notes for Orchestrator

- Update `docs/backlog/features/BL-030-snapshot-date-override.md` Status → `done` + Done date after handoff.
- Deploy note: repackage `openportfo-jobs.zip` before console Test with `date` works live; old zips ignore `date`.
- Residual: override is literal string (UTC date, no TZ conversion); document for ICT operators.
