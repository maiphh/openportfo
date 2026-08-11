# Sprint 10 — Components

## Jobs
- run_news_job(ctx): RssSources → fetch → keyword match → NewsRepo; JobRuns
- run_price_job(ctx): symbols from holdings/watchlist → market → PriceCache
- run_snapshot_job(ctx): per user portfolio snapshot → SnapshotRepo + ObjectStorage path snapshots/userId=…/dt=…/part.json

## Context
Dataclass of ports (DI), not boto3

## handler(event) thin wrapper for future Lambda
