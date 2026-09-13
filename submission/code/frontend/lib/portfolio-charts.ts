/** Portfolio history chart + daily PnL heatmap helpers (BL-014). */

import { apiBase } from "@/lib/api";
import { bearerHeader, readAuthToken } from "@/lib/auth";
import { parseMoney, PortfolioApiError } from "@/lib/portfolio";
import type { DisplayCurrency } from "@/lib/currency";

export const PERFORMANCE_RANGES = ["1w", "mtd", "ytd", "max"] as const;
export type PerformanceRange = (typeof PERFORMANCE_RANGES)[number];
export const DEFAULT_PERFORMANCE_RANGE: PerformanceRange = "1w";

export const PERFORMANCE_RANGE_AXIS: Record<PerformanceRange, [string, string]> = {
  "1w": ["1w ago", "Now"],
  mtd: ["MTD", "Now"],
  ytd: ["YTD", "Now"],
  max: ["Start", "Now"],
};

export function isPerformanceRange(value: string): value is PerformanceRange {
  return (PERFORMANCE_RANGES as readonly string[]).includes(value);
}

export function parsePerformanceRange(value: unknown): PerformanceRange {
  return typeof value === "string" && isPerformanceRange(value) ? value : DEFAULT_PERFORMANCE_RANGE;
}

export type PerformancePoint = {
  date: string;
  marketValue: string | null;
  currency: string | null;
};

export type PerformanceResponse = {
  range: string;
  from: string | null;
  to: string;
  startValue: string | null;
  endValue: string | null;
  change: string | null;
  changePercent: string | null;
  currency: string | null;
  points: PerformancePoint[];
};

export type SnapshotPayload = {
  totalsDisplay?: {
    currency?: string | null;
    marketValue?: string | null;
    pnl?: string | null;
  } | null;
  totalsByCurrency?: Record<string, { marketValue?: string | null; pnl?: string | null }> | null;
};

export type SnapshotDto = {
  userId: string;
  date: string;
  createdAt?: string | null;
  payload: SnapshotPayload;
};

export type ConvertToDisplay = (amount: number, nativeCurrency: string) => number | null;

export type ValuedPoint = {
  date: string;
  marketValue: number;
};

export type DailyPnlPoint = {
  date: string;
  marketValue: number;
  dailyPnl: number | null;
  dailyPnlPct: number | null;
};

export const SNAPSHOTS_EMPTY_COPY = "Daily snapshots appear after the snapshot job runs.";

/** Inclusive lookback: 53 weeks × 7 days. */
export const HEATMAP_WEEKS = 53;
export const HEATMAP_LOOKBACK_DAYS = HEATMAP_WEEKS * 7;

/** Treat |daily PnL| below this as flat (near-zero). */
export const PNL_FLAT_EPS = 1e-9;

export type PnlColorBucket =
  | "empty"
  | "flat"
  | "up-1"
  | "up-2"
  | "up-3"
  | "up-4"
  | "down-1"
  | "down-2"
  | "down-3"
  | "down-4";

/**
 * Cursor-style activity intensity (teal scale), not diverging red/green.
 *
 * |daily PnL| vs window maxAbs:
 *   empty — no snapshot or no prior day (no delta)
 *   flat  — |pnl| < 1e-9
 *   1–4   — quartiles of |pnl| / maxAbs
 * Sign is kept on the bucket name for All / Gains / Losses filtering.
 */
export const PNL_BUCKET_COLORS: Record<PnlColorBucket, string> = {
  empty: "#21262d",
  flat: "#21262d",
  "up-1": "#0a3d38",
  "up-2": "#0f5c56",
  "up-3": "#0d9488",
  "up-4": "#0fedbe",
  "down-1": "#0a3d38",
  "down-2": "#0f5c56",
  "down-3": "#0d9488",
  "down-4": "#0fedbe",
};

/** Five-step Fewer → More legend matching Cursor’s activity map. */
export const PNL_LEGEND_STEPS = ["#21262d", "#0a3d38", "#0f5c56", "#0d9488", "#0fedbe"] as const;

export type PnlHeatmapFilter = "all" | "gains" | "losses";

export function pnlBucketVisible(bucket: PnlColorBucket, filter: PnlHeatmapFilter): boolean {
  if (filter === "all") return true;
  if (bucket === "empty" || bucket === "flat") return false;
  if (filter === "gains") return bucket.startsWith("up-");
  return bucket.startsWith("down-");
}

export function pnlBucketFill(bucket: PnlColorBucket, filter: PnlHeatmapFilter): string {
  if (!pnlBucketVisible(bucket, filter)) return PNL_BUCKET_COLORS.empty;
  return PNL_BUCKET_COLORS[bucket];
}

export type HeatmapCell = {
  date: string;
  weekday: number;
  inRange: boolean;
  dailyPnl: number | null;
  dailyPnlPct: number | null;
  bucket: PnlColorBucket;
};

export type HeatmapGrid = {
  weeks: HeatmapCell[][];
  from: string;
  to: string;
  monthLabels: { weekIndex: number; label: string }[];
};

const MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_LETTER = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

export function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  );
}

async function parseDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (body.detail != null) return JSON.stringify(body.detail);
  } catch {
    // ignore
  }
  return `HTTP ${res.status}`;
}

async function authedGet<T>(
  path: string,
  options?: { token?: string | null; signal?: AbortSignal },
): Promise<T> {
  const token = options?.token ?? readAuthToken();
  const res = await fetch(`${apiBase()}${path}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
      ...bearerHeader(token),
    },
    signal: options?.signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new PortfolioApiError(res.status, await parseDetail(res));
  }
  return (await res.json()) as T;
}

export async function fetchPortfolioPerformance(options: {
  range: PerformanceRange | string;
  currency?: DisplayCurrency;
  token?: string | null;
  signal?: AbortSignal;
}): Promise<PerformanceResponse> {
  const range = parsePerformanceRange(options.range);
  const currencyQuery = options.currency ? `&currency=${encodeURIComponent(options.currency)}` : "";
  const body = await authedGet<PerformanceResponse>(`/api/portfolio/performance?range=${encodeURIComponent(range)}${currencyQuery}`, {
    token: options.token,
    signal: options.signal,
  });
  if (!body || !Array.isArray(body.points)) {
    throw new Error("Performance payload missing points");
  }
  return body;
}

export async function fetchSnapshots(options: {
  from: string;
  to: string;
  currency?: DisplayCurrency;
  token?: string | null;
  signal?: AbortSignal;
}): Promise<SnapshotDto[]> {
  const qs = new URLSearchParams({ from: options.from, to: options.to });
  if (options.currency) qs.set("currency", options.currency);
  const body = await authedGet<SnapshotDto[]>(`/api/snapshots?${qs}`, {
    token: options.token,
    signal: options.signal,
  });
  if (!Array.isArray(body)) {
    throw new Error("Snapshots payload missing list");
  }
  return body;
}

function utcYmd(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function parseIsoDate(value: string): Date {
  const [y, m, day] = value.split("-").map(Number);
  return new Date(Date.UTC(y, (m || 1) - 1, day || 1));
}

export function addUtcDays(d: Date, n: number): Date {
  const next = new Date(d.getTime());
  next.setUTCDate(next.getUTCDate() + n);
  return next;
}

export function utcToday(now: Date = new Date()): Date {
  return parseIsoDate(utcYmd(now));
}

/** Default heatmap window: today-370d … today (371 inclusive days). */
export function heatmapDateWindow(today: Date = new Date()): { from: string; to: string } {
  const to = utcToday(today);
  const from = addUtcDays(to, -(HEATMAP_LOOKBACK_DAYS - 1));
  return { from: utcYmd(from), to: utcYmd(to) };
}

function startOfSundayWeek(d: Date): Date {
  const copy = utcToday(d);
  return addUtcDays(copy, -copy.getUTCDay());
}

/**
 * Market value only — never `totalsDisplay.pnl` (that field is cumulative unrealized).
 * Prefer totalsDisplay.marketValue; else a single native totalsByCurrency bucket.
 */
export function snapshotMarketValue(payload: SnapshotPayload | null | undefined): {
  marketValue: number;
  currency: string;
} | null {
  if (!payload || typeof payload !== "object") return null;
  const display = payload.totalsDisplay;
  if (display && typeof display === "object") {
    const n = parseMoney(display.marketValue);
    const ccy = String(display.currency || "")
      .trim()
      .toUpperCase();
    if (n != null && ccy) return { marketValue: n, currency: ccy };
  }
  const totals = payload.totalsByCurrency;
  if (totals && typeof totals === "object") {
    const keys = Object.keys(totals);
    if (keys.length === 1) {
      const ccy = keys[0].trim().toUpperCase();
      const n = parseMoney(totals[keys[0]]?.marketValue);
      if (n != null && ccy) return { marketValue: n, currency: ccy };
    }
  }
  return null;
}

export function convertToSessionValue(
  amount: number,
  nativeCurrency: string,
  displayCurrency: string,
  convertToDisplay: ConvertToDisplay,
): number | null {
  const src = nativeCurrency.trim().toUpperCase();
  const dst = displayCurrency.trim().toUpperCase();
  if (!src || !dst || !Number.isFinite(amount)) return null;
  if (src === dst) return amount;
  return convertToDisplay(amount, src);
}

export function valuedPointsInDisplay(
  points: { date: string; marketValue: string | number | null; currency: string | null }[],
  displayCurrency: string,
  convertToDisplay: ConvertToDisplay,
): ValuedPoint[] {
  const out: ValuedPoint[] = [];
  for (const point of points) {
    const n = typeof point.marketValue === "number" ? point.marketValue : parseMoney(point.marketValue);
    const ccy = (point.currency || "").trim();
    if (n == null || !ccy) continue;
    const converted = convertToSessionValue(n, ccy, displayCurrency, convertToDisplay);
    if (converted == null) continue;
    out.push({ date: point.date, marketValue: converted });
  }
  return out;
}

/** Consume backend-converted points; no browser FX arithmetic. */
export function backendValuedPoints(
  points: { date: string; marketValue: string | number | null; currency: string | null }[],
  displayCurrency: string,
): ValuedPoint[] {
  const target = displayCurrency.trim().toUpperCase();
  return points.flatMap((point) => {
    const value = typeof point.marketValue === "number" ? point.marketValue : parseMoney(point.marketValue);
    const pointCurrency = (point.currency || "").trim().toUpperCase();
    return value != null && pointCurrency === target ? [{ date: point.date, marketValue: value }] : [];
  });
}

/** Day-over-day MV delta on sorted snapshot dates. First point has no delta. */
export function dailyPnlSeries(points: ValuedPoint[]): DailyPnlPoint[] {
  const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
  return sorted.map((point, index) => {
    if (index === 0) {
      return { date: point.date, marketValue: point.marketValue, dailyPnl: null, dailyPnlPct: null };
    }
    const prev = sorted[index - 1].marketValue;
    const dailyPnl = point.marketValue - prev;
    const dailyPnlPct = prev !== 0 ? dailyPnl / prev : null;
    return { date: point.date, marketValue: point.marketValue, dailyPnl, dailyPnlPct };
  });
}

export function pnlColorBucket(dailyPnl: number | null, maxAbs: number): PnlColorBucket {
  if (dailyPnl == null || !Number.isFinite(dailyPnl)) return "empty";
  const abs = Math.abs(dailyPnl);
  if (abs < PNL_FLAT_EPS) return "flat";
  const cap = maxAbs > PNL_FLAT_EPS ? maxAbs : abs;
  const ratio = abs / cap;
  const level = ratio <= 0.25 ? 1 : ratio <= 0.5 ? 2 : ratio <= 0.75 ? 3 : 4;
  return dailyPnl > 0 ? (`up-${level}` as PnlColorBucket) : (`down-${level}` as PnlColorBucket);
}

export function maxAbsDailyPnl(series: DailyPnlPoint[]): number {
  let max = 0;
  for (const point of series) {
    if (point.dailyPnl == null) continue;
    const abs = Math.abs(point.dailyPnl);
    if (abs > max) max = abs;
  }
  return max;
}

export function heatmapMonthLabels(weeks: HeatmapCell[][]): { weekIndex: number; label: string }[] {
  const labels: { weekIndex: number; label: string }[] = [];
  let lastMonth = -1;
  weeks.forEach((week, weekIndex) => {
    const first = week.find((cell) => cell.inRange) ?? week[0];
    if (!first) return;
    const month = parseIsoDate(first.date).getUTCMonth();
    if (month !== lastMonth) {
      labels.push({ weekIndex, label: MONTH_LETTER[month] ?? MONTH_SHORT[month] });
      lastMonth = month;
    }
  });
  return labels.filter((label, index, all) => index === 0 || label.weekIndex - all[index - 1].weekIndex >= 2);
}

/** 7×53 Sunday-start grid. Days without a computed delta stay `empty`. */
export function buildPnlHeatmapGrid(options: {
  today?: Date;
  series?: DailyPnlPoint[];
}): HeatmapGrid {
  const { from, to } = heatmapDateWindow(options.today);
  const toDate = parseIsoDate(to);
  const lastSunday = startOfSundayWeek(toDate);
  const firstSunday = addUtcDays(lastSunday, -7 * (HEATMAP_WEEKS - 1));
  const byDate = new Map((options.series ?? []).map((point) => [point.date, point]));
  const maxAbs = maxAbsDailyPnl(options.series ?? []);

  const weeks: HeatmapCell[][] = [];
  for (let week = 0; week < HEATMAP_WEEKS; week += 1) {
    const days: HeatmapCell[] = [];
    for (let weekday = 0; weekday < 7; weekday += 1) {
      const date = utcYmd(addUtcDays(firstSunday, week * 7 + weekday));
      const inRange = date >= from && date <= to;
      const point = byDate.get(date);
      const dailyPnl = inRange ? (point?.dailyPnl ?? null) : null;
      days.push({
        date,
        weekday,
        inRange,
        dailyPnl,
        dailyPnlPct: inRange ? (point?.dailyPnlPct ?? null) : null,
        bucket: inRange ? pnlColorBucket(dailyPnl, maxAbs) : "empty",
      });
    }
    weeks.push(days);
  }

  return { weeks, from, to, monthLabels: heatmapMonthLabels(weeks) };
}

export function snapshotsToDailyPnl(
  snapshots: SnapshotDto[],
  displayCurrency: string,
  convertToDisplay: ConvertToDisplay,
): DailyPnlPoint[] {
  const valued = snapshots
    .map((snap) => {
      const extracted = snapshotMarketValue(snap.payload);
      if (!extracted) return null;
      const converted = convertToSessionValue(
        extracted.marketValue,
        extracted.currency,
        displayCurrency,
        convertToDisplay,
      );
      if (converted == null) return null;
      return { date: snap.date, marketValue: converted };
    })
    .filter((point): point is ValuedPoint => point != null);
  return dailyPnlSeries(valued);
}

/** Compute chart deltas from snapshot payloads already converted by API. */
export function backendSnapshotsToDailyPnl(
  snapshots: SnapshotDto[],
  displayCurrency: string,
): DailyPnlPoint[] {
  const target = displayCurrency.trim().toUpperCase();
  const valued = snapshots.flatMap((snap) => {
    const extracted = snapshotMarketValue(snap.payload);
    return extracted && extracted.currency === target
      ? [{ date: snap.date, marketValue: extracted.marketValue }]
      : [];
  });
  return dailyPnlSeries(valued);
}
