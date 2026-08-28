# OpenPortfo agent contract

For any request that changes or builds the product, read and follow [`.workflows/feature-cycle.md`](.workflows/feature-cycle.md). Treat it as the authoritative, tool-neutral SDLC loop. Explanations, diagnosis-only requests, and read-only reviews do not trigger implementation.

Run [`.workflows/verify.ps1`](.workflows/verify.ps1) before declaring implementation complete. Use the repository skills when their trigger matches:

- `$playwright-verification` for browser-visible behavior.
- `$localstack-verification` for DynamoDB, S3, AWS adapters, or infrastructure.

Preserve the architecture constraints in `docs/architecture-design.md`: Next.js static CSR, FastAPI on Elastic Beanstalk, ports/adapters isolation, server-side market providers, Cognito JWT, and the stated AWS budget. Never deploy, push, merge, delete shared cloud resources, or mutate real AWS unless the user's feature instruction explicitly authorizes that action.

Keep generated verification evidence under `.workflows/runs/`; it is intentionally untracked. A handoff must name the acceptance criteria satisfied, commands run, results, and any remaining risks.
