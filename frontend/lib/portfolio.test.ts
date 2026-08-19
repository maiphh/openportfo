import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import {
  describeDonutSlice,
  fetchPortfolio,
  parseMoney,
  pieSlices,
  PortfolioApiError,
  portfolioQuery,
  refreshPortfolio,
} from "@/lib/portfolio";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("portfolio helpers", () => {
  it("portfolioQuery includes displayCurrency and optional assetType", () => {
    expect(portfolioQuery({ displayCurrency: "VND" })).toBe("displayCurrency=VND");
    expect(portfolioQuery({ displayCurrency: "USD", assetType: "crypto" })).toBe(
      "displayCurrency=USD&assetType=crypto",
    );
    expect(portfolioQuery({ displayCurrency: "EUR", assetType: "all" })).toBe("displayCurrency=EUR");
  });

  it("parseMoney handles nullish and numeric strings", () => {
    expect(parseMoney(null)).toBeNull();
    expect(parseMoney("")).toBeNull();
    expect(parseMoney("12.5")).toBe(12.5);
    expect(parseMoney("nope")).toBeNull();
  });

  it("pieSlices builds sequential angles that cover 360", () => {
    const slices = pieSlices([
      { key: "a", value: 1, color: "#fff" },
      { key: "b", value: 3, color: "#000" },
    ]);
    expect(slices).toHaveLength(2);
    expect(slices[0].startAngle).toBe(-90);
    expect(slices[1].endAngle - slices[0].startAngle).toBeCloseTo(360);
    expect(pieSlices([{ key: "z", value: 0, color: "#fff" }])).toEqual([]);
  });

  it("describeDonutSlice returns an SVG path", () => {
    const d = describeDonutSlice(80, 80, 70, 40, -90, 0);
    expect(d.startsWith("M ")).toBe(true);
    expect(d.includes("A ")).toBe(true);
    expect(d.endsWith("Z")).toBe(true);
  });
});

describe("portfolio API client", () => {
  const base = apiBase();

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
  });

  afterEach(() => {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("fetchPortfolio sends Bearer + displayCurrency", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({
        lines: [],
        totalsByCurrency: {},
        totalsDisplay: null,
        fx: { status: "missing", rates: {} },
      }),
    );

    await fetchPortfolio({ displayCurrency: "EUR", assetType: "stock" });

    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/portfolio?displayCurrency=EUR&assetType=stock`,
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer fake:alice",
        }),
      }),
    );
  });

  it("refreshPortfolio POSTs to /api/portfolio/refresh", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({
        lines: [],
        totalsByCurrency: {},
        fx: { status: "fresh", rates: {} },
      }),
    );

    await refreshPortfolio({ displayCurrency: "VND" });

    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/portfolio/refresh?displayCurrency=VND`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("maps 401 to PortfolioApiError.authRequired", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ detail: "Missing authorization header" }, 401));

    await expect(fetchPortfolio({ displayCurrency: "USD" })).rejects.toMatchObject({
      name: "PortfolioApiError",
      authRequired: true,
      status: 401,
    } satisfies Partial<PortfolioApiError>);
  });
});
