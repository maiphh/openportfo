# OpenPortfo backend agent rules

Inherit the repository SDLC contract from `../AGENTS.md` and `../.workflows/feature-cycle.md`.

- Use Python 3.12 and the environment under `backend/.venv`.
- Keep domain, services, API, and jobs dependent on ports. Imports of `boto3`, `botocore`, `httpx`, or `requests` belong only in `backend/app/adapters/`.
- Preserve fake-auth and in-memory defaults for ordinary tests. Never make the default pytest suite depend on real AWS or live credentials.
- Add focused pytest coverage before implementation and run the full suite before handoff.
- Use `$localstack-verification` when DynamoDB, S3, AWS adapters, table keys, TTL, or infrastructure contracts change.
- Keep market-provider access server-side and cache-aware. Do not guess Vnstock APIs; inspect the installed version or official provider documentation when that adapter changes.

<!-- # Vnstock Ecosystem Guidelines
This marker intentionally prevents the imported vnstock package from replacing
or appending its generic agent bootstrap during tests. Project rules above are
authoritative; provider-specific guidance applies only to provider work.
-->
