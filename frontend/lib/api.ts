import type { HeatmapSector, QuoteGroup, QuoteRow } from "@/lib/mock-data";

export type { QuoteGroup, QuoteRow };

const DEFAULT_API = "http://127.0.0.1:8000";

export type MarketKind = "stock" | "crypto";

export function apiBase(): string {
  const raw = (process.env.NEXT_PUBLIC_API_URL || DEFAULT_API).trim();
  return raw.replace(/\/$/, "");
}

export type HeatmapResponse = {
  exchange?: string;
  limit: number;
  sectors: HeatmapSector[];
  source: string;
};

export type QuotesResponse = {
  exchange?: string;
  limit: number;
  groups: QuoteGroup[];
  source: string;
};

type MarketFetchOptions = {
  market?: MarketKind;
  exchange?: string;
  limit?: number;
  signal?: AbortSignal;
};

async function getJson<T>(url: string, signal?: AbortSignal, label = "Request"): Promise<T> {
  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`${label} HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function fetchMarketHeatmap(options?: MarketFetchOptions): Promise<HeatmapResponse> {
  const market = options?.market ?? "stock";
  const limit = options?.limit ?? 100;
  const url =
    market === "crypto"
      ? `${apiBase()}/api/markets/crypto/heatmap?limit=${limit}`
      : `${apiBase()}/api/markets/heatmap?exchange=${encodeURIComponent(options?.exchange ?? "HOSE")}&limit=${limit}`;
  const body = await getJson<HeatmapResponse>(url, options?.signal, "Heatmap");
  if (!body || !Array.isArray(body.sectors)) {
    throw new Error("Heatmap payload missing sectors");
  }
  return body;
}

export async function fetchMarketQuotes(options?: MarketFetchOptions): Promise<QuotesResponse> {
  const market = options?.market ?? "stock";
  const limit = options?.limit ?? 80;
  const url =
    market === "crypto"
      ? `${apiBase()}/api/markets/crypto/quotes?limit=${limit}`
      : `${apiBase()}/api/markets/quotes?exchange=${encodeURIComponent(options?.exchange ?? "HOSE")}&limit=${limit}`;
  const body = await getJson<QuotesResponse>(url, options?.signal, "Quotes");
  if (!body || !Array.isArray(body.groups)) {
    throw new Error("Quotes payload missing groups");
  }
  return body;
}
