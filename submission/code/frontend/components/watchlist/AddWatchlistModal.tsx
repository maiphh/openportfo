"use client";

import { useEffect, useState } from "react";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { Button } from "@/components/ui/button";
import {
  ASSET_SEARCH_DEBOUNCE_MS,
  liveSearchQuery,
  searchLiveCatalog,
} from "@/lib/asset-search";
import type { AssetSearchHit } from "@/lib/portfolio";

export default function AddWatchlistModal({
  open,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  open: boolean;
  busy?: boolean;
  error?: string | null;
  onClose: () => void;
  onSubmit: (hit: AssetSearchHit) => Promise<void> | void;
}) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<AssetSearchHit[]>([]);
  const [selected, setSelected] = useState<AssetSearchHit | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [softWarning, setSoftWarning] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setHits([]);
    setSelected(null);
    setSearchError(null);
    setSoftWarning(null);
    setSearching(false);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const q = liveSearchQuery(query);
    if (!q || selected) {
      setHits([]);
      setSoftWarning(null);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setSearching(true);
      setSearchError(null);
      setSoftWarning(null);
      try {
        const result = await searchLiveCatalog({
          q,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (result.authRequired) {
          setHits([]);
          setSearchError("Sign in required to search.");
          return;
        }
        setHits(result.hits);
        if (result.failedTypes.length === 2) {
          setSearchError("Search failed. Try again.");
        } else if (result.failedTypes.length === 1) {
          setSoftWarning(
            `${result.failedTypes[0] === "stock" ? "Stock" : "Crypto"} search failed. Showing other results.`,
          );
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        setHits([]);
        setSoftWarning(null);
        setSearchError(err instanceof Error ? err.message : "Search failed");
      } finally {
        if (!controller.signal.aborted) setSearching(false);
      }
    }, ASSET_SEARCH_DEBOUNCE_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, open, selected]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center bg-black/60 px-4 pt-20" onClick={onClose}>
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl border border-gray-600 bg-gray-800 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-gray-600 px-5 py-4">
          <h2 className="text-lg font-semibold text-gray-100">Add to watchlist</h2>
          <p className="mt-1 text-xs text-gray-500">Search the catalog and pick a VN stock or crypto. Free-text symbols are not allowed.</p>
        </div>

        <div className="space-y-4 px-5 py-4">
          <div>
            <label className="mb-1 block text-xs text-gray-500">Search asset</label>
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelected(null);
              }}
              placeholder="e.g. VNM, FPT, BTC, ethereum"
              className="h-10 w-full rounded-md border border-gray-600 bg-gray-900 px-3 text-sm text-gray-200 outline-none focus:border-teal-500"
            />
            {searching && <p className="mt-1 text-xs text-gray-500">Searching…</p>}
            {searchError && <p className="mt-1 text-xs text-red-400">{searchError}</p>}
            {!searchError && softWarning && <p className="mt-1 text-xs text-amber-400">{softWarning}</p>}
            {hits.length > 0 && !selected && (
              <ul className="mt-2 max-h-40 overflow-y-auto rounded-md border border-gray-600">
                {hits.slice(0, 12).map((hit) => (
                  <li key={`${hit.assetType}:${hit.assetId || hit.symbol}`}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-700/70"
                      onClick={() => {
                        setSelected(hit);
                        setQuery(hit.symbol);
                        setHits([]);
                        setSoftWarning(null);
                      }}
                    >
                      <CompanyLogo symbol={hit.symbol} size={18} assetType={hit.assetType} />
                      <span className="font-medium text-gray-100">{hit.symbol}</span>
                      <span className="min-w-0 flex-1 truncate text-xs text-gray-500">{hit.name}</span>
                      <span className="rounded bg-gray-700 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                        {hit.assetType === "crypto" ? "Crypto" : "Stock"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {query.trim() && !searching && hits.length === 0 && !selected && !searchError && (
              <p className="mt-1 text-xs text-gray-500">No results — pick a valid catalog asset.</p>
            )}
            {selected && (
              <p className="mt-2 flex items-center gap-2 text-xs text-teal-400">
                <CompanyLogo symbol={selected.symbol} size={16} assetType={selected.assetType} />
                Selected {selected.symbol} ({selected.assetId})
              </p>
            )}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}
        </div>

        <div className="flex justify-end gap-2 border-t border-gray-600 px-5 py-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!selected || busy}
            onClick={() => {
              if (!selected) return;
              void onSubmit(selected);
            }}
          >
            {busy ? "Adding…" : "Add to watchlist"}
          </Button>
        </div>
      </div>
    </div>
  );
}
