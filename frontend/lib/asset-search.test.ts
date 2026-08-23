import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ASSET_SEARCH_DEBOUNCE_MS,
  liveSearchQuery,
  optionalSearchQuote,
  searchLiveCatalog,
  searchResultLinkId,
} from "@/lib/asset-search";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import { PortfolioApiError, type AssetSearchHit } from "@/lib/portfolio";

const searchAssets = vi.fn();

vi.mock("@/lib/portfolio", async () => {
  const actual = await vi.importActual<typeof import("@/lib/portfolio")>("@/lib/portfolio");
  return {
    ...actual,
    searchAssets: (...args: unknown[]) => searchAssets(...args),
  };
});

const stockHit: AssetSearchHit = {
  symbol: "VNM",
  name: "Vinamilk",
  assetId: "VNM",
  assetType: "stock",
};

const cryptoHit: AssetSearchHit = {
  symbol: "BTC",
  name: "Bitcoin",
  assetId: "bitcoin",
  assetType: "crypto",
};

describe("liveSearchQuery", () => {
  it("debounces header search at 250ms", () => {
    expect(ASSET_SEARCH_DEBOUNCE_MS).toBe(250);
  });

  it("returns null for blank queries so callers skip fetch", () => {
    expect(liveSearchQuery("")).toBeNull();
    expect(liveSearchQuery("   ")).toBeNull();
    expect(liveSearchQuery("VNM")).toBe("VNM");
    expect(liveSearchQuery(" btc ")).toBe("btc");
  });
});

describe("searchLiveCatalog", () => {
  beforeEach(() => {
    searchAssets.mockReset();
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
  });

  afterEach(() => {
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    vi.restoreAllMocks();
  });

  it("does not fetch when q is empty", async () => {
    const result = await searchLiveCatalog({ q: "   " });
    expect(searchAssets).not.toHaveBeenCalled();
    expect(result).toEqual({ hits: [], failedTypes: [], authRequired: false });
  });

  it("issues parallel stock and crypto searches with the trimmed query", async () => {
    searchAssets.mockImplementation(async ({ type }: { type: "stock" | "crypto" }) => {
      return type === "stock" ? [stockHit] : [cryptoHit];
    });

    const result = await searchLiveCatalog({ q: "  btc  ", token: "fake:alice" });

    expect(searchAssets).toHaveBeenCalledTimes(2);
    expect(searchAssets).toHaveBeenCalledWith(
      expect.objectContaining({ q: "btc", type: "stock", token: "fake:alice" }),
    );
    expect(searchAssets).toHaveBeenCalledWith(
      expect.objectContaining({ q: "btc", type: "crypto", token: "fake:alice" }),
    );
    expect(result.hits).toEqual([stockHit, cryptoHit]);
    expect(result.failedTypes).toEqual([]);
    expect(result.authRequired).toBe(false);
  });

  it("returns authRequired with no hits on 401", async () => {
    searchAssets.mockRejectedValue(new PortfolioApiError(401, "Missing authorization header"));

    const result = await searchLiveCatalog({ q: "VNM" });

    expect(searchAssets).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ hits: [], failedTypes: [], authRequired: true });
  });

  it("keeps the other type when one search fails", async () => {
    searchAssets.mockImplementation(async ({ type }: { type: "stock" | "crypto" }) => {
      if (type === "stock") throw new Error("stock down");
      return [cryptoHit];
    });

    const result = await searchLiveCatalog({ q: "btc" });

    expect(result.hits).toEqual([cryptoHit]);
    expect(result.failedTypes).toEqual(["stock"]);
    expect(result.authRequired).toBe(false);
  });
});

describe("optionalSearchQuote / link id", () => {
  it("omits prices unless they already exist on the payload", () => {
    expect(optionalSearchQuote(stockHit)).toEqual({ price: null, changePct: null });
    expect(
      optionalSearchQuote({
        ...cryptoHit,
        price: "68420",
        changePct: 1.21,
      } as AssetSearchHit),
    ).toEqual({ price: 68420, changePct: 1.21 });
  });

  it("prefers assetId for AssetLink", () => {
    expect(searchResultLinkId(cryptoHit)).toBe("bitcoin");
    expect(searchResultLinkId(stockHit)).toBe("VNM");
  });
});
