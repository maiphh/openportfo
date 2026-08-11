-- OpenPortfo Sprint 12 — Athena sample over portfolio snapshots
-- Prerequisites (console / one-time lab setup):
-- 1. S3 data bucket from CFN (prefix snapshots/)
-- 2. Glue database e.g. openportfo
-- 3. External table over JSON snapshots (Hive-style partitions optional)
--
-- Snapshot key layout (locked):
--   s3://{DATA_BUCKET}/snapshots/userId={userId}/dt={YYYY-MM-DD}/part.json
--
-- Example part.json fields (from snapshot_job payload):
--   userId, date, lines[], totalsByCurrency{}, fxStatus, rates{}

-- ---------------------------------------------------------------------------
-- A) Create database
-- ---------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS openportfo
COMMENT 'OpenPortfo analytics (Learner Lab)';

-- ---------------------------------------------------------------------------
-- B) External table (JSON). Adjust LOCATION bucket name after CFN deploy.
--    Using OpenX JSON SerDe; each object is one line or whole file.
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS openportfo.portfolio_snapshots (
  userId string,
  date string,
  fxStatus string,
  totalsByCurrency map<string, struct<
    marketValue:string,
    costBasis:string,
    pnl:string
  >>,
  rates map<string, string>
)
PARTITIONED BY (
  userid_part string,
  dt string
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES (
  'ignore.malformed.json' = 'true'
)
LOCATION 's3://REPLACE_WITH_DATA_BUCKET/snapshots/'
TBLPROPERTIES (
  'projection.enabled' = 'false'
);

-- If using Hive-style partitions userId=.../dt=...:
-- MSCK REPAIR TABLE openportfo.portfolio_snapshots;
-- or:
-- ALTER TABLE openportfo.portfolio_snapshots ADD
--   PARTITION (userid_part='demo-user', dt='2026-08-09')
--   LOCATION 's3://REPLACE_WITH_DATA_BUCKET/snapshots/userId=demo-user/dt=2026-08-09/';

-- ---------------------------------------------------------------------------
-- C) Simpler non-partitioned table (easiest for student demo)
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS openportfo.portfolio_snapshots_raw (
  userId string,
  date string,
  fxStatus string,
  lines array<struct<
    symbol:string,
    assetType:string,
    qty:string,
    currency:string,
    marketValue:string,
    costBasis:string,
    pnl:string,
    missingPrice:boolean
  >>
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES (
  'ignore.malformed.json' = 'true'
)
LOCATION 's3://REPLACE_WITH_DATA_BUCKET/snapshots/';

-- ---------------------------------------------------------------------------
-- D) Demo queries
-- ---------------------------------------------------------------------------

-- Latest snapshot rows (limit)
SELECT userId, date, fxStatus
FROM openportfo.portfolio_snapshots_raw
ORDER BY date DESC
LIMIT 20;

-- Count snapshots per user
SELECT userId, COUNT(*) AS snapshot_count
FROM openportfo.portfolio_snapshots_raw
GROUP BY userId
ORDER BY snapshot_count DESC;

-- Notes for demo evidence:
-- 1. Run snapshot Lambda or job once so S3 has part.json
-- 2. Run MSCK REPAIR / query portfolio_snapshots_raw
-- 3. Screenshot Athena results for architecture report
