import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import {
  fetchNews,
  formatTimeAgo,
  inferAssetType,
  linkedSymbols,
  mapNewsItem,
  mapNewsItems,
  NEWS_DEFAULT_LIMIT,
  NewsApiError,
  safeNewsUrl,
} from "@/lib/news";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("inferAssetType / linkedSymbols", () => {
  it("treats 3–4 letter tickers as stock", () => {
    expect(inferAssetType("VNM")).toBe("stock");
    expect(inferAssetType("VCB")).toBe("stock");
    expect(inferAssetType("FPT")).toBe("stock");
    expect(inferAssetType("AAPL")).toBe("stock");
    expect(inferAssetType("vnm")).toBe("stock");
  });

  it("treats known crypto symbols as crypto even when 3–4 letters", () => {
    expect(inferAssetType("BTC")).toBe("crypto");
    expect(inferAssetType("eth")).toBe("crypto");
    expect(inferAssetType("USDT")).toBe("crypto");
    expect(inferAssetType("bitcoin")).toBe("crypto");
    expect(inferAssetType("sol")).toBe("crypto");
  });

  it("skips unknown symbols", () => {
    expect(inferAssetType("GOOGL")).toBeNull();
    expect(inferAssetType("UNKNOWN")).toBeNull();
    expect(inferAssetType("X")).toBeNull();
    expect(inferAssetType("")).toBeNull();
    expect(inferAssetType("BTC-USD")).toBeNull();
  });

  it("keeps only inferable unique symbols", () => {
    expect(linkedSymbols(["VNM", "BTC", "GOOGL", "vnm", "", 12, "bitcoin"])).toEqual([
      { symbol: "VNM", id: "VNM", assetType: "stock" },
      { symbol: "BTC", id: "btc", assetType: "crypto" },
      { symbol: "BITCOIN", id: "bitcoin", assetType: "crypto" },
    ]);
    expect(linkedSymbols(undefined)).toEqual([]);
  });
});

describe("mapNewsItems", () => {
  const now = Date.parse("2026-08-19T12:00:00Z");

  it("maps title, url, source, publishedAt, symbols", () => {
    const story = mapNewsItem(
      {
        id: "n1",
        title: "Vinamilk expands",
        url: "https://cafef.vn/vnm",
        source: "CafeF",
        publishedAt: "2026-08-19T10:00:00Z",
        symbols: ["VNM", "????"],
      },
      now,
    );
    expect(story).toMatchObject({
      id: "n1",
      title: "Vinamilk expands",
      url: "https://cafef.vn/vnm",
      source: "CafeF",
      sourceInitial: "C",
      publishedAt: "2026-08-19T10:00:00Z",
      timeAgo: "2 hours ago",
      symbols: [{ symbol: "VNM", id: "VNM", assetType: "stock" }],
    });
    expect(story?.sourceColor).toMatch(/^#/);
  });

  it("renders missing url as null (not a broken link)", () => {
    expect(safeNewsUrl("")).toBeNull();
    expect(safeNewsUrl("javascript:alert(1)")).toBeNull();
    expect(safeNewsUrl("not-a-url")).toBeNull();
    expect(mapNewsItem({ title: "No link", url: "" }, now)?.url).toBeNull();
    expect(mapNewsItem({ title: "No link" }, now)?.url).toBeNull();
  });

  it("sorts newest first and drops title-less rows", () => {
    const mapped = mapNewsItems(
      [
        { id: "old", title: "Older", publishedAt: "2026-08-17T00:00:00Z" },
        { id: "bad", title: "   " },
        { id: "new", title: "Newer", publishedAt: "2026-08-19T00:00:00Z" },
        { id: "mid", title: "Middle", publishedAt: "2026-08-18T00:00:00Z" },
      ],
      now,
    );
    expect(mapped.map((s) => s.id)).toEqual(["new", "mid", "old"]);
  });

  it("never seeds mock TOP_STORIES headlines", () => {
    expect(mapNewsItems([])).toEqual([]);
    expect(mapNewsItems(undefined)).toEqual([]);
    const titles = mapNewsItems([]).map((s) => s.title).join(" ");
    expect(titles).not.toMatch(/UNTREE|Robot Maker|Legal Nightmare/i);
  });
});

describe("formatTimeAgo", () => {
  const now = Date.parse("2026-08-19T12:00:00Z");

  it("formats relative buckets", () => {
    expect(formatTimeAgo("2026-08-19T11:59:40Z", now)).toBe("just now");
    expect(formatTimeAgo("2026-08-19T11:58:00Z", now)).toBe("2 minutes ago");
    expect(formatTimeAgo("2026-08-19T11:00:00Z", now)).toBe("1 hour ago");
    expect(formatTimeAgo("2026-08-18T12:00:00Z", now)).toBe("yesterday");
    expect(formatTimeAgo("2026-08-15T12:00:00Z", now)).toBe("4 days ago");
    expect(formatTimeAgo("not-a-date", now)).toBe("");
    expect(formatTimeAgo(null, now)).toBe("");
  });
});

describe("fetchNews", () => {
  const base = apiBase();

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("GETs /api/news with limit and Bearer token", async () => {
    sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse([]));

    await fetchNews({ limit: 12 });

    const [url, init] = vi.mocked(global.fetch).mock.calls[0] ?? [];
    expect(String(url)).toBe(`${base}/api/news?limit=12`);
    expect((init as RequestInit).headers).toMatchObject({
      Accept: "application/json",
      Authorization: "Bearer fake:alice",
    });
    expect((init as RequestInit).cache).toBe("no-store");
  });

  it("uses the default limit when omitted", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse([]));
    await fetchNews();
    expect(String(vi.mocked(global.fetch).mock.calls[0]?.[0])).toBe(
      `${base}/api/news?limit=${NEWS_DEFAULT_LIMIT}`,
    );
  });

  it("maps 401 to NewsApiError.authRequired and does not return mock items", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({ detail: "Missing authorization header" }, 401),
    );

    const pending = fetchNews();
    await expect(pending).rejects.toMatchObject({
      name: "NewsApiError",
      authRequired: true,
      status: 401,
    } satisfies Partial<NewsApiError>);
    await expect(pending).rejects.toBeInstanceOf(NewsApiError);
    expect(mapNewsItems([])).toEqual([]);
  });

  it("maps 403 as auth required", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ detail: "Forbidden" }, 403));
    await expect(fetchNews()).rejects.toMatchObject({ authRequired: true, status: 403 });
  });

  it("throws on non-OK without treating it as auth", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ detail: "down" }, 503));
    await expect(fetchNews()).rejects.toMatchObject({
      name: "NewsApiError",
      authRequired: false,
      status: 503,
    });
  });

  it("throws when payload is not an array", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ items: [] }));
    await expect(fetchNews()).rejects.toThrow(/items/i);
  });
});
