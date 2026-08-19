"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { holdingCostLabel, type DisplayCurrency } from "@/lib/currency";
import {
  searchAssets,
  type AssetSearchHit,
  type HoldingMutation,
  type PortfolioLine,
} from "@/lib/portfolio";

type Mode = "create" | "edit";

/** Shared submit gate for create/edit (and BL-002 prefill tests). */
export function holdingFormCanSubmit(
  selected: AssetSearchHit | null | undefined,
  qty: string,
  avgCost: string,
): boolean {
  if (!selected) return false;
  const qtyRaw = String(qty ?? "").trim();
  const costRaw = String(avgCost ?? "").trim();
  // Reject blanks — Number("") is 0 and would otherwise look "valid".
  if (!qtyRaw || !costRaw) return false;
  const q = Number(qtyRaw);
  const c = Number(costRaw);
  return Number.isFinite(q) && q > 0 && Number.isFinite(c) && c >= 0;
}

export default function HoldingFormModal({
  open,
  mode,
  displayCurrency,
  initial,
  prefill,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  open: boolean;
  mode: Mode;
  displayCurrency: DisplayCurrency;
  initial?: PortfolioLine | null;
  /** Create-mode asset preselection (BL-002 detail CTA). Does not invent qty. */
  prefill?: AssetSearchHit | null;
  busy?: boolean;
  error?: string | null;
  onClose: () => void;
  onSubmit: (payload: HoldingMutation) => Promise<void> | void;
}) {
  const [assetType, setAssetType] = useState<"crypto" | "stock">("stock");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<AssetSearchHit[]>([]);
  const [selected, setSelected] = useState<AssetSearchHit | null>(null);
  const [qty, setQty] = useState("1");
  const [avgCost, setAvgCost] = useState("");
  const [note, setNote] = useState("");
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const lockedPrefill = mode === "create" && Boolean(prefill);

  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && initial) {
      setAssetType(initial.assetType);
      setSelected({
        symbol: initial.symbol,
        name: initial.symbol,
        assetId: initial.assetId || initial.symbol,
        assetType: initial.assetType,
      });
      setQuery(initial.symbol);
      setQty(initial.qty);
      setAvgCost(initial.avgCost);
      setNote(initial.note || "");
      setHits([]);
      setSearchError(null);
      return;
    }
    if (mode === "create" && prefill) {
      setAssetType(prefill.assetType);
      setSelected(prefill);
      setQuery(prefill.symbol);
      setQty("");
      setAvgCost("");
      setNote("");
      setHits([]);
      setSearchError(null);
      return;
    }
    setAssetType("stock");
    setQuery("");
    setHits([]);
    setSelected(null);
    setQty("1");
    setAvgCost("");
    setNote("");
    setSearchError(null);
  }, [open, mode, initial, prefill]);

  useEffect(() => {
    if (!open || mode === "edit" || lockedPrefill) return;
    const q = query.trim();
    if (q.length < 1) {
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
  }, [query, assetType, open, mode, lockedPrefill]);

  const canSubmit = useMemo(() => holdingFormCanSubmit(selected, qty, avgCost), [selected, qty, avgCost]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center bg-black/60 px-4 pt-20" onClick={onClose}>
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl border border-gray-600 bg-gray-800 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-gray-600 px-5 py-4">
          <h2 className="text-lg font-semibold text-gray-100">
            {mode === "create" ? "Add holding" : `Edit ${initial?.symbol ?? ""}`}
          </h2>
          <p className="mt-1 text-xs text-gray-500">
            Cost is entered in {displayCurrency} and converted to native units (stock VND / crypto USD) on save.
          </p>
        </div>

        <div className="space-y-4 px-5 py-4">
          {mode === "create" && !lockedPrefill && (
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
          )}

          {mode === "create" && lockedPrefill && selected ? (
            <p className="text-sm text-gray-300">
              {selected.symbol} · <span className="capitalize">{selected.assetType}</span>
              <span className="ml-2 text-xs text-gray-500">({selected.assetId})</span>
            </p>
          ) : mode === "create" ? (
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
                        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-gray-700/70"
                        onClick={() => {
                          setSelected(hit);
                          setQuery(hit.symbol);
                          setHits([]);
                        }}
                      >
                        <span className="font-medium text-gray-100">{hit.symbol}</span>
                        <span className="truncate text-xs text-gray-500">{hit.name}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {query.trim() && !searching && hits.length === 0 && !selected && !searchError && (
                <p className="mt-1 text-xs text-gray-500">No results — pick a valid catalog asset.</p>
              )}
              {selected && (
                <p className="mt-2 text-xs text-teal-400">
                  Selected {selected.symbol} ({selected.assetId})
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-300">
              {initial?.symbol} · <span className="capitalize">{initial?.assetType}</span>
            </p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="holding-qty" className="mb-1 block text-xs text-gray-500">
                Quantity
              </label>
              <input
                id="holding-qty"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
                inputMode="decimal"
                className="h-10 w-full rounded-md border border-gray-600 bg-gray-900 px-3 text-sm text-gray-200 outline-none focus:border-teal-500"
              />
            </div>
            <div>
              <label htmlFor="holding-avg-cost" className="mb-1 block text-xs text-gray-500">
                {holdingCostLabel(displayCurrency)}
              </label>
              <input
                id="holding-avg-cost"
                value={avgCost}
                onChange={(e) => setAvgCost(e.target.value)}
                inputMode="decimal"
                className="h-10 w-full rounded-md border border-gray-600 bg-gray-900 px-3 text-sm text-gray-200 outline-none focus:border-teal-500"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-gray-500">Note (optional)</label>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="h-10 w-full rounded-md border border-gray-600 bg-gray-900 px-3 text-sm text-gray-200 outline-none focus:border-teal-500"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}
        </div>

        <div className="flex justify-end gap-2 border-t border-gray-600 px-5 py-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!canSubmit || busy}
            onClick={() => {
              if (!selected) return;
              void onSubmit({
                assetType: selected.assetType,
                symbol: selected.symbol,
                assetId: selected.assetId,
                qty: String(qty).trim(),
                avgCost: String(avgCost).trim(),
                currency: displayCurrency,
                note: note.trim() || null,
              });
            }}
          >
            {busy ? "Saving…" : mode === "create" ? "Add holding" : "Save changes"}
          </Button>
        </div>
      </div>
    </div>
  );
}
