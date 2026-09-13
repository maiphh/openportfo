# OpenPortfo frontend agent rules

Inherit the repository SDLC contract from `../AGENTS.md` and `../.workflows/feature-cycle.md`.

- Keep the Next.js App Router application compatible with static export to S3 and CloudFront. Do not add SSR, server actions, runtime-only dynamic routes, or optimized image requirements that break `npm run build`.
- Browser code talks to the FastAPI API through `frontend/lib/*` clients. Do not call CoinGecko, Vnstock, ExchangeRate-API, DynamoDB, S3, or other provider/AWS APIs directly from the browser.
- Preserve Cognito hosted-login behavior when Cognito variables are configured and fake-token development behavior when they are absent.
- Add focused Vitest tests beside affected components or libraries. Use `$playwright-verification` for pages, navigation, forms, authentication flows, responsive behavior, and cross-component user journeys.
- Run focused tests while iterating. Before handoff, run `npm run lint`, `npm test`, `npm run build`, and `npm run test:e2e` whenever browser-visible behavior changed.
- Prefer accessible roles, labels, and semantic HTML so browser tests and assistive technology can observe the same behavior.

Do not invoke Python market-analysis skills for ordinary frontend work. Cross-stack market-provider changes must follow the root cycle and keep provider access in backend adapters.
