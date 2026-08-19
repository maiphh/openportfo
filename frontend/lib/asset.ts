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
  points: HistoryPoint[];
  fx?: AssetFxDto | null;
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

/** Build `/crypto/{id}` or `/stock/{id}` for shared AssetLink click-through. */
export function assetDetailHref(assetType: AssetKind | string, id: string): string {
  const kind = normalizeAssetKind(assetType) ?? "stock";
  const slug = String(id || "").trim();
  if (!slug) return `/${kind}`;
  return `/${kind}/${encodeURIComponent(slug)}`;
}

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
  token?: string | null;
  signal?: AbortSignal;
}): Promise<AssetHistoryDto> {
  const qs = new URLSearchParams({
    range: options.range,
    currency: displayCurrencyQuery(options.currency),
  });
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

export function historySeries(
  history: AssetHistoryDto | null | undefined,
  preferDisplay: boolean,
): number[] {
  const points = history?.points ?? [];
  const values: number[] = [];
  for (const point of points) {
    const raw = preferDisplay
      ? (point.priceDisplay ?? point.price)
      : (point.price ?? point.priceDisplay);
    if (raw == null || raw === "") continue;
    const n = Number(raw);
    if (Number.isFinite(n)) values.push(n);
  }
  return values;
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
