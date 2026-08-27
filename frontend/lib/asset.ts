/** Asset detail href builder + API client (BL-002). */

import { apiBase, displayCurrencyQuery } from "@/lib/api";
import { bearerHeader, readAuthToken } from "@/lib/auth";
import type { DisplayCurrency } from "@/lib/currency";
import type { AssetSearchHit } from "@/lib/portfolio";

export type AssetKind = "crypto" | "stock";

export type ChartRange = "7d" | "30d" | "90d" | "1y";

export const CHART_RANGES: { value: ChartRange; label: string }[] = [
  { value: "7d", label: "7D" },
  { value: "30d", label: "30D" },
  { value: "90d", label: "90D" },
  { value: "1y", label: "1Y" },
];

export const DEFAULT_CHART_RANGE: ChartRange = "30d";

export type AssetProfileDto = {
  description?: string | null;
  imageUrl?: string | null;
  homepage?: string | null;
  categories?: string[];
  marketCapRank?: number | null;
  genesisDate?: string | null;
  hashingAlgorithm?: string | null;
  circulatingSupply?: string | null;
  totalSupply?: string | null;
  maxSupply?: string | null;
  exchange?: string | null;
  industry?: string | null;
  country?: string | null;
  links?: Record<string, string | null | undefined>;
};

export type AssetQuoteDto = {
  price?: string | null;
  currency?: string | null;
  asOf?: string | null;
  stale?: boolean;
  source?: string | null;
  changePercent24h?: string | null;
  changePercent7d?: string | null;
  changePercent30d?: string | null;
  marketCap?: string | null;
  volume24h?: string | null;
  high24h?: string | null;
  low24h?: string | null;
  ath?: string | null;
  atl?: string | null;
  priceDisplay?: string | null;
  marketCapDisplay?: string | null;
  volume24hDisplay?: string | null;
  high24hDisplay?: string | null;
  low24hDisplay?: string | null;
  assetId?: string | null;
  symbol?: string | null;
  assetType?: string | null;
};

export type AssetFxDto = {
  status?: string | null;
  asOf?: string | null;
  rate?: string | null;
};

export type HistoryPoint = {
  t?: string | null;
  price?: string | number | null;
  priceDisplay?: string | number | null;
};

export type AssetHistoryDto = {
  assetType: AssetKind;
  symbol: string;
  assetId: string;
  range: ChartRange | string;
  nativeCurrency: string;
  displayCurrency: string;
  source?: string | null;
  stale?: boolean;
  cachedAt?: string | null;
  expiresAt?: string | null;
  points: HistoryPoint[];
  fx?: AssetFxDto | null;
};

/** Legacy history route DTO (`/api/assets/{assetId}/history`). */
export type LegacyAssetHistoryDto = {
  assetId: string;
  range: ChartRange | string;
  type: AssetKind;
  source: string;
  stale: boolean;
  cachedAt?: string | null;
  expiresAt?: string | null;
  points: HistoryPoint[];
};

export type AssetDetailDto = {
  assetType: AssetKind;
  symbol: string;
  assetId: string;
  name: string;
  nativeCurrency: string;
  displayCurrency: string;
  profile: AssetProfileDto;
  quote: AssetQuoteDto | null;
  fx?: AssetFxDto | null;
  history?: AssetHistoryDto | null;
};

export class AssetApiError extends Error {
  status: number;
  detail: string;
  authRequired: boolean;
  notFound: boolean;

  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.name = "AssetApiError";
    this.status = status;
    this.detail = detail || `HTTP ${status}`;
    this.authRequired = status === 401 || status === 403;
    this.notFound = status === 404;
  }
}

export function normalizeAssetKind(value: string | null | undefined): AssetKind | null {
  const raw = (value || "").trim().toLowerCase();
  if (raw === "crypto") return "crypto";
  if (raw === "stock") return "stock";
  return null;
}

/**
 * Asset ids are provider slugs/symbols, not filesystem paths. Keep the
 * canonical query route bounded and reject values that could become another
 * path segment or contain control characters. Unicode is allowed here: the
 * query route does not have the static-export filesystem restrictions of the
 * legacy dynamic routes.
 */
export function normalizeAssetId(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const id = value.trim();
  if (
    !id ||
    id.length > 128 ||
    id === "." ||
    id === ".." ||
    /[\u0000-\u001f\u007f]/.test(id) ||
    id.includes("/") ||
    id.includes("\\")
  ) {
    return null;
  }
  return id;
}

export type AssetRouteParams = {
  assetType: AssetKind;
  id: string;
};

/** Parse and validate `/asset?type=...&id=...` query parameters. */
export function parseAssetRouteParams(
  params: Pick<URLSearchParams, "get">,
): AssetRouteParams | null {
  const assetType = normalizeAssetKind(params.get("type"));
  const id = normalizeAssetId(params.get("id"));
  if (!assetType || !id) return null;
  return { assetType, id };
}

/** Build the canonical static-export-safe `/asset?type=...&id=...` URL. */
export function assetDetailHref(assetType: AssetKind | string, id: string): string {
  const kind = normalizeAssetKind(assetType);
  const slug = normalizeAssetId(id);
  if (!kind || !slug) return "/asset";
  return `/asset?type=${kind}&id=${encodeURIComponent(slug)}`;
}

/** Descriptive alias for callers that need to emphasize canonical routing. */
export const assetCanonicalHref = assetDetailHref;

export function parseChartRange(value: string | null | undefined): ChartRange {
  const raw = (value || "").trim().toLowerCase();
  if (raw === "7d" || raw === "30d" || raw === "90d" || raw === "1y") return raw;
  return DEFAULT_CHART_RANGE;
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

async function apiFetch<T>(
  path: string,
  options?: {
    method?: string;
    token?: string | null;
    signal?: AbortSignal;
  },
): Promise<T> {
  const token = options?.token ?? readAuthToken();
  const res = await fetch(`${apiBase()}${path}`, {
    method: options?.method ?? "GET",
    headers: {
      Accept: "application/json",
      ...bearerHeader(token),
    },
    signal: options?.signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new AssetApiError(res.status, await parseDetail(res));
  }
  return (await res.json()) as T;
}

export function assetDetailQuery(params: {
  currency: DisplayCurrency;
  range?: ChartRange | null;
}): string {
  const q = new URLSearchParams();
  q.set("currency", displayCurrencyQuery(params.currency));
  if (params.range) q.set("range", params.range);
  return q.toString();
}

export async function fetchAssetDetail(options: {
  assetType: AssetKind;
  slug: string;
  currency: DisplayCurrency;
  range?: ChartRange | null;
  token?: string | null;
  signal?: AbortSignal;
}): Promise<AssetDetailDto> {
  const qs = assetDetailQuery({
    currency: options.currency,
    range: options.range,
  });
  return apiFetch<AssetDetailDto>(
    `/api/assets/${encodeURIComponent(options.assetType)}/${encodeURIComponent(options.slug)}?${qs}`,
    { token: options.token, signal: options.signal },
  );
}

export async function fetchAssetHistory(options: {
  assetType: AssetKind;
  slug: string;
  currency: DisplayCurrency;
  range: ChartRange;
  force?: boolean;
  token?: string | null;
  signal?: AbortSignal;
}): Promise<AssetHistoryDto> {
  const qs = new URLSearchParams({
    range: options.range,
    currency: displayCurrencyQuery(options.currency),
  });
  if (options.force) qs.set("force", "true");
  return apiFetch<AssetHistoryDto>(
    `/api/assets/${encodeURIComponent(options.assetType)}/${encodeURIComponent(options.slug)}/history?${qs}`,
    { token: options.token, signal: options.signal },
  );
}

export type StatRow = { label: string; value: string };

function present(value: string | number | null | undefined): string | null {
  if (value == null) return null;
  const s = String(value).trim();
  return s === "" ? null : s;
}

/** Type-specific stats; null/empty fields are omitted. */
export function buildAssetStats(
  assetType: AssetKind,
  profile: AssetProfileDto | null | undefined,
  quote: AssetQuoteDto | null | undefined,
): StatRow[] {
  const p = profile ?? {};
  const q = quote ?? {};
  const rows: Array<[string, string | number | null | undefined]> =
    assetType === "crypto"
      ? [
          ["Rank", p.marketCapRank],
          ["Market cap", q.marketCapDisplay ?? q.marketCap],
          ["Volume 24h", q.volume24hDisplay ?? q.volume24h],
          ["Circulating supply", p.circulatingSupply],
          ["Total supply", p.totalSupply],
          ["Max supply", p.maxSupply],
          ["ATH", q.ath],
          ["ATL", q.atl],
          ["High 24h", q.high24hDisplay ?? q.high24h],
          ["Low 24h", q.low24hDisplay ?? q.low24h],
          ["Genesis", p.genesisDate],
          ["Hashing", p.hashingAlgorithm],
          ["Categories", (p.categories || []).filter(Boolean).join(", ") || null],
        ]
      : [
          ["Exchange", p.exchange],
          ["Industry", p.industry],
          ["Country", p.country],
          ["Market cap", q.marketCapDisplay ?? q.marketCap],
          ["Volume 24h", q.volume24hDisplay ?? q.volume24h],
          ["High 24h", q.high24hDisplay ?? q.high24h],
          ["Low 24h", q.low24hDisplay ?? q.low24h],
        ];

  return rows
    .map(([label, value]) => {
      const shown = present(value);
      return shown == null ? null : { label, value: shown };
    })
    .filter((row): row is StatRow => row != null);
}

/** External links from homepage + profile.links (nulls skipped). */
export function buildExternalLinks(
  profile: AssetProfileDto | null | undefined,
): { label: string; href: string }[] {
  const out: { label: string; href: string }[] = [];
  const homepage = present(profile?.homepage);
  if (homepage) out.push({ label: "Homepage", href: homepage });
  const links = profile?.links ?? {};
  for (const [key, raw] of Object.entries(links)) {
    const href = present(raw);
    if (!href) continue;
    if (homepage && href === homepage) continue;
    out.push({ label: key, href });
  }
  return out;
}

export type ChartPricePoint = {
  t: string | null;
  price: number;
};

export type ChartCandle = {
  t: string | null;
  open: number;
  high: number;
  low: number;
  close: number;
};

export type ChartMode = "line" | "candle";

export function historySeries(
  history: AssetHistoryDto | null | undefined,
  preferDisplay: boolean,
): number[] {
  return historyChartPoints(history, preferDisplay).map((p) => p.price);
}

/** Timestamped close series for interactive charts (line + candle). */
export function historyChartPoints(
  history: AssetHistoryDto | null | undefined,
  preferDisplay: boolean,
): ChartPricePoint[] {
  const points = history?.points ?? [];
  const out: ChartPricePoint[] = [];
  for (const point of points) {
    const raw = preferDisplay
      ? (point.priceDisplay ?? point.price)
      : (point.price ?? point.priceDisplay);
    if (raw == null || raw === "") continue;
    const n = Number(raw);
    if (!Number.isFinite(n)) continue;
    out.push({ t: point.t ?? null, price: n });
  }
  return out;
}

function dayKey(t: string | null): string | null {
  if (!t) return null;
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return t.slice(0, 10) || null;
  return d.toISOString().slice(0, 10);
}

/**
 * Build OHLC candles from close-only history.
 * Same-day samples become one candle; single-point days use the prior close as open.
 */
export function buildCandles(points: ChartPricePoint[]): ChartCandle[] {
  if (points.length === 0) return [];

  type Bucket = { t: string | null; prices: number[] };
  const buckets: Bucket[] = [];
  const indexByDay = new Map<string, number>();

  for (const point of points) {
    const key = dayKey(point.t);
    if (key != null && indexByDay.has(key)) {
      buckets[indexByDay.get(key)!].prices.push(point.price);
      continue;
    }
    if (key != null) indexByDay.set(key, buckets.length);
    buckets.push({ t: point.t, prices: [point.price] });
  }

  const candles: ChartCandle[] = [];
  for (let i = 0; i < buckets.length; i++) {
    const prices = buckets[i].prices;
    const close = prices[prices.length - 1];
    const open = prices.length > 1 ? prices[0] : candles.length ? candles[candles.length - 1].close : close;
    const high = Math.max(open, close, ...prices);
    const low = Math.min(open, close, ...prices);
    candles.push({ t: buckets[i].t, open, high, low, close });
  }
  return candles;
}

export function toPrefillHit(detail: AssetDetailDto): AssetSearchHit {
  return {
    symbol: detail.symbol,
    name: detail.name,
    assetId: detail.assetId,
    assetType: detail.assetType,
    currency: detail.nativeCurrency,
  };
}

export function fallbackDescription(detail: Pick<AssetDetailDto, "name" | "symbol">): string {
  return `${detail.name} (${detail.symbol}).`;
}
