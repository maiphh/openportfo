OpenPortfo data / SQL

There is no large downloaded dataset. Market prices come from CoinGecko and
vnstock at run time. Daily portfolio snapshots are written by the application
to S3 and queried with Athena.

athena-sample.sql
  Creates database openportfo, external table portfolio_snapshots_raw on
  s3://openportfo-data-databucket-bnfamm6trgmo/snapshots/, and demo SELECT
  statements. File size is under 5 MB, so no data.txt download link is needed.

Do not put AWS credentials in this folder.
