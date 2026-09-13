import { expect, test, type Page } from "@playwright/test";

async function stubSettingsApis(page: Page) {
  const profile = {
    userId: "alice",
    email: "alice@example.com",
    name: "Alice",
    role: "user",
    emailOptIn: false,
    newsKeywords: [],
    preferredCurrency: "USD",
  };

  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(profile),
    });
  });

  await page.route("**/api/settings", async (route) => {
    const request = route.request();
    if (request.method() === "PUT") {
      const body = request.postDataJSON() as { emailOptIn?: boolean };
      profile.emailOptIn = Boolean(body.emailOptIn);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(profile),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(profile),
    });
  });

  await page.route("**/api/**", async (route) => {
    if (route.request().url().includes("/api/auth/me") || route.request().url().includes("/api/settings")) {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });
}

test("user can opt in to the daily portfolio email", async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("openportfo.accessToken", "e2e-user-token");
  });
  await stubSettingsApis(page);
  await page.goto("/settings");
  const checkbox = page.getByRole("checkbox", { name: /Receive daily portfolio email/i });
  await expect(checkbox).toBeVisible({ timeout: 15_000 });
  await expect(checkbox).not.toBeChecked();
  await expect(page.getByText(/00:15 Asia\/Ho_Chi_Minh/i)).toBeVisible();
  await checkbox.check();
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("status")).toHaveText("Saved.");
  await expect(checkbox).toBeChecked();
});
