/** News API client + TopStories mapping (BL-007). */

import { apiBase } from "@/lib/api";
import type { AssetKind } from "@/lib/asset";
import { bearerHeader, readAuthToken } from "@/lib/auth";
import { CRYPTO_STATIC_SEED } from "@/lib/static-asset-params";

export const NEWS_DEFAULT_LIMIT = 20;

const KNOWN_CRYPTO = new Set(CRYPTO_STATIC_SEED.map((s) => s.toUpperCase()));

const SOURCE_PALETTE = [
  "#ef4444",
  "#0668e1",
  "#22c55e",
  "#f97316",
  "#fb923c",
  "#e50914",
  "#555555",
  "#76b900",
];

export class NewsApiError extends Error {
  status: number;
  detail: string;
  authRequired: boolean;

  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.name = "NewsApiError";
    this.status = status;
    this.detail = detail || `HTTP ${status}`;
    this.authRequired = status === 401 || status === 403;
  }
}

export type NewsItemDto = {
  id: string;
  title: string;
  url: string | null;
  source: string;
  publishedAt: string | null;
  symbols: string[];
  date: string | null;
};

export type LinkedSymbol = {
  /** Display ticker. */
  symbol: string;
  /** AssetLink id (stock uppercase, crypto lowercase slug). */
  id: string;
  assetType: AssetKind;
};

export type TopStory = {
  id: string;
  title: string;
  url: string | null;
  source: string;
  sourceInitial: string;
  sourceColor: string;
  publishedAt: string | null;
  timeAgo: string;
  symbols: LinkedSymbol[];
};

export function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  );
}

/** Stock if 3–4 letter VN ticker; else crypto if known; otherwise skip. */
export function inferAssetType(symbol: string): AssetKind | null {
  const raw = symbol.trim();
  if (!raw) return null;
  if (KNOWN_CRYPTO.has(raw.toUpperCase())) return "crypto";
  if (/^[A-Za-z]{3,4}$/.test(raw)) return "stock";
  return null;
}

export function linkedSymbols(symbols: unknown): LinkedSymbol[] {
  if (!Array.isArray(symbols)) return [];
  const out: LinkedSymbol[] = [];
  const seen = new Set<string>();
  for (const entry of symbols) {
    if (typeof entry !== "string") continue;
    const raw = entry.trim();
    if (!raw) continue;
    const assetType = inferAssetType(raw);
    if (!assetType) continue;
    const key = raw.toUpperCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      symbol: raw.toUpperCase(),
      id: assetType === "crypto" ? raw.toLowerCase() : raw.toUpperCase(),
      assetType,
    });
  }
  return out;
}

export function safeNewsUrl(url: unknown): string | null {
  if (typeof url !== "string") return null;
  const trimmed = url.trim();
  if (!trimmed) return null;
  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") return trimmed;
  } catch {
    return null;
  }
  return null;
}

export function sourceColor(source: string): string {
  let hash = 0;
  for (let i = 0; i < source.length; i += 1) {
    hash = (hash * 31 + source.charCodeAt(i)) >>> 0;
  }
  return SOURCE_PALETTE[hash % SOURCE_PALETTE.length];
}

export function formatTimeAgo(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return "";
  const deltaSec = Math.max(0, Math.round((now - t) / 1000));
  if (deltaSec < 60) return "just now";
  const minutes = Math.round(deltaSec / 60);
  if (minutes < 60) return minutes === 1 ? "1 minute ago" : `${minutes} minutes ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
  const days = Math.round(hours / 24);
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  return new Date(t).toISOString().slice(0, 10);
}

function publishedMs(iso: string | null): number {
  if (!iso) return 0;
  const t = Date.parse(iso);
  return Number.isFinite(t) ? t : 0;
}

export function mapNewsItem(raw: unknown, now = Date.now()): TopStory | null {
  if (!raw || typeof raw !== "object") return null;
  const item = raw as Record<string, unknown>;
  const title = typeof item.title === "string" ? item.title.trim() : "";
  if (!title) return null;
  const url = safeNewsUrl(item.url);
  const source = typeof item.source === "string" ? item.source.trim() : "";
  const publishedAt = typeof item.publishedAt === "string" && item.publishedAt.trim() ? item.publishedAt.trim() : null;
  const id =
    typeof item.id === "string" && item.id.trim()
      ? item.id.trim()
      : `${title}|${publishedAt ?? ""}|${url ?? ""}`;
  return {
    id,
    title,
    url,
    source: source || "News",
    sourceInitial: (source || "N").slice(0, 1).toUpperCase(),
    sourceColor: sourceColor(source || "News"),
    publishedAt,
    timeAgo: formatTimeAgo(publishedAt, now),
    symbols: linkedSymbols(item.symbols),
  };
}

/** Map API items; newest `publishedAt` first. Drops title-less rows. */
export function mapNewsItems(raw: unknown, now = Date.now()): TopStory[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => mapNewsItem(item, now))
    .filter((story): story is TopStory => story != null)
    .sort((a, b) => publishedMs(b.publishedAt) - publishedMs(a.publishedAt));
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

export async function fetchNews(options?: {
  limit?: number;
  token?: string | null;
  signal?: AbortSignal;
  /** Markets board: stock | crypto */
  market?: "stock" | "crypto" | null;
  /** Asset detail tokens */
  symbol?: string | null;
  name?: string | null;
  assetId?: string | null;
  assetType?: "stock" | "crypto" | null;
  /** Extra comma-joined keywords */
  q?: string | null;
}): Promise<NewsItemDto[]> {
  const token = options?.token ?? readAuthToken();
  const limit = options?.limit ?? NEWS_DEFAULT_LIMIT;
  const params = new URLSearchParams({ limit: String(limit) });
  if (options?.market) params.set("market", options.market);
  if (options?.symbol?.trim()) params.set("symbol", options.symbol.trim());
  if (options?.name?.trim()) params.set("name", options.name.trim());
  if (options?.assetId?.trim()) params.set("assetId", options.assetId.trim());
  if (options?.assetType) params.set("assetType", options.assetType);
  if (options?.q?.trim()) params.set("q", options.q.trim());
  const res = await fetch(`${apiBase()}/api/news?${params.toString()}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
      ...bearerHeader(token),
    },
    signal: options?.signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new NewsApiError(res.status, await parseDetail(res));
  }
  const body: unknown = await res.json();
  if (!Array.isArray(body)) {
    throw new NewsApiError(502, "News payload missing items");
  }
  return body as NewsItemDto[];
}
