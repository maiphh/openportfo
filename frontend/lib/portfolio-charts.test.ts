import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import { PortfolioApiError } from "@/lib/portfolio";
import {
  DEFAULT_PERFORMANCE_RANGE,
  HEATMAP_LOOKBACK_DAYS,
  HEATMAP_WEEKS,
  PERFORMANCE_RANGE_AXIS,
  PERFORMANCE_RANGES,
  PNL_BUCKET_COLORS,
  SNAPSHOTS_EMPTY_COPY,
  buildPnlHeatmapGrid,
  dailyPnlSeries,
  fetchPortfolioPerformance,
  fetchSnapshots,
  heatmapDateWindow,
  parseIsoDate,
  parsePerformanceRange,
  pnlColorBucket,
  snapshotMarketValue,
  snapshotsToDailyPnl,
  valuedPointsInDisplay,
} from "@/lib/portfolio-charts";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("chart range mapping", () => {
  it("defaults to 1w and keeps API tabs", () => {
    expect(DEFAULT_PERFORMANCE_RANGE).toBe("1w");
    expect([...PERFORMANCE_RANGES]).toEqual(["1w", "mtd", "ytd", "max"]);
    expect(parsePerformanceRange("ytd")).toBe("ytd");
    expect(parsePerformanceRange("1d")).toBe("1w");
    expect(parsePerformanceRange(null)).toBe("1w");
    expect(PERFORMANCE_RANGE_AXIS.mtd).toEqual(["MTD", "Now"]);
  });
});

describe("daily PnL series", () => {
  it("uses day-over-day market value, not a cumulative pnl field", () => {
    const series = dailyPnlSeries([
      { date: "2026-08-18", marketValue: 130 },
      { date: "2026-08-16", marketValue: 100 },
      { date: "2026-08-17", marketValue: 90 },
    ]);
    expect(series.map((p) => p.date)).toEqual(["2026-08-16", "2026-08-17", "2026-08-18"]);
    expect(series[0].dailyPnl).toBeNull();
    expect(series[1].dailyPnl).toBe(-10);
    expect(series[1].dailyPnlPct).toBeCloseTo(-0.1);
    expect(series[2].dailyPnl).toBe(40);
    expect(series[2].dailyPnlPct).toBeCloseTo(40 / 90);
  });

  it("snapshotMarketValue ignores totalsDisplay.pnl", () => {
    expect(
      snapshotMarketValue({
        totalsDisplay: { currency: "USD", marketValue: "200", pnl: "9999" },
      }),
    ).toEqual({ marketValue: 200, currency: "USD" });
    expect(
      snapshotMarketValue({
        totalsDisplay: { currency: "USD", pnl: "50" },
        totalsByCurrency: { USD: { marketValue: "80", pnl: "50" } },
      }),
    ).toEqual({ marketValue: 80, currency: "USD" });
    expect(snapshotMarketValue({ totalsDisplay: { pnl: "50" } })).toBeNull();
  });

  it("drops points that cannot convert when currencies differ", () => {
    const points = valuedPointsInDisplay(
      [
        { date: "2026-08-16", marketValue: "100", currency: "USD" },
        { date: "2026-08-17", marketValue: "2500000", currency: "VND" },
        { date: "2026-08-18", marketValue: "110", currency: "USD" },
      ],
      "EUR",
      (amount, native) => (native === "USD" ? amount * 0.9 : null),
    );
    expect(points).toEqual([
      { date: "2026-08-16", marketValue: 90 },
      { date: "2026-08-18", marketValue: 99 },
    ]);
  });

  it("keeps same-currency values without calling FX", () => {
    const convert = vi.fn();
    const points = valuedPointsInDisplay(
      [{ date: "2026-08-16", marketValue: "100", currency: "VND" }],
      "VND",
      convert,
    );
    expect(points).toEqual([{ date: "2026-08-16", marketValue: 100 }]);
    expect(convert).not.toHaveBeenCalled();
  });

  it("snapshotsToDailyPnl converts then diffs MV", () => {
    const series = snapshotsToDailyPnl(
      [
        {
          userId: "alice",
          date: "2026-08-16",
          payload: { totalsDisplay: { currency: "USD", marketValue: "100", pnl: "40" } },
        },
        {
          userId: "alice",
          date: "2026-08-17",
          payload: { totalsDisplay: { currency: "USD", marketValue: "130", pnl: "70" } },
        },
      ],
      "VND",
      (amount, native) => (native === "USD" ? amount * 25000 : null),
    );
    expect(series[0].dailyPnl).toBeNull();
    expect(series[1].marketValue).toBe(3_250_000);
    expect(series[1].dailyPnl).toBe(750_000);
    expect(series[1].dailyPnl).not.toBe(70 * 25000);
  });
});

describe("color buckets", () => {
  it("maps empty / flat / quartile intensity by |daily PnL|", () => {
    expect(pnlColorBucket(null, 100)).toBe("empty");
    expect(pnlColorBucket(0, 100)).toBe("flat");
    expect(pnlColorBucket(20, 100)).toBe("up-1");
    expect(pnlColorBucket(25, 100)).toBe("up-1");
    expect(pnlColorBucket(40, 100)).toBe("up-2");
    expect(pnlColorBucket(70, 100)).toBe("up-3");
    expect(pnlColorBucket(80, 100)).toBe("up-4");
    expect(pnlColorBucket(-20, 100)).toBe("down-1");
    expect(pnlColorBucket(-80, 100)).toBe("down-4");
  });

  it("uses distinct red vs green fills", () => {
    expect(PNL_BUCKET_COLORS.empty).toBe("#161b22");
    expect(PNL_BUCKET_COLORS["up-4"]).toBe("#2dd4bf");
    expect(PNL_BUCKET_COLORS["down-4"]).toBe("#ef4444");
    expect(PNL_BUCKET_COLORS["up-4"]).not.toBe(PNL_BUCKET_COLORS["down-4"]);
  });
});

describe("empty heatmap grid", () => {
  it("builds a 7×53 Sunday-start grid with muted empty cells", () => {
    const today = parseIsoDate("2026-08-19");
    const grid = buildPnlHeatmapGrid({ today, series: [] });
    expect(grid.weeks).toHaveLength(HEATMAP_WEEKS);
    expect(grid.weeks.every((week) => week.length === 7)).toBe(true);
    expect(grid.weeks.flat().every((cell) => cell.bucket === "empty")).toBe(true);
    expect(grid.weeks[0][0].weekday).toBe(0);
    expect(parseIsoDate(grid.weeks[0][0].date).getUTCDay()).toBe(0);
    expect(grid.to).toBe("2026-08-19");
    expect(SNAPSHOTS_EMPTY_COPY).toMatch(/snapshot job/);
  });

  it("uses a 371-day lookback window", () => {
    const { from, to } = heatmapDateWindow(parseIsoDate("2026-08-19"));
    expect(to).toBe("2026-08-19");
    expect(from).toBe("2025-08-14");
    expect(HEATMAP_LOOKBACK_DAYS).toBe(371);
  });

  it("colors only days that have a day-over-day delta", () => {
    const today = parseIsoDate("2026-08-19");
    const series = dailyPnlSeries([
      { date: "2026-08-17", marketValue: 100 },
      { date: "2026-08-18", marketValue: 180 },
    ]);
    const grid = buildPnlHeatmapGrid({ today, series });
    const byDate = Object.fromEntries(grid.weeks.flat().map((cell) => [cell.date, cell]));
    expect(byDate["2026-08-17"].bucket).toBe("empty");
    expect(byDate["2026-08-18"].bucket).toBe("up-4");
    expect(byDate["2026-08-18"].dailyPnl).toBe(80);
    expect(byDate["2026-08-19"].bucket).toBe("empty");
  });

  it("places month labels on week columns", () => {
    const grid = buildPnlHeatmapGrid({ today: parseIsoDate("2026-08-19") });
    expect(grid.monthLabels.length).toBeGreaterThan(0);
    expect(grid.monthLabels.some((label) => label.label === "Aug")).toBe(true);
    expect(grid.monthLabels.every((label) => label.weekIndex >= 0 && label.weekIndex < HEATMAP_WEEKS)).toBe(true);
  });
});

describe("performance + snapshot clients", () => {
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

  it("fetchPortfolioPerformance sends Bearer + range", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({
        range: "1w",
        from: "2026-08-12",
        to: "2026-08-19",
        currency: "USD",
        points: [{ date: "2026-08-18", marketValue: "100", currency: "USD" }],
      }),
    );

    await fetchPortfolioPerformance({ range: "1w" });

    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/portfolio/performance?range=1w`,
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer fake:alice",
        }),
      }),
    );
  });

  it("fetchSnapshots sends Bearer + from/to", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse([]));

    await fetchSnapshots({ from: "2025-08-13", to: "2026-08-19" });

    expect(global.fetch).toHaveBeenCalledWith(
      `${base}/api/snapshots?from=2025-08-13&to=2026-08-19`,
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer fake:alice",
        }),
      }),
    );
  });

  it("maps 401 to PortfolioApiError.authRequired", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ detail: "Missing authorization header" }, 401));

    await expect(fetchPortfolioPerformance({ range: "max" })).rejects.toMatchObject({
      name: "PortfolioApiError",
      authRequired: true,
      status: 401,
    } satisfies Partial<PortfolioApiError>);
  });
});
