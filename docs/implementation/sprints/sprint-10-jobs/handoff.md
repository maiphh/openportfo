# Handoff — Sprint 10 — Jobs

## Status
- [x] Done

## Modules
- `app/jobs/context.py` — JobContext (ports only; **no ExchangeRateClient**)
- `app/jobs/news_job.py`, `price_job.py`, `snapshot_job.py`
- `app/jobs/handler.py` — Lambda-shaped dispatcher
- Ports: `rss.py`, `snapshots.py` + fakes

## Event schema (for S12)
```json
{"job": "news"}
{"job": "price"}
{"job": "snapshot"}
```

## JobRun fields
`runId`, `jobType`, `status` (success|error|skipped), `startedAt`, `finishedAt`, `message`, `counts`

## Snapshot storage key
`snapshots/userId={id}/dt={YYYY-MM-DD}/part.json`

## Tests
6 job tests green; full suite includes prior sprints
