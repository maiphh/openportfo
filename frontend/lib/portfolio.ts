/** Portfolio + holdings API client (auth required). */

import { apiBase, displayCurrencyQuery } from "@/lib/api";
import { bearerHeader, readAuthToken } from "@/lib/auth";
import type { DisplayCurrency } from "@/lib/currency";

export type AssetTypeFilter = "all" | "crypto" | "stock";

export type PortfolioLine = {
  userId: string;
  assetType: "crypto" | "stock";
  symbol: string;
  assetId?: string | null;
  qty: string;
  avgCost: string;
  currency: string;
  note?: string | null;
  price?: string | null;
  marketValue?: string | null;
  costBasis?: string | null;
  pnl?: string | null;
  pnlPercent?: string | null;
  missingPrice: boolean;
  stale: boolean;
  displayCurrency?: string | null;
  marketValueDisplay?: string | null;
  costBasisDisplay?: string | null;
  pnlDisplay?: string | null;
  allocation?: string | null;
};

export type CurrencyTotalsDto = {
  marketValue?: string | null;
  costBasis?: string | null;
  pnl?: string | null;
  pnlPercent?: string | null;
};

export type PortfolioResponse = {
  lines: PortfolioLine[];
  totalsByCurrency: Record<string, CurrencyTotalsDto>;
  totalsByAssetClass?: Record<string, CurrencyTotalsDto & { currency?: string }>;
  totalsDisplay?: (CurrencyTotalsDto & { currency?: string }) | null;
  fx: {
    status: string;
    asOf?: string | null;
    rates: Record<string, string>;
  };
  asOf?: string | null;
  displayCurrency?: string | null;
};

export type AssetSearchHit = {
  symbol: string;
  name: string;
  assetId: string;
  assetType: "crypto" | "stock";
  currency?: string | null;
};

export type HoldingMutation = {
  assetType: "crypto" | "stock";
  symbol: string;
  assetId?: string | null;
  qty: string;
  avgCost: string;
  currency: string;
  note?: string | null;
};

export class PortfolioApiError extends Error {
  status: number;
  detail: string;
  authRequired: boolean;

  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.name = "PortfolioApiError";
    this.status = status;
    this.detail = detail || `HTTP ${status}`;
    this.authRequired = status === 401 || status === 403;
  }
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
    body?: unknown;
    signal?: AbortSignal;
  },
): Promise<T> {
  const token = options?.token ?? readAuthToken();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...bearerHeader(token),
  };
  if (options?.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${apiBase()}${path}`, {
    method: options?.method ?? "GET",
    headers,
    body: options?.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options?.signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new PortfolioApiError(res.status, await parseDetail(res));
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export function portfolioQuery(params: {
  displayCurrency: DisplayCurrency;
  assetType?: AssetTypeFilter;
}): string {
  const q = new URLSearchParams();
  q.set("displayCurrency", displayCurrencyQuery(params.displayCurrency));
  if (params.assetType && params.assetType !== "all") {
    q.set("assetType", params.assetType);
  }
  return q.toString();
}

export async function fetchPortfolio(options: {
  displayCurrency: DisplayCurrency;
  assetType?: AssetTypeFilter;
  token?: string | null;
  signal?: AbortSignal;
}): Promise<PortfolioResponse> {
  const qs = portfolioQuery({
    displayCurrency: options.displayCurrency,
    assetType: options.assetType,
  });
  return apiFetch<PortfolioResponse>(`/api/portfolio?${qs}`, {
    token: options.token,
    signal: options.signal,
  });
}

export async function refreshPortfolio(options: {
  displayCurrency: DisplayCurrency;
  assetType?: AssetTypeFilter;
  token?: string | null;
  signal?: AbortSignal;
}): Promise<PortfolioResponse> {
  const qs = portfolioQuery({
    displayCurrency: options.displayCurrency,
    assetType: options.assetType,
  });
  return apiFetch<PortfolioResponse>(`/api/portfolio/refresh?${qs}`, {
    method: "POST",
    token: options.token,
    signal: options.signal,
  });
}

export async function searchAssets(options: {
  q: string;
  type: "crypto" | "stock";
  token?: string | null;
  signal?: AbortSignal;
}): Promise<AssetSearchHit[]> {
  const qs = new URLSearchParams({
    q: options.q,
    type: options.type,
  });
  return apiFetch<AssetSearchHit[]>(`/api/assets/search?${qs}`, {
    token: options.token,
    signal: options.signal,
  });
}

export async function createHolding(
  body: HoldingMutation,
  options?: { token?: string | null; signal?: AbortSignal },
): Promise<unknown> {
  return apiFetch("/api/holdings", {
    method: "POST",
    body,
    token: options?.token,
    signal: options?.signal,
  });
}

export async function updateHolding(
  assetType: string,
  symbol: string,
  body: Partial<Pick<HoldingMutation, "qty" | "avgCost" | "currency" | "note" | "assetId">>,
  options?: { token?: string | null; signal?: AbortSignal },
): Promise<unknown> {
  return apiFetch(`/api/holdings/${encodeURIComponent(assetType)}/${encodeURIComponent(symbol)}`, {
    method: "PUT",
    body,
    token: options?.token,
    signal: options?.signal,
  });
}

export async function deleteHolding(
  assetType: string,
  symbol: string,
  options?: { token?: string | null; signal?: AbortSignal },
): Promise<void> {
  await apiFetch(`/api/holdings/${encodeURIComponent(assetType)}/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
    token: options?.token,
    signal: options?.signal,
  });
}

export function parseMoney(value: string | null | undefined): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/** Slice angles for a simple SVG pie (values must be >= 0). */
export function pieSlices(
  items: { key: string; value: number; color: string }[],
): { key: string; color: string; startAngle: number; endAngle: number; value: number }[] {
  const positive = items.filter((i) => i.value > 0);
  const total = positive.reduce((sum, i) => sum + i.value, 0);
  if (total <= 0) return [];
  let angle = -90;
  return positive.map((item) => {
    const sweep = (item.value / total) * 360;
    const startAngle = angle;
    const endAngle = angle + sweep;
    angle = endAngle;
    return { key: item.key, color: item.color, startAngle, endAngle, value: item.value };
  });
}

export function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

export function describeDonutSlice(
  cx: number,
  cy: number,
  outerR: number,
  innerR: number,
  startAngle: number,
  endAngle: number,
): string {
  const large = endAngle - startAngle > 180 ? 1 : 0;
  const oStart = polarToCartesian(cx, cy, outerR, endAngle);
  const oEnd = polarToCartesian(cx, cy, outerR, startAngle);
  const iStart = polarToCartesian(cx, cy, innerR, startAngle);
  const iEnd = polarToCartesian(cx, cy, innerR, endAngle);
  return [
    `M ${oStart.x} ${oStart.y}`,
    `A ${outerR} ${outerR} 0 ${large} 0 ${oEnd.x} ${oEnd.y}`,
    `L ${iStart.x} ${iStart.y}`,
    `A ${innerR} ${innerR} 0 ${large} 1 ${iEnd.x} ${iEnd.y}`,
    "Z",
  ].join(" ");
}
