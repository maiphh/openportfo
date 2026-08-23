import type { HeatmapResponse, MarketKind, QuotesResponse } from "@/lib/api";

export type MarketsWidget = "heatmap" | "quotes";

export type MarketsCacheEntry<T> = {
  savedAt: string;
  payload: T;
};

type SessionLike = Pick<Storage, "getItem" | "setItem">;

function defaultSessionStorage(): SessionLike | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    // Private mode / blocked storage.
    return null;
  }
}

export function marketsCacheKey(widget: MarketsWidget, market: MarketKind): string {
  return `openportfo.markets.${widget}.${market}`;
}

function isIsoTimestamp(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function isCacheEnvelope(value: unknown): value is { savedAt: string; payload: unknown } {
  if (!value || typeof value !== "object") return false;
  const rec = value as { savedAt?: unknown; payload?: unknown };
  return isIsoTimestamp(rec.savedAt) && "payload" in rec;
}

export function isHeatmapPayload(value: unknown): value is HeatmapResponse {
  if (!value || typeof value !== "object") return false;
  const sectors = (value as { sectors?: unknown }).sectors;
  if (!Array.isArray(sectors)) return false;
  return sectors.some((sector) => {
    if (!sector || typeof sector !== "object") return false;
    const stocks = (sector as { stocks?: unknown }).stocks;
    return Array.isArray(stocks) && stocks.length > 0;
  });
}

export function isQuotesPayload(value: unknown): value is QuotesResponse {
  if (!value || typeof value !== "object") return false;
  const groups = (value as { groups?: unknown }).groups;
  if (!Array.isArray(groups)) return false;
  return groups.some((group) => {
    if (!group || typeof group !== "object") return false;
    const rows = (group as { rows?: unknown }).rows;
    return Array.isArray(rows) && rows.length > 0;
  });
}

export function readMarketsCache<T>(
  widget: MarketsWidget,
  market: MarketKind,
  isValidPayload: (payload: unknown) => payload is T,
  storage: SessionLike | null | undefined = defaultSessionStorage(),
): MarketsCacheEntry<T> | null {
  if (!storage) return null;
  try {
    const raw = storage.getItem(marketsCacheKey(widget, market));
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!isCacheEnvelope(parsed) || !isValidPayload(parsed.payload)) return null;
    return { savedAt: parsed.savedAt, payload: parsed.payload };
  } catch {
    return null;
  }
}

export function writeMarketsCache<T>(
  widget: MarketsWidget,
  market: MarketKind,
  payload: T,
  storage: SessionLike | null | undefined = defaultSessionStorage(),
): void {
  if (!storage) return;
  try {
    const entry: MarketsCacheEntry<T> = {
      savedAt: new Date().toISOString(),
      payload,
    };
    storage.setItem(marketsCacheKey(widget, market), JSON.stringify(entry));
  } catch {
    // Quota / private mode — live fetch still proceeds.
  }
}

export function readHeatmapCache(
  market: MarketKind,
  storage?: SessionLike | null,
): MarketsCacheEntry<HeatmapResponse> | null {
  return readMarketsCache("heatmap", market, isHeatmapPayload, storage);
}

export function writeHeatmapCache(
  market: MarketKind,
  payload: HeatmapResponse,
  storage?: SessionLike | null,
): void {
  writeMarketsCache("heatmap", market, payload, storage);
}

export function readQuotesCache(
  market: MarketKind,
  storage?: SessionLike | null,
): MarketsCacheEntry<QuotesResponse> | null {
  return readMarketsCache("quotes", market, isQuotesPayload, storage);
}

export function writeQuotesCache(
  market: MarketKind,
  payload: QuotesResponse,
  storage?: SessionLike | null,
): void {
  writeMarketsCache("quotes", market, payload, storage);
}
