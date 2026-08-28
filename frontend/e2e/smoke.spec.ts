import { expect, test } from "@playwright/test";

test("loads the market dashboard shell and primary navigation", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/");

  await expect(page).toHaveURL(/\/markets\/stock\/?$/);
  await expect(page).toHaveTitle(/OpenPortfo/);
  await expect(page.getByRole("navigation")).toBeVisible();
  await expect(page.getByRole("link", { name: /Portfolio/i })).toBeVisible();
  expect(pageErrors).toEqual([]);
});
