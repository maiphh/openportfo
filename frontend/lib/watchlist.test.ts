import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import {
  addWatchlist,
  fetchWatchlist,
  removeWatchlist,
  watchlistItemKey,
  watchlistPriceInDisplay,
  WatchlistApiError,
} from "@/lib/watchlist";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function emptyResponse(status: number): Response {
  return new Response(null, { status });
}

const sampleItem = {
  userId: "alice",
  assetType: "crypto" as const,
  symbol: "BTC",
  assetId: "bitcoin",
  addedAt: "2026-08-19T00:00:00Z",
  price: "97000",
  currency: "USD",
  asOf: "2026-08-19T01:00:00Z",
  stale: false,
};

describe("watchlist helpers", () => {
  it("watchlistItemKey joins type and symbol", () => {
    expect(watchlistItemKey({ assetType: "stock", symbol: "VNM" })).toBe("stock:VNM");
  });

  it("watchlistPriceInDisplay marks missing quotes", () => {
    expect(watchlistPriceInDisplay(null, "USD", "VND")).toEqual({
      amount: null,
      currency: "USD",
      missing: true,
    });
    expect(watchlistPriceInDisplay("", null, "VND")).toEqual({
      amount: null,
      currency: "VND",
      missing: true,
    });
  });

  it("watchlistPriceInDisplay keeps native when currencies match", () => {
    expect(watchlistPriceInDisplay("90.5", "VND", "VND")).toEqual({
      amount: 90.5,
      currency: "VND",
      missing: false,
    });
  });

  it("watchlistPriceInDisplay converts when FX is available", () => {
    expect(
      watchlistPriceInDisplay("100", "USD", "VND", (amount, src) => {
        expect(src).toBe("USD");
        return amount * 25000;
      }),
    ).toEqual({ amount: 2500000, currency: "VND", missing: false });
  });

  it("watchlistPriceInDisplay keeps native amount when FX is missing", () => {
    expect(watchlistPriceInDisplay("100", "USD", "EUR", () => null)).toEqual({
      amount: 100,
      currency: "USD",
      missing: false,
    });
    expect(watchlistPriceInDisplay("100", "USD", "EUR")).toEqual({
      amount: 100,
      currency: "USD",
      missing: false,
    });
  });
});

describe("watchlist API client", () => {
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

  it("fetchWatchlist GET /api/watchlist with Bearer", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse([sampleItem]));

    const items = await fetchWatchlist();

    expect(items).toEqual([sampleItem]);
    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/watchlist`,
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer fake:alice",
        }),
      }),
    );
  });

  it("addWatchlist POSTs camelCase body and returns the created item", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse(
        {
          userId: "alice",
          assetType: "stock",
          symbol: "VNM",
          assetId: "VNM",
          stale: false,
          price: null,
          currency: null,
        },
        201,
      ),
    );

    const created = await addWatchlist({
      assetType: "stock",
      symbol: "VNM",
      assetId: "VNM",
    });

    expect(created.symbol).toBe("VNM");
    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/watchlist`,
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
        }),
      }),
    );
  });

  it("addWatchlist maps 409 to WatchlistApiError.conflict", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({ detail: "Watchlist item already exists" }, 409),
    );

    await expect(
      addWatchlist({ assetType: "crypto", symbol: "BTC", assetId: "bitcoin" }),
    ).rejects.toMatchObject({
      name: "WatchlistApiError",
      status: 409,
      conflict: true,
      authRequired: false,
      detail: "Watchlist item already exists",
    } satisfies Partial<WatchlistApiError>);
  });

  it("removeWatchlist DELETE path is encoded and accepts 204", async () => {
    vi.mocked(global.fetch).mockResolvedValue(emptyResponse(204));

    await expect(removeWatchlist("crypto", "BTC")).resolves.toBeUndefined();

    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/watchlist/crypto/BTC`,
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({
          Authorization: "Bearer fake:alice",
        }),
      }),
    );
  });

  it("maps 401 to WatchlistApiError.authRequired", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ detail: "Missing authorization header" }, 401));

    await expect(fetchWatchlist()).rejects.toMatchObject({
      name: "WatchlistApiError",
      authRequired: true,
      status: 401,
    } satisfies Partial<WatchlistApiError>);
  });

  it("maps 400 invalid asset to WatchlistApiError", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({ detail: "assetType must be 'crypto' or 'stock'" }, 400),
    );

    await expect(
      addWatchlist({ assetType: "stock", symbol: "???", assetId: "???" }),
    ).rejects.toMatchObject({
      name: "WatchlistApiError",
      status: 400,
      conflict: false,
      detail: "assetType must be 'crypto' or 'stock'",
    } satisfies Partial<WatchlistApiError>);
  });
});
