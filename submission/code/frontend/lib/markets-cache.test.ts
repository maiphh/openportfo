import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { HeatmapResponse, QuotesResponse } from "@/lib/api";
import {
  isHeatmapPayload,
  isQuotesPayload,
  marketsCacheKey,
  readHeatmapCache,
  readMarketsCache,
  readQuotesCache,
  writeHeatmapCache,
  writeMarketsCache,
  writeQuotesCache,
} from "@/lib/markets-cache";

const heatmapPayload: HeatmapResponse = {
  exchange: "HOSE",
  limit: 100,
  source: "vnstock",
  sectors: [
    {
      name: "Banks",
      stocks: [{ symbol: "VCB", name: "Vietcombank", changePct: 1.25, marketCap: 400 }],
    },
  ],
};

const quotesPayload: QuotesResponse = {
  exchange: "HOSE",
  limit: 80,
  source: "vnstock",
  groups: [
    {
      name: "BANKS",
      rows: [
        {
          symbol: "VCB",
          name: "Vietcombank",
          value: 90,
          change: 1,
          changePct: 1.1,
          open: 89,
          high: 91,
          low: 88,
          prev: 89,
        },
      ],
    },
  ],
};

describe("markets-cache", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-19T04:00:00.000Z"));
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.useRealTimers();
  });

  it("uses per-market per-widget keys", () => {
    expect(marketsCacheKey("heatmap", "stock")).toBe("openportfo.markets.heatmap.stock");
    expect(marketsCacheKey("heatmap", "crypto")).toBe("openportfo.markets.heatmap.crypto");
    expect(marketsCacheKey("quotes", "stock")).toBe("openportfo.markets.quotes.stock");
    expect(marketsCacheKey("quotes", "crypto")).toBe("openportfo.markets.quotes.crypto");
  });

  it("writes and reads a heatmap payload", () => {
    writeHeatmapCache("stock", heatmapPayload);
    const hit = readHeatmapCache("stock");
    expect(hit?.savedAt).toBe("2026-08-19T04:00:00.000Z");
    expect(hit?.payload.sectors[0]?.stocks[0]?.symbol).toBe("VCB");
    expect(readHeatmapCache("crypto")).toBeNull();
    expect(readQuotesCache("stock")).toBeNull();
  });

  it("writes and reads a quotes payload", () => {
    writeQuotesCache("crypto", { ...quotesPayload, source: "coingecko" });
    const hit = readQuotesCache("crypto");
    expect(hit?.payload.groups[0]?.rows[0]?.symbol).toBe("VCB");
    expect(readQuotesCache("stock")).toBeNull();
  });

  it("ignores corrupt JSON", () => {
    sessionStorage.setItem(marketsCacheKey("heatmap", "stock"), "{not-json");
    expect(readHeatmapCache("stock")).toBeNull();
  });

  it("ignores envelopes missing payload or a valid savedAt", () => {
    sessionStorage.setItem(marketsCacheKey("heatmap", "stock"), JSON.stringify({ payload: heatmapPayload }));
    expect(readHeatmapCache("stock")).toBeNull();

    sessionStorage.setItem(
      marketsCacheKey("quotes", "stock"),
      JSON.stringify({ savedAt: "not-a-date", payload: quotesPayload }),
    );
    expect(readQuotesCache("stock")).toBeNull();
  });

  it("ignores empty boards so a later remount still cold-loads", () => {
    sessionStorage.setItem(
      marketsCacheKey("heatmap", "stock"),
      JSON.stringify({ savedAt: "2026-08-19T04:00:00.000Z", payload: { sectors: [] } }),
    );
    sessionStorage.setItem(
      marketsCacheKey("quotes", "stock"),
      JSON.stringify({
        savedAt: "2026-08-19T04:00:00.000Z",
        payload: { groups: [{ name: "BANKS", rows: [] }] },
      }),
    );
    expect(readHeatmapCache("stock")).toBeNull();
    expect(readQuotesCache("stock")).toBeNull();
    expect(isHeatmapPayload({ sectors: [] })).toBe(false);
    expect(isQuotesPayload({ groups: [{ name: "BANKS", rows: [] }] })).toBe(false);
  });

  it("skips persist when storage throws (quota / private mode)", () => {
    const storage = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("quota");
      },
    };
    expect(() => writeMarketsCache("heatmap", "stock", heatmapPayload, storage)).not.toThrow();
    expect(readMarketsCache("heatmap", "stock", isHeatmapPayload, storage)).toBeNull();
  });

  it("skips persist when storage is unavailable", () => {
    expect(() => writeHeatmapCache("stock", heatmapPayload, null)).not.toThrow();
    expect(readHeatmapCache("stock", null)).toBeNull();
  });
});
