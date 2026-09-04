import type { DisplayCurrency } from "@/lib/currency";
import type { HeatmapSector, QuoteGroup, QuoteRow } from "@/types/markets";

export type { HeatmapSector, QuoteGroup, QuoteRow };

const DEFAULT_API = "http://127.0.0.1:8000";

export type MarketKind = "stock" | "crypto";

function isLocalBrowserHost(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

export function apiBase(): string {
  // BL-031 single-EB hosting: an explicitly empty NEXT_PUBLIC_API_URL means
  // same-origin (relative `/api/*`). Unset falls back to local only on
  // localhost / non-browser; public hosts use same-origin so a missed bake
  // cannot point the browser at loopback (Private Network Access block).
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (raw === undefined || raw === null) {
    if (typeof window !== "undefined" && !isLocalBrowserHost()) return "";
    return DEFAULT_API;
  }
  const trimmed = raw.trim();
  if (trimmed === "") return "";
  return trimmed.replace(/\/+$/, "");
}

/** Query value for portfolio `displayCurrency` / asset `currency` (BL-001/002). */
export function displayCurrencyQuery(currency: DisplayCurrency): string {
  return currency;
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
