---
name: localstack-verification
description: Start, inspect, and verify OpenPortfo's local DynamoDB and S3 integration through LocalStack when changes affect AWS adapters, table keys, TTL, S3 storage, CloudFormation, jobs, or local cloud configuration. Do not use LocalStack results as proof that unsupported Cognito, Lambda, EventBridge, or Elastic Beanstalk behavior works.
---

# LocalStack verification

LocalStack is the repository's safe AWS integration target. It exposes DynamoDB and S3 at `http://localhost:4566`; Cognito stays in fake mode.

1. Read `infra/localstack/README.md`, `docker-compose.yml`, and the affected adapter or infrastructure file.
2. Start the service from the repository root with `docker compose up -d --wait --wait-timeout 120 localstack`. The ready hook may finish creating resources just after the container health check; retry the contract probe briefly when it reports a missing resource during startup.
3. Run the read-only contract probe with the backend virtual environment:

   ```powershell
   backend\.venv\Scripts\python.exe .agents\skills\localstack-verification\scripts\verify_localstack.py
   ```

4. Point application interactions at LocalStack explicitly with dummy credentials, `DYNAMODB_ENDPOINT_URL=http://localhost:4566`, and `S3_ENDPOINT_URL=http://localhost:4566`. Keep `AUTH_MODE=fake`. Confirm the endpoint before every write so a local test cannot mutate real AWS.
5. Exercise the affected adapter through its public port or service where practical, then inspect the resulting DynamoDB item or S3 object. Use a unique test key and remove only that exact key after verification.
6. Re-run the contract probe and the relevant pytest tests. Report the endpoint, resources checked, test command, and result.

Do not run `docker compose down -v`, delete tables or buckets, purge shared data, or invoke real AWS without explicit user authorization. The existing `RUN_AWS_TESTS` suite targets real AWS and is not a LocalStack substitute.
