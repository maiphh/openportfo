-- OpenPortfo Sprint 12 — Athena sample over portfolio snapshots
-- Live Learner Lab (us-east-1):
--   Bucket: s3://openportfo-data-databucket-bnfamm6trgmo/snapshots/
--   Database: openportfo
--   Table: portfolio_snapshots_raw
--   Results: s3://openportfo-data-databucket-bnfamm6trgmo/athena-results/
--   Saved query: openportfo-latest-snapshots
--
-- Snapshot key layout (locked):
--   s3://{DATA_BUCKET}/snapshots/userId={userId}/dt={YYYY-MM-DD}/part.json
--
-- Live part.json fields: userId, date, lines[], totalsByCurrency{}, fx{status,base,asOf,rates}

-- ---------------------------------------------------------------------------
-- A) Create database
-- ---------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS openportfo
COMMENT 'OpenPortfo analytics (Learner Lab)';

-- ---------------------------------------------------------------------------
-- B) External table matching live snapshot JSON (nested fx, not top-level fxStatus)
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS openportfo.portfolio_snapshots_raw (
  userId string,
  date string,
  lines array<struct<
    symbol:string,
    assetType:string,
    qty:string,
    currency:string,
    marketValue:string,
    costBasis:string,
    pnl:string,
    missingPrice:boolean
  >>,
  totalsByCurrency map<string, struct<
    marketValue:string,
    costBasis:string,
    pnl:string
  >>,
  fx struct<
    status:string,
    base:string,
    asOf:string,
    rates:map<string,string>
  >
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES (
  'ignore.malformed.json' = 'true'
)
LOCATION 's3://openportfo-data-databucket-bnfamm6trgmo/snapshots/';

-- ---------------------------------------------------------------------------
-- D) Demo queries
-- ---------------------------------------------------------------------------

-- Latest snapshot rows (saved in Athena as openportfo-latest-snapshots)
SELECT userId, date, fx.status AS fxStatus,
       totalsByCurrency['USD'].marketValue AS usd_value
FROM openportfo.portfolio_snapshots_raw
ORDER BY date DESC
LIMIT 20;

-- Count snapshots per user
SELECT userId, COUNT(*) AS snapshot_count
FROM openportfo.portfolio_snapshots_raw
GROUP BY userId
ORDER BY snapshot_count DESC;

-- Notes for demo evidence:
-- 1. Snapshots already exist under snapshots/userId=.../dt=.../part.json
-- 2. Athena → Query editor → workgroup primary → Saved queries → openportfo-latest-snapshots
-- 3. Screenshot Athena results for architecture report
