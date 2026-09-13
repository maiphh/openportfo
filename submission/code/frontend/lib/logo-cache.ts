/** Browser logo URL cache shared across search / heatmap / detail / lists. */

const STORAGE_KEY = "openportfo.logoCache.v1";
const TTL_MS = 7 * 24 * 60 * 60 * 1000;

type CacheEntry = { url: string; at: number };
type CacheMap = Record<string, CacheEntry>;

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function cacheKey(assetType: string, symbol: string): string | null {
  const kind = assetType.trim().toLowerCase();
  const raw = symbol.trim();
  if (!kind || !raw) return null;
  const id = kind === "stock" ? raw.toUpperCase() : raw.toUpperCase();
  return `${kind}:${id}`;
}

function readMap(): CacheMap {
  const store = storage();
  if (!store) return {};
  try {
    const raw = store.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as CacheMap;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeMap(map: CacheMap): void {
  const store = storage();
  if (!store) return;
  try {
    store.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // quota / private mode — ignore
  }
}

export function rememberLogo(
  assetType: string | null | undefined,
  symbol: string,
  url: string | null | undefined,
): void {
  const key = cacheKey(assetType || "", symbol);
  const image = (url || "").trim();
  if (!key || !image) return;
  const map = readMap();
  map[key] = { url: image, at: Date.now() };
  writeMap(map);
}

export function lookupLogo(
  assetType: string | null | undefined,
  symbol: string,
): string | null {
  const key = cacheKey(assetType || "", symbol);
  if (!key) return null;
  const entry = readMap()[key];
  if (!entry?.url) return null;
  if (Date.now() - entry.at > TTL_MS) return null;
  return entry.url;
}

export function rememberLogosFromHeatmap(
  assetType: "crypto" | "stock",
  stocks: { symbol: string; imageUrl?: string | null }[],
): void {
  for (const stock of stocks) {
    rememberLogo(assetType, stock.symbol, stock.imageUrl);
  }
}
