/** App-shell live search: dual stock+crypto via existing `searchAssets`. */

import {
  PortfolioApiError,
  searchAssets,
  type AssetSearchHit,
} from "@/lib/portfolio";

export const ASSET_SEARCH_DEBOUNCE_MS = 250;

export const ASSET_SEARCH_TYPES = ["stock", "crypto"] as const;

export type LiveSearchType = (typeof ASSET_SEARCH_TYPES)[number];

export type LiveSearchOutcome = {
  hits: AssetSearchHit[];
  failedTypes: LiveSearchType[];
  authRequired: boolean;
};

/** Trimmed query, or null when the dialog must not fetch. */
export function liveSearchQuery(raw: string): string | null {
  const q = raw.trim();
  return q.length > 0 ? q : null;
}

function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  );
}

function parseOptionalNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value !== "string" || value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/** Quotes are optional on the search DTO — never invent mock prices. */
export function optionalSearchQuote(hit: AssetSearchHit): {
  price: number | null;
  changePct: number | null;
} {
  const row = hit as AssetSearchHit & {
    price?: unknown;
    value?: unknown;
    priceDisplay?: unknown;
    changePct?: unknown;
  };
  return {
    price: parseOptionalNumber(row.price ?? row.value ?? row.priceDisplay),
    changePct: parseOptionalNumber(row.changePct),
  };
}

export function searchResultKey(hit: AssetSearchHit): string {
  return `${hit.assetType}:${hit.assetId || hit.symbol}`;
}

export function searchResultLinkId(hit: AssetSearchHit): string {
  return hit.assetId || hit.symbol;
}

/**
 * Parallel GET `/api/assets/search?q&type=stock|crypto`.
 * Empty `q` does not fetch. 401 → `authRequired` (no mock hits).
 * One type failing still returns the other.
 */
export async function searchLiveCatalog(options: {
  q: string;
  token?: string | null;
  signal?: AbortSignal;
}): Promise<LiveSearchOutcome> {
  const q = liveSearchQuery(options.q);
  if (!q) {
    return { hits: [], failedTypes: [], authRequired: false };
  }

  const settled = await Promise.allSettled(
    ASSET_SEARCH_TYPES.map((type) =>
      searchAssets({
        q,
        type,
        token: options.token,
        signal: options.signal,
      }),
    ),
  );

  if (options.signal?.aborted) {
    throw new DOMException("Aborted", "AbortError");
  }

  const hits: AssetSearchHit[] = [];
  const failedTypes: LiveSearchType[] = [];
  let authRequired = false;

  settled.forEach((result, index) => {
    const type = ASSET_SEARCH_TYPES[index];
    if (result.status === "fulfilled") {
      hits.push(...result.value);
      return;
    }
    if (isAbortError(result.reason)) {
      throw result.reason;
    }
    if (result.reason instanceof PortfolioApiError && result.reason.authRequired) {
      authRequired = true;
      return;
    }
    failedTypes.push(type);
  });

  if (authRequired) {
    return { hits: [], failedTypes: [], authRequired: true };
  }

  return { hits, failedTypes, authRequired: false };
}
