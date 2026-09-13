import { expect, test } from "@playwright/test";

/**
 * BL-031 single-EB smoke: verifies the FastAPI process serves the bundled
 * Next.js export (same-origin UI + API) instead of the static-server.
 *
 * Skipped unless SINGLE_EB_SMOKE=1 so the default suite stays green without
 * a running backend. Run against a local backend serving a real build:
 *
 *   $env:SERVE_FRONTEND = "true"
 *   uvicorn app.main:app --port 8000            # from backend/
 *   $env:SINGLE_EB_SMOKE = "1"
 *   $env:SINGLE_EB_BASE_URL = "http://127.0.0.1:8000"
 *   npx playwright test e2e/single-eb-smoke.spec.ts
 */
const enabled = process.env.SINGLE_EB_SMOKE === "1";
const baseUrl = (process.env.SINGLE_EB_BASE_URL || "http://127.0.0.1:8000").replace(
  /\/+$/,
  "",
);

test.describe("single-EB hosting smoke (BL-031)", () => {
  test.skip(!enabled, "set SINGLE_EB_SMOKE=1 to run against a SERVE_FRONTEND=true backend");

  test("GET / serves the bundled frontend HTML", async ({ request }) => {
    const res = await request.get(`${baseUrl}/`);
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"] ?? "").toContain("text/html");
    await expect(res.text()).resolves.toMatch(/__next|OpenPortfo/);
  });

  test("deep links fall back to HTML", async ({ request }) => {
    for (const path of ["/portfolio/", "/auth/callback/"]) {
      const res = await request.get(`${baseUrl}${path}`);
      expect(res.status(), path).toBe(200);
      expect(res.headers()["content-type"] ?? "", path).toContain("text/html");
    }
  });

  test("GET /health stays JSON", async ({ request }) => {
    const res = await request.get(`${baseUrl}/health`);
    expect(res.status()).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });

  test("unauthenticated /api/* stays 401 JSON (never HTML)", async ({ request }) => {
    const res = await request.get(`${baseUrl}/api/auth/me`);
    expect(res.status()).toBe(401);
    expect(res.headers()["content-type"] ?? "").toContain("application/json");
  });
});
