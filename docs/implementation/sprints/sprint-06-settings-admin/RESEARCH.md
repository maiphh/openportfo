# Sprint 06 settings/admin research

**Date:** 2026-08-23  
**Scope:** only questions that repository evidence could not settle for BL-023 through BL-026.  
**Source policy:** primary, official technical documentation only.

## Next.js 15 static export and query tabs

### Question

Can `/settings?tab=avatar` remain a static-exported App Router route while reacting to query-string tab changes and browser history?

### Sources

- [Next.js `useSearchParams`](https://nextjs.org/docs/app/api-reference/functions/use-search-params)
- [Next.js missing-Suspense diagnostic](https://nextjs.org/docs/messages/missing-suspense-with-csr-bailout)
- [Next.js `useRouter`](https://nextjs.org/docs/app/api-reference/functions/use-router)
- [Next.js static exports](https://nextjs.org/docs/app/building-your-application/deploying/static-exports)

### Consequence

`app/settings/page.tsx` stays a static Server Component and renders the smallest client subtree that calls `useSearchParams()` inside `<Suspense>`. Production builds otherwise fail for a statically rendered page. The client uses `router.push(..., { scroll: false })` for user tab selection and `router.replace` only to canonicalize invalid/default/unauthorized queries; query changes re-render the client subtree and browser Back traverses user selections. No request-time `searchParams` page prop, `connection()`, route handler, middleware, cookie, or dynamic rendering is permitted. With the repository's `output: "export"` and `trailingSlash: true`, acceptance includes `out/settings/index.html`.

## DynamoDB user pagination

### Question

What can the admin-users API promise when the current Users table has only a partition key and listing requires `Scan`?

### Sources

- [AWS: scanning tables and pagination](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html)
- [AWS: read consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html)
- [AWS: query/scan best practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-query-scan.html)

### Consequence

The API wraps `LastEvaluatedKey` in a validated opaque cursor and supplies it back as `ExclusiveStartKey`; it does not invent an offset. DynamoDB scan order is arbitrary, and even a strongly consistent scan does not provide a multi-request snapshot, so the public contract promises neither sorting nor snapshot isolation. `limit` controls evaluated items, each request uses `ConsistentRead=True`, and the frontend uses forward-only “Load more” pagination. A future sorted/searchable directory requires a new access pattern/index and is out of this batch.

## DynamoDB last-admin concurrency

### Question

Can two concurrent demotions both pass a read/count guard, and which primitive prevents that?

### Sources

- [AWS: DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)
- [AWS: `TransactWriteItems`](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html)

### Consequence

A scan followed by an ordinary update is insufficient. Dynamo role demotion uses one `TransactWriteItems` call that conditionally changes the target role and conditionally increments a dedicated guard item in the Settings table. Concurrent demotions sharing a guard version cannot both commit; the loser re-reads/recounts once and either retries or returns a conflict/last-admin result. The Elastic Beanstalk role therefore needs `dynamodb:TransactWriteItems` on both the Users and Settings table ARNs. The lab template creates no IAM role, so its runbook must explicitly require the equivalent permission on `LabInstanceProfile`.

## Provider-neutral LLM controls

### Question

Which runtime fields have a sufficiently common OpenAI-compatible meaning, and can the service promise that every configured model supports them?

### Sources

- [OpenAI API response parameters](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)
- [OpenRouter common response parameters](https://openrouter.ai/docs/api/reference/responses/basic-usage)
- [OpenRouter model `supported_parameters`](https://openrouter.ai/docs/guides/overview/models)

### Consequence

Expose only model/fallbacks, `temperature`, `top_p`, output-token budget, and a bounded prompt suffix. Temperature `0..2` and top-p `0..1` are common wire ranges. Output-token capacity and even parameter support vary by model/provider, so the application safety ceiling is not a capability guarantee. The adapter sends only non-null overrides, keeps its current Chat Completions `max_tokens` wire field, and surfaces a sanitized provider rejection without silently changing the stored setting. The UI advises changing temperature or top-p, not both, but does not prohibit both because existing compatible providers accept both.
