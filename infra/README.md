# OpenPortfo — AWS infra (Academy Learner Lab)

Deployable data plane + IAM for **us-east-1** (Learner Lab default).

**Local testing without AWS:** see [localstack/README.md](localstack/README.md) and root `docker-compose.yml`.

## What this stack creates

| Resource | Purpose |
|----------|---------|
| DynamoDB tables | `openportfo-*` multi-table (users, holdings, watchlist, price-cache, news, settings, fx, rss, job-runs, snapshots) |
| S3 data bucket | `history/` and `snapshots/` prefixes (app writes keys) |
| Cognito User Pool + public app client | Email sign-in; Hosted UI callbacks for localhost + CloudFront placeholder |
| EB instance role + profile | DynamoDB RW + S3 data RW + logs (no Cognito Admin APIs; JWT verify uses public JWKS) |
| Lambda jobs role | Same data plane + CloudWatch Logs |
| Optional EventBridge rules | `news`, `price`, `snapshot` only — **no FX schedule** |

Does **not** create the Elastic Beanstalk environment or upload Lambda zip (see RUNBOOK).

## Prerequisites

1. Start **AWS Academy Learner Lab** and open AWS console / CLI credentials.
2. Region: **us-east-1**.
3. CLI: `aws` configured (lab “AWS Details” → CLI credentials).

## Deploy CloudFormation

```bash
# From repo root
aws cloudformation deploy \
  --region us-east-1 \
  --stack-name openportfo-data \
  --template-file infra/cloudformation.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ProjectPrefix=openportfo
```

Capture outputs:

```bash
aws cloudformation describe-stacks \
  --region us-east-1 \
  --stack-name openportfo-data \
  --query "Stacks[0].Outputs" \
  --output table
```

Important outputs:

- `DataBucketName` → `DATA_BUCKET`
- `CognitoUserPoolId` → `COGNITO_USER_POOL_ID`
- `CognitoAppClientId` → `COGNITO_APP_CLIENT_ID`
- `EBInstanceProfileName` → EB environment configuration
- `LambdaExecutionRoleArn` → Lambda function role

### Enable EventBridge after Lambda exists

```bash
aws cloudformation deploy \
  --region us-east-1 \
  --stack-name openportfo-data \
  --template-file infra/cloudformation.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectPrefix=openportfo \
    CreateEventBridgeRules=true \
    JobsLambdaArn=arn:aws:lambda:us-east-1:ACCOUNT:function:openportfo-jobs
```

## Standalone IAM JSON

If the lab role forbids creating IAM roles via CFN, attach policies from:

- [`iam/eb-instance-policy.json`](iam/eb-instance-policy.json) — replace `REPLACE_WITH_DATA_BUCKET`
- [`iam/lambda-execution-policy.json`](iam/lambda-execution-policy.json)

Also attach managed EB policies to the instance role (WebTier etc.) as needed.

## Key schemes (summary)

See sprint handoff for full mapping. Locked logical keys:

| Entity | PK | SK |
|--------|----|----|
| Users | `userId` | — |
| Holdings | `userId` | `HOLD#{assetType}#{symbol}` |
| Watchlist | `userId` | `WATCH#{assetType}#{symbol}` |
| PriceCache | `{assetType}#{symbol}` (`pk`) | — |
| News | `date` (YYYY-MM-DD) | `source#{hash}` |
| Settings | `SETTINGS` | `GLOBAL` |
| FX | `FX` | `LATEST` |
| RSS | `RSS` | `sourceId` |
| JobRuns | `JOB#{type}` | `runAt` ISO + `#runId` |
| Snapshots | `userId` | `SNAP#YYYY-MM-DD` |

S3:

```
s3://{DATA_BUCKET}/history/{assetType}/{assetId}/{range}.json
s3://{DATA_BUCKET}/snapshots/userId={id}/dt={YYYY-MM-DD}/part.json
```

## Next steps

1. Deploy EB API — `deploy/eb-deploy.md`
2. Package Lambda — `infra/lambda/`
3. Athena sample — `docs/implementation/sprints/sprint-12-aws-deploy/athena-sample.sql`
4. Full runbook — `docs/implementation/sprints/sprint-12-aws-deploy/RUNBOOK.md`
