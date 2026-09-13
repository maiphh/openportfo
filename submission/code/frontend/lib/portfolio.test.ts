import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import {
  assetSearchQuery,
  createHolding,
  defaultPortfolioCsvFilename,
  describeDonutSlice,
  exportPortfolioCsv,
  fetchPortfolio,
  filenameFromContentDisposition,
  parseMoney,
  pieSlices,
  PortfolioApiError,
  portfolioQuery,
  refreshPortfolio,
  searchAssets,
  triggerBlobDownload,
  unitPriceInDisplay,
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

  it("assetSearchQuery builds q and required type", () => {
    expect(assetSearchQuery({ q: "VNM", type: "stock" })).toBe("q=VNM&type=stock");
    expect(assetSearchQuery({ q: "btc", type: "crypto" })).toBe("q=btc&type=crypto");
  });

  it("parseMoney handles nullish and numeric strings", () => {
    expect(parseMoney(null)).toBeNull();
    expect(parseMoney("")).toBeNull();
    expect(parseMoney("12.5")).toBe(12.5);
    expect(parseMoney("nope")).toBeNull();
  });

  it("unitPriceInDisplay prefers API display fields", () => {
    expect(
      unitPriceInDisplay("30000", "27600", "USD", "EUR", () => 1),
    ).toEqual({ amount: 27600, currency: "EUR" });
  });

  it("unitPriceInDisplay falls back to convertToDisplay when API field is absent", () => {
    expect(
      unitPriceInDisplay("30000", null, "USD", "EUR", (amt, src) => {
        expect(src).toBe("USD");
        return amt * 0.92;
      }),
    ).toEqual({ amount: 27600, currency: "EUR" });
  });

  it("unitPriceInDisplay keeps native amount and currency when FX is missing", () => {
    expect(unitPriceInDisplay("30000", null, "USD", "EUR", () => null)).toEqual({
      amount: 30000,
      currency: "USD",
    });
    expect(unitPriceInDisplay("30000", null, "USD", "EUR")).toEqual({
      amount: 30000,
      currency: "USD",
    });
  });

  it("unitPriceInDisplay shows em dash input as null amount when native is missing", () => {
    expect(unitPriceInDisplay(null, null, "USD", "EUR")).toEqual({
      amount: null,
      currency: "USD",
    });
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
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
  });

  afterEach(() => {
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
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

  it("searchAssets GETs /api/assets/search with q and type", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse([]));

    await searchAssets({ q: "VNM", type: "stock" });

    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/assets/search?q=VNM&type=stock`,
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer fake:alice",
        }),
      }),
    );
  });

  it("searchAssets maps 401 to authRequired", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ detail: "Missing authorization header" }, 401));

    await expect(searchAssets({ q: "btc", type: "crypto" })).rejects.toMatchObject({
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
      assetId: "bitcoin",
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
          assetId: "bitcoin",
        }),
      }),
    );
  });

  it("exportPortfolioCsv fetches text/csv and returns a Blob", async () => {
    const csvBody = "symbol,assetType\r\nBTC,crypto\r\n";
    vi.mocked(global.fetch).mockResolvedValue(
      new Response(csvBody, {
        status: 200,
        headers: {
          "Content-Type": "text/csv; charset=utf-8",
          "Content-Disposition": 'attachment; filename="openportfo-portfolio-20260823.csv"',
        },
      }),
    );

    const result = await exportPortfolioCsv({ displayCurrency: "VND", assetType: "crypto" });

    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/portfolio/export?displayCurrency=VND&assetType=crypto&format=csv`,
      expect.objectContaining({
        method: "GET",
        cache: "no-store",
        headers: expect.objectContaining({
          Authorization: "Bearer fake:alice",
          Accept: "text/csv",
        }),
      }),
    );
    expect(result.blob).toBeTruthy();
    expect(result.blob.size).toBeGreaterThan(0);
    expect(String(result.blob.type)).toContain("text/csv");
    expect(result.filename).toBe("openportfo-portfolio-20260823.csv");
    await expect(result.blob.text()).resolves.toContain("BTC");
  });

  it("exportPortfolioCsv maps 401 to PortfolioApiError.authRequired", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Missing authorization header" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(exportPortfolioCsv({ displayCurrency: "USD" })).rejects.toMatchObject({
      name: "PortfolioApiError",
      authRequired: true,
      status: 401,
    } satisfies Partial<PortfolioApiError>);
  });

  it("exportPortfolioCsv maps 400 detail from JSON body", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "format must be csv" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(exportPortfolioCsv({ displayCurrency: "USD" })).rejects.toMatchObject({
      name: "PortfolioApiError",
      status: 400,
      detail: "format must be csv",
    });
  });
});

describe("portfolio CSV helpers", () => {
  it("filenameFromContentDisposition reads quoted filename", () => {
    expect(
      filenameFromContentDisposition('attachment; filename="openportfo-portfolio-20260823.csv"'),
    ).toBe("openportfo-portfolio-20260823.csv");
    expect(filenameFromContentDisposition(null)).toBeNull();
  });

  it("defaultPortfolioCsvFilename uses UTC YYYYMMDD", () => {
    expect(defaultPortfolioCsvFilename(new Date("2026-08-23T01:02:03Z"))).toBe(
      "openportfo-portfolio-20260823.csv",
    );
  });

  it("triggerBlobDownload creates an object URL and clicks an anchor without reload", () => {
    const createObjectURL = vi.fn(() => "blob:test-csv");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, writable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, writable: true, value: revokeObjectURL });

    const click = vi.fn();
    const origCreate = document.createElement.bind(document);
    const createSpy = vi.spyOn(document, "createElement").mockImplementation((tag: string, options?: ElementCreationOptions) => {
      const el = origCreate(tag, options);
      if (tag === "a") {
        el.click = click;
      }
      return el;
    });

    const hrefBefore = window.location.href;
    triggerBlobDownload(new Blob(["symbol\r\n"], { type: "text/csv" }), "openportfo-portfolio-20260823.csv");

    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:test-csv");
    expect(window.location.href).toBe(hrefBefore);

    createSpy.mockRestore();
  });
});
