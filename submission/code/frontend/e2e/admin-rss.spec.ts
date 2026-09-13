import { expect, test, type Page } from "@playwright/test";

async function stubAdminApis(page: Page) {
  const sources: Array<{ sourceId: string; name: string; url: string; enabled: boolean }> = [];
  let settings = {
    version: 1,
    emailTime: "08:00",
    timezone: "UTC",
    emailEnabled: false,
    priceCacheTtlMinutes: 10,
    jobs: { news: false, snapshot: true, email: false, price: true },
    defaultDisplayCurrency: "USD",
    chat: {
      overrides: {
        model: null,
        fallbackModels: null,
        temperature: null,
        topP: null,
        maxTokens: null,
        systemPromptExtra: null,
      },
      defaults: {
        model: null,
        fallbackModels: null,
        temperature: null,
        topP: null,
        maxTokens: null,
        systemPromptExtra: null,
      },
      effective: {
        model: null,
        fallbackModels: null,
        temperature: null,
        topP: null,
        maxTokens: null,
        systemPromptExtra: null,
      },
      availableModels: [] as string[],
    },
  };

  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        userId: "admin",
        email: "admin@example.com",
        name: "Admin",
        role: "admin",
      }),
    });
  });

  await page.route("**/api/admin/users**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], nextCursor: null }),
    });
  });

  await page.route("**/api/admin/rss-sources**", async (route) => {
    const request = route.request();
    const method = request.method();
    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sources),
      });
      return;
    }
    if (method === "POST") {
      const body = request.postDataJSON() as { name?: string; url?: string };
      if (!body.url?.startsWith("http") || body.url.includes("127.0.0.1")) {
        await route.fulfill({
          status: 400,
          contentType: "application/json",
          body: JSON.stringify({ detail: "URL host is not allowed" }),
        });
        return;
      }
      const created = {
        sourceId: `src-${sources.length + 1}`,
        name: body.name || "Feed",
        url: body.url,
        enabled: true,
      };
      sources.push(created);
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(created),
      });
      return;
    }
    if (method === "PUT") {
      const id = request.url().split("/").pop() || "";
      const body = request.postDataJSON() as { enabled?: boolean };
      const idx = sources.findIndex((item) => item.sourceId === id);
      if (idx < 0) {
        await route.fulfill({ status: 404, body: "missing" });
        return;
      }
      sources[idx] = { ...sources[idx], enabled: Boolean(body.enabled) };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sources[idx]),
      });
      return;
    }
    if (method === "DELETE") {
      const id = request.url().split("/").pop() || "";
      const idx = sources.findIndex((item) => item.sourceId === id);
      if (idx >= 0) sources.splice(idx, 1);
      await route.fulfill({ status: 204 });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/admin/settings**", async (route) => {
    const request = route.request();
    if (request.method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(settings),
      });
      return;
    }
    if (request.method() === "PUT") {
      const body = request.postDataJSON() as {
        version?: number;
        jobs?: { news?: boolean; email?: boolean };
        emailEnabled?: boolean;
      };
      if (body.version !== settings.version) {
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({ detail: { code: "settings_conflict" } }),
        });
        return;
      }
      settings = {
        ...settings,
        version: settings.version + 1,
        emailEnabled: body.emailEnabled ?? settings.emailEnabled,
        jobs: {
          ...settings.jobs,
          news: body.jobs?.news ?? settings.jobs.news,
          email: body.jobs?.email ?? settings.jobs.email,
        },
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(settings),
      });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/admin/job-runs**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          runId: "run-1",
          jobType: "news",
          status: "success",
          startedAt: "2026-08-28T00:00:00Z",
          finishedAt: "2026-08-28T00:01:00Z",
          message: null,
          counts: { written: 2, fetched: 2, sources_succeeded: 1, sources_failed: 0 },
        },
      ]),
    });
  });
}

async function openAdmin(page: Page) {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("openportfo.accessToken", "e2e-admin-token");
  });
  await stubAdminApis(page);
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "RSS sources" })).toBeVisible({
    timeout: 15_000,
  });
}

test("admin can manage RSS sources and toggle the news job", async ({ page }) => {
  await openAdmin(page);

  await expect(page.getByRole("heading", { name: "RSS sources" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Job controls" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent job runs" })).toBeVisible();

  await page.getByLabel("Name").fill("CoinDesk");
  await page.getByLabel("Feed URL").fill("https://example.com/feed.xml");
  await page.getByRole("button", { name: "Add source" }).click();
  await expect(page.getByText("CoinDesk")).toBeVisible();

  await page.getByLabel("Enabled CoinDesk").click();
  await expect(page.getByLabel("Enabled CoinDesk")).not.toBeChecked();

  await page.getByLabel("News ingest").click();
  await expect(page.getByLabel("News ingest")).toBeChecked();

  await page.getByLabel("Daily portfolio email").click();
  await expect(page.getByLabel("Daily portfolio email")).toBeChecked();

  await expect(page.getByRole("cell", { name: "success" })).toBeVisible();
});

test("admin RSS validation failure is announced", async ({ page }) => {
  await openAdmin(page);
  await page.getByLabel("Name").fill("Bad");
  await page.getByLabel("Feed URL").fill("https://127.0.0.1/feed.xml");
  await page.getByRole("button", { name: "Add source" }).click();
  await expect(page.getByText(/public http\(s\) feed URL/i)).toBeVisible();
});

test("admin panels remain usable on a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openAdmin(page);
  await expect(page.getByRole("heading", { name: "RSS sources" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Job controls" })).toBeVisible();
  await expect(page.getByLabel("News ingest")).toBeVisible();
});
