import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase, fetchMarketHeatmap, fetchMarketQuotes } from "@/lib/api";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

function lastFetchUrl(): string {
  expect(global.fetch).toHaveBeenCalled();
  const [url] = vi.mocked(global.fetch).mock.calls.at(-1) ?? [];
  expect(url).toEqual(expect.any(String));
  return String(url);
}

describe("market API client", () => {
  const base = apiBase();

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('fetchMarketQuotes({ market: "stock" }) hits HOSE quotes', async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({ exchange: "HOSE", limit: 80, groups: [], source: "vnstock" }),
    );

    await fetchMarketQuotes({ market: "stock" });

    expect(lastFetchUrl()).toBe(`${base}/api/markets/quotes?exchange=HOSE&limit=80`);
  });

  it('fetchMarketQuotes({ market: "crypto" }) hits crypto quotes', async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({ limit: 80, groups: [], source: "coingecko" }),
    );

    await fetchMarketQuotes({ market: "crypto" });

    expect(lastFetchUrl()).toBe(`${base}/api/markets/crypto/quotes?limit=80`);
  });

  it('fetchMarketHeatmap({ market: "crypto" }) hits crypto heatmap', async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({ limit: 100, sectors: [], source: "coingecko" }),
    );

    await fetchMarketHeatmap({ market: "crypto" });

    expect(lastFetchUrl()).toBe(`${base}/api/markets/crypto/heatmap?limit=100`);
  });

  it("keeps the stock heatmap URL (default exchange and limit)", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({ exchange: "HOSE", limit: 100, sectors: [], source: "vnstock" }),
    );

    await fetchMarketHeatmap();

    expect(lastFetchUrl()).toBe(`${base}/api/markets/heatmap?exchange=HOSE&limit=100`);
  });

  it("throws on non-OK quotes HTTP", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ groups: [] }, 503));

    await expect(fetchMarketQuotes({ market: "stock" })).rejects.toThrow(/503/);
  });

  it("throws on non-OK heatmap HTTP", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ sectors: [] }, 502));

    await expect(fetchMarketHeatmap({ market: "stock" })).rejects.toThrow(/502/);
  });

  it("throws when quotes payload is missing groups", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ source: "vnstock" }));

    await expect(fetchMarketQuotes({ market: "stock" })).rejects.toThrow(/groups/i);
  });

  it("throws when heatmap payload is missing sectors", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ source: "vnstock" }));

    await expect(fetchMarketHeatmap({ market: "stock" })).rejects.toThrow(/sectors/i);
  });

  it("returns live stock heatmap payload without transforming sectors", async () => {
    const body = {
      exchange: "HOSE",
      limit: 100,
      sectors: [{ name: "Banks", stocks: [{ symbol: "VCB", name: "Vietcombank", changePct: 1.2, marketCap: 100 }] }],
      source: "vnstock",
    };
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse(body));

    await expect(fetchMarketHeatmap({ market: "stock" })).resolves.toEqual(body);
  });

  it("returns live crypto quotes payload without transforming groups", async () => {
    const body = {
      limit: 80,
      groups: [
        {
          name: "MAJOR",
          rows: [
            {
              symbol: "BTC",
              name: "Bitcoin",
              value: 1,
              change: 0,
              changePct: 0,
              open: 1,
              high: 1,
              low: 1,
              prev: 1,
            },
          ],
        },
      ],
      source: "coingecko",
    };
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse(body));

    await expect(fetchMarketQuotes({ market: "crypto" })).resolves.toEqual(body);
  });
});
