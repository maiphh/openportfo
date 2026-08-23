import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import {
  assetDetailHref,
  assetCanonicalHref,
  assetDetailQuery,
  buildAssetStats,
  buildExternalLinks,
  fetchAssetDetail,
  fetchAssetHistory,
  historySeries,
  normalizeAssetId,
  normalizeAssetKind,
  parseAssetRouteParams,
  parseChartRange,
  AssetApiError,
} from "@/lib/asset";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("assetDetailHref", () => {
  it("builds canonical crypto and stock query routes", () => {
    expect(assetDetailHref("crypto", "btc")).toBe("/asset?type=crypto&id=btc");
    expect(assetDetailHref("stock", "VNM")).toBe("/asset?type=stock&id=VNM");
    expect(assetCanonicalHref("CRYPTO", "bitcoin")).toBe("/asset?type=crypto&id=bitcoin");
  });

  it("encodes query ids", () => {
    expect(assetDetailHref("crypto", "my coin")).toBe("/asset?type=crypto&id=my%20coin");
  });

  it("does not guess a type for invalid input", () => {
    expect(assetDetailHref("other", "ABC")).toBe("/asset");
    expect(assetDetailHref("crypto", "")).toBe("/asset");
  });
});

describe("asset route params", () => {
  it("normalizes valid ids and parses the canonical query", () => {
    expect(normalizeAssetId("  token-with.dots  ")).toBe("token-with.dots");
    expect(parseAssetRouteParams(new URLSearchParams("type=CRYPTO&id=arbitrary-token-999"))).toEqual({
      assetType: "crypto",
      id: "arbitrary-token-999",
    });
  });

  it("rejects malformed or path-like query values", () => {
    expect(normalizeAssetId("/etc/passwd")).toBeNull();
    expect(normalizeAssetId("\\windows\\path")).toBeNull();
    expect(normalizeAssetId("\u0000bad")).toBeNull();
    expect(parseAssetRouteParams(new URLSearchParams("type=fx&id=VNM"))).toBeNull();
    expect(parseAssetRouteParams(new URLSearchParams("type=stock&id="))).toBeNull();
  });
});

describe("asset helpers", () => {
  it("normalizeAssetKind and parseChartRange", () => {
    expect(normalizeAssetKind("crypto")).toBe("crypto");
    expect(normalizeAssetKind("STOCK")).toBe("stock");
    expect(normalizeAssetKind("fx")).toBeNull();
    expect(parseChartRange("7d")).toBe("7d");
    expect(parseChartRange("1Y")).toBe("1y");
    expect(parseChartRange("nope")).toBe("30d");
  });

  it("assetDetailQuery includes currency and optional range", () => {
    expect(assetDetailQuery({ currency: "VND" })).toBe("currency=VND");
    expect(assetDetailQuery({ currency: "USD", range: "90d" })).toBe("currency=USD&range=90d");
  });

  it("buildAssetStats hides nulls and keeps type-relevant rows", () => {
    const crypto = buildAssetStats(
      "crypto",
      {
        marketCapRank: 1,
        circulatingSupply: "19",
        exchange: "HOSE",
        industry: null,
      },
      { marketCapDisplay: "1000", volume24h: null, ath: "2" },
    );
    expect(crypto.map((r) => r.label)).toEqual(["Rank", "Market cap", "Circulating supply", "ATH"]);
    expect(crypto.find((r) => r.label === "Exchange")).toBeUndefined();

    const stock = buildAssetStats(
      "stock",
      { exchange: "HOSE", industry: "Food", country: "VN", circulatingSupply: "99" },
      { marketCap: "500" },
    );
    expect(stock.map((r) => r.label)).toEqual(["Exchange", "Industry", "Country", "Market cap"]);
    expect(stock.find((r) => r.label === "Circulating supply")).toBeUndefined();
  });

  it("buildExternalLinks skips empty values and homepage duplicates", () => {
    expect(
      buildExternalLinks({
        homepage: "https://example.com",
        links: {
          homepage: "https://example.com",
          twitter: "https://x.com/ex",
          empty: "",
          missing: null,
        },
      }),
    ).toEqual([
      { label: "Homepage", href: "https://example.com" },
      { label: "twitter", href: "https://x.com/ex" },
    ]);
  });

  it("historySeries prefers display prices when requested", () => {
    const series = historySeries(
      {
        assetType: "crypto",
        symbol: "BTC",
        assetId: "bitcoin",
        range: "7d",
        nativeCurrency: "USD",
        displayCurrency: "VND",
        points: [
          { t: "a", price: "1", priceDisplay: "25000" },
          { t: "b", price: "2", priceDisplay: "50000" },
          { t: "c", price: "bad", priceDisplay: null },
        ],
      },
      true,
    );
    expect(series).toEqual([25000, 50000]);
  });
});

describe("asset API client", () => {
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

  it("fetchAssetDetail hits typed slug with currency", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({
        assetType: "crypto",
        symbol: "BTC",
        assetId: "bitcoin",
        name: "Bitcoin",
        nativeCurrency: "USD",
        displayCurrency: "VND",
        profile: {},
        quote: null,
      }),
    );

    await fetchAssetDetail({ assetType: "crypto", slug: "btc", currency: "VND" });

    const [url, init] = vi.mocked(global.fetch).mock.calls[0] ?? [];
    expect(String(url)).toBe(`${base}/api/assets/crypto/btc?currency=VND`);
    expect((init as RequestInit).headers).toMatchObject({
      Authorization: "Bearer fake:alice",
    });
  });

  it("fetchAssetHistory hits history endpoint with range", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({
        assetType: "stock",
        symbol: "VNM",
        assetId: "VNM",
        range: "1y",
        nativeCurrency: "VND",
        displayCurrency: "USD",
        points: [],
      }),
    );

    await fetchAssetHistory({
      assetType: "stock",
      slug: "VNM",
      currency: "USD",
      range: "1y",
    });

    const [url] = vi.mocked(global.fetch).mock.calls[0] ?? [];
    expect(String(url)).toBe(`${base}/api/assets/stock/VNM/history?range=1y&currency=USD`);
  });

  it("maps 404 to AssetApiError.notFound", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ detail: "Asset not found" }, 404));

    await expect(
      fetchAssetDetail({ assetType: "crypto", slug: "nope", currency: "USD" }),
    ).rejects.toMatchObject({
      name: "AssetApiError",
      notFound: true,
      status: 404,
    } satisfies Partial<AssetApiError>);
  });
});
