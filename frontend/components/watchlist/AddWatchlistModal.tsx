"use client";

import { useEffect, useState } from "react";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { Button } from "@/components/ui/button";
import { searchAssets, type AssetSearchHit } from "@/lib/portfolio";

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
  const [assetType, setAssetType] = useState<"crypto" | "stock">("stock");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<AssetSearchHit[]>([]);
  const [selected, setSelected] = useState<AssetSearchHit | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (!open) return;
    setAssetType("stock");
    setQuery("");
    setHits([]);
    setSelected(null);
    setSearchError(null);
    setSearching(false);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    if (q.length < 1 || selected) {
      setHits([]);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setSearching(true);
      setSearchError(null);
      try {
        const results = await searchAssets({
          q,
          type: assetType,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setHits(results);
      } catch (err) {
        if (controller.signal.aborted) return;
        setHits([]);
        setSearchError(err instanceof Error ? err.message : "Search failed");
      } finally {
        if (!controller.signal.aborted) setSearching(false);
      }
    }, 250);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, assetType, open, selected]);

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
          <div className="flex gap-2">
            {(["stock", "crypto"] as const).map((t) => (
              <Button
                key={t}
                type="button"
                size="sm"
                variant={assetType === t ? "default" : "outline"}
                onClick={() => {
                  setAssetType(t);
                  setSelected(null);
                  setHits([]);
                }}
              >
                {t === "stock" ? "VN stock" : "Crypto"}
              </Button>
            ))}
          </div>

          <div>
            <label className="mb-1 block text-xs text-gray-500">Search asset</label>
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelected(null);
              }}
              placeholder={assetType === "stock" ? "e.g. VNM, FPT" : "e.g. BTC, ethereum"}
              className="h-10 w-full rounded-md border border-gray-600 bg-gray-900 px-3 text-sm text-gray-200 outline-none focus:border-teal-500"
            />
            {searching && <p className="mt-1 text-xs text-gray-500">Searching…</p>}
            {searchError && <p className="mt-1 text-xs text-red-400">{searchError}</p>}
            {hits.length > 0 && !selected && (
              <ul className="mt-2 max-h-40 overflow-y-auto rounded-md border border-gray-600">
                {hits.slice(0, 12).map((hit) => (
                  <li key={`${hit.assetType}:${hit.assetId}`}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-700/70"
                      onClick={() => {
                        setSelected(hit);
                        setQuery(hit.symbol);
                        setHits([]);
                      }}
                    >
                      <CompanyLogo symbol={hit.symbol} size={18} assetType={hit.assetType} />
                      <span className="font-medium text-gray-100">{hit.symbol}</span>
                      <span className="min-w-0 flex-1 truncate text-xs text-gray-500">{hit.name}</span>
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
