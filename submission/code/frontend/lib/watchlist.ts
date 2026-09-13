/** Watchlist API client (auth required). */

import { apiBase } from "@/lib/api";
import { bearerHeader, readAuthToken } from "@/lib/auth";
import { parseMoney, type ConvertToDisplay } from "@/lib/portfolio";

export type WatchlistAssetType = "crypto" | "stock";

export type WatchlistItem = {
  userId: string;
  assetType: WatchlistAssetType;
  symbol: string;
  assetId?: string | null;
  addedAt?: string | null;
  price?: string | null;
  currency?: string | null;
  asOf?: string | null;
  stale: boolean;
};

export type WatchlistAddBody = {
  assetType: WatchlistAssetType;
  symbol: string;
  assetId?: string | null;
};

export class WatchlistApiError extends Error {
  status: number;
  detail: string;
  authRequired: boolean;
  conflict: boolean;

  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.name = "WatchlistApiError";
    this.status = status;
    this.detail = detail || `HTTP ${status}`;
    this.authRequired = status === 401 || status === 403;
    this.conflict = status === 409;
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
    throw new WatchlistApiError(res.status, await parseDetail(res));
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export function watchlistItemKey(item: Pick<WatchlistItem, "assetType" | "symbol">): string {
  return `${item.assetType}:${item.symbol}`;
}

/** Convert cache-first quote to session currency; missing quote → null amount. */
export function watchlistPriceInDisplay(
  price: string | null | undefined,
  nativeCurrency: string | null | undefined,
  displayCurrency: string,
  convertToDisplay?: ConvertToDisplay,
): { amount: number | null; currency: string; missing: boolean } {
  const nativeAmt = parseMoney(price);
  const native = (nativeCurrency || "").trim() || displayCurrency;
  if (nativeAmt == null) {
    return { amount: null, currency: native, missing: true };
  }
  if (native.toUpperCase() === displayCurrency.toUpperCase()) {
    return { amount: nativeAmt, currency: displayCurrency, missing: false };
  }
  if (convertToDisplay) {
    const converted = convertToDisplay(nativeAmt, native);
    if (converted != null) {
      return { amount: converted, currency: displayCurrency, missing: false };
    }
  }
  return { amount: nativeAmt, currency: native, missing: false };
}

export async function fetchWatchlist(options?: {
  token?: string | null;
  signal?: AbortSignal;
}): Promise<WatchlistItem[]> {
  const body = await apiFetch<WatchlistItem[]>("/api/watchlist", {
    token: options?.token,
    signal: options?.signal,
  });
  return Array.isArray(body) ? body : [];
}

export async function addWatchlist(
  body: WatchlistAddBody,
  options?: { token?: string | null; signal?: AbortSignal },
): Promise<WatchlistItem> {
  return apiFetch<WatchlistItem>("/api/watchlist", {
    method: "POST",
    body,
    token: options?.token,
    signal: options?.signal,
  });
}

export async function removeWatchlist(
  assetType: string,
  symbol: string,
  options?: { token?: string | null; signal?: AbortSignal },
): Promise<void> {
  await apiFetch(
    `/api/watchlist/${encodeURIComponent(assetType)}/${encodeURIComponent(symbol)}`,
    {
      method: "DELETE",
      token: options?.token,
      signal: options?.signal,
    },
  );
}
