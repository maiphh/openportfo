import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import {
  createHolding,
  describeDonutSlice,
  fetchPortfolio,
  parseMoney,
  pieSlices,
  PortfolioApiError,
  portfolioQuery,
  refreshPortfolio,
  updateHolding,
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

  it("pieSlices starts at 0° (12 o'clock) and covers 360", () => {
    const slices = pieSlices([
      { key: "a", value: 1, color: "#fff" },
      { key: "b", value: 3, color: "#000" },
    ]);
    expect(slices).toHaveLength(2);
    expect(slices[0].startAngle).toBe(0);
    expect(slices[1].endAngle - slices[0].startAngle).toBeCloseTo(360);
    expect(pieSlices([{ key: "z", value: 0, color: "#fff" }])).toEqual([]);
  });

  it("describeDonutSlice returns a non-degenerate path for a 100% slice", () => {
    const [slice] = pieSlices([{ key: "only", value: 42, color: "#0fedbe" }]);
    expect(slice.endAngle - slice.startAngle).toBeCloseTo(360);
    const d = describeDonutSlice(80, 80, 70, 40, slice.startAngle, slice.endAngle);
    expect(d.startsWith("M ")).toBe(true);
    expect(d.includes("A ")).toBe(true);
    expect(d.endsWith("Z")).toBe(true);
    // Full ring uses two outer arcs; a collapsed single-arc path would be tiny.
    expect(d.match(/A 70 70/g)?.length).toBeGreaterThanOrEqual(2);
    expect(d.length).toBeGreaterThan(40);
  });

  it("describeDonutSlice returns an SVG path for partial sweeps", () => {
    const d = describeDonutSlice(80, 80, 70, 40, 0, 90);
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

  it("createHolding sends Bearer and session currency body", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({
        userId: "alice",
        assetType: "stock",
        symbol: "VNM",
        qty: "1",
        avgCost: "25000",
        currency: "VND",
      }, 201),
    );

    await createHolding({
      assetType: "stock",
      symbol: "VNM",
      assetId: "VNM",
      qty: "1",
      avgCost: "1",
      currency: "USD",
      note: null,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/holdings`,
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer fake:alice",
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({
          assetType: "stock",
          symbol: "VNM",
          assetId: "VNM",
          qty: "1",
          avgCost: "1",
          currency: "USD",
          note: null,
        }),
      }),
    );
  });

  it("updateHolding PUTs Bearer + avgCost/currency camelCase", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({
        userId: "alice",
        assetType: "crypto",
        symbol: "BTC",
        qty: "2",
        avgCost: "1000",
        currency: "USD",
      }),
    );

    await updateHolding("crypto", "BTC", {
      qty: "2",
      avgCost: "25000000",
      currency: "VND",
      note: "rebalance",
    });

    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/holdings/crypto/BTC`,
      expect.objectContaining({
        method: "PUT",
        headers: expect.objectContaining({
          Authorization: "Bearer fake:alice",
        }),
        body: JSON.stringify({
          qty: "2",
          avgCost: "25000000",
          currency: "VND",
          note: "rebalance",
        }),
      }),
    );
  });
});
