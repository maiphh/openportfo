import { apiBase } from "@/lib/api";

/** Always-exported crypto slugs (symbol + common CoinGecko ids). */
export const CRYPTO_STATIC_SEED = [
  "btc",
  "bitcoin",
  "eth",
  "ethereum",
  "usdt",
  "tether",
  "bnb",
  "sol",
  "solana",
  "xrp",
  "ada",
  "cardano",
  "doge",
  "dogecoin",
] as const;

/** Always-exported VN stock tickers for static export. */
export const STOCK_STATIC_SEED = [
  "VNM",
  "VCB",
  "FPT",
  "HPG",
  "MWG",
  "VIC",
  "VHM",
  "MSN",
  "TCB",
  "MBB",
  "CTG",
  "BID",
  "GAS",
  "PLX",
  "SAB",
] as const;

/** Static-export path segment: ASCII only (Windows + prerender-manifest safe). */
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;

function addParam(out: Set<string>, raw: unknown) {
  if (typeof raw !== "string") return;
  const id = raw.trim();
  // Reject empty, route templates, and non-ASCII (e.g. CoinGecko display names).
  if (!id || id.includes("[") || id.includes("]") || id.includes("/") || !SAFE_ID.test(id)) {
    return;
  }
  out.add(id);
}

const BUILD_FETCH_TIMEOUT_MS = 2500;

async function fetchJson(url: string): Promise<unknown | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), BUILD_FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      // Build-time only; avoid Next fetch cache surprises during `next build`.
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function collectFromHeatmap(body: unknown, out: Set<string>) {
  if (!body || typeof body !== "object") return;
  const sectors = (body as { sectors?: unknown }).sectors;
  if (!Array.isArray(sectors)) return;
  for (const sector of sectors) {
    if (!sector || typeof sector !== "object") continue;
    const stocks = (sector as { stocks?: unknown }).stocks;
    if (!Array.isArray(stocks)) continue;
    for (const row of stocks) {
      if (!row || typeof row !== "object") continue;
      addParam(out, (row as { symbol?: unknown }).symbol);
    }
  }
}

function collectFromQuotes(body: unknown, out: Set<string>) {
  if (!body || typeof body !== "object") return;
  const groups = (body as { groups?: unknown }).groups;
  if (!Array.isArray(groups)) return;
  for (const group of groups) {
    if (!group || typeof group !== "object") continue;
    const rows = (group as { rows?: unknown }).rows;
    if (!Array.isArray(rows)) continue;
    for (const row of rows) {
      if (!row || typeof row !== "object") continue;
      addParam(out, (row as { symbol?: unknown }).symbol);
    }
  }
}

/**
 * IDs for `output: "export"` dynamic routes.
 * Prefers live public `/api/markets/*` at build time; always includes seeds.
 */
export async function buildStaticAssetParams(
  market: "crypto" | "stock",
): Promise<{ id: string }[]> {
  const ids = new Set<string>();
  const seeds = market === "crypto" ? CRYPTO_STATIC_SEED : STOCK_STATIC_SEED;
  for (const seed of seeds) addParam(ids, seed);

  const base = apiBase();
  if (market === "crypto") {
    const [heatmap, quotes] = await Promise.all([
      fetchJson(`${base}/api/markets/crypto/heatmap?limit=300`),
      fetchJson(`${base}/api/markets/crypto/quotes?limit=300`),
    ]);
    collectFromHeatmap(heatmap, ids);
    collectFromQuotes(quotes, ids);
  } else {
    const [heatmap, quotes] = await Promise.all([
      fetchJson(`${base}/api/markets/heatmap?exchange=HOSE&limit=300`),
      fetchJson(`${base}/api/markets/quotes?exchange=HOSE&limit=300`),
    ]);
    collectFromHeatmap(heatmap, ids);
    collectFromQuotes(quotes, ids);
  }

  return [...ids]
    .sort((a, b) => a.localeCompare(b))
    .map((id) => ({ id }));
}
