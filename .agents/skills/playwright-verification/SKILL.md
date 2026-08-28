---
name: playwright-verification
description: Verify OpenPortfo browser behavior with Playwright when a change affects pages, navigation, forms, authentication flows, responsive layout, or client/API integration. Do not use it as a substitute for Vitest unit tests or the production build.
---

# Playwright verification

Use `frontend/playwright.config.ts` and tests under `frontend/e2e/`.

1. Translate the affected acceptance criteria into observable user behavior. Prefer roles, labels, and visible text over CSS selectors.
2. Run the smallest relevant test while iterating from `frontend/`:

   ```powershell
   npx playwright test e2e/<spec>.spec.ts
   ```

3. Run `npm run test:e2e` before handoff when browser-visible behavior changed. Also run Vitest and `npm run build`; an E2E pass does not cover type errors or component edge cases.
4. Let Playwright manage the frontend server through `webServer`. If a scenario needs the FastAPI backend, start it with fake auth and memory adapters unless the acceptance criteria explicitly require LocalStack. Never point tests at production services.
5. Inspect failures using the saved trace, screenshot, video, console errors, and network responses. Fix the underlying behavior; do not weaken assertions merely to make a test pass.
6. Cover the happy path plus the highest-risk failure or boundary path. For responsive UI, verify at least one desktop and one mobile viewport when layout behavior changes.

Keep tests deterministic. Stub only third-party boundaries that are outside the feature; do not stub the application behavior being accepted. Do not update visual snapshots without inspecting the rendered result.
