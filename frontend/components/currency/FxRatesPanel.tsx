"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { Button } from "@/components/ui/button";
import { formatPrice } from "@/lib/utils";

function formatAsOf(asOf: string | null): string {
  if (!asOf) return "—";
  const d = new Date(asOf);
  return Number.isNaN(d.getTime()) ? asOf : d.toLocaleString();
}

function formatFxRate(rate: string): string {
  const n = Number(rate);
  return Number.isFinite(n) ? formatPrice(n) : rate;
}

function describeRatesError(ratesError: string | null): string | null {
  if (!ratesError) return null;
  if (ratesError === "auth_required") return null; // handled by auth banner
  if (ratesError.startsWith("http_")) return `Could not refresh rates (${ratesError.replace("http_", "HTTP ")}). Showing last loaded data.`;
  if (ratesError === "fetch_failed") return "Could not refresh rates. Showing last loaded data.";
  return `Could not refresh rates (${ratesError}). Showing last loaded data.`;
}

export default function FxRatesPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const {
    rates,
    ratesLoading,
    ratesAuthRequired,
    ratesError,
    refreshRates,
    fxStatus,
    asOf,
  } = useDisplayCurrency();

  useEffect(() => {
    if (!open) return;
    void refreshRates();
  }, [open, refreshRates]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const pairs = Object.entries(rates.rates).sort(([a], [b]) => a.localeCompare(b));
  const hasCachedPairs = pairs.length > 0;
  const softError = describeRatesError(ratesError);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="fx-rates-title">
      <button type="button" className="absolute inset-0 bg-black/60" aria-label="Close rates panel" onClick={onClose} />
      <div className="relative z-10 flex max-h-[min(80vh,560px)] w-full max-w-lg flex-col overflow-hidden rounded-lg border border-gray-600 bg-gray-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-700 px-4 py-3">
          <div>
            <h2 id="fx-rates-title" className="text-base font-semibold text-gray-100">
              Exchange rates
            </h2>
            <p className="text-[11px] text-gray-500">Read-only · stored admin rates</p>
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X className="size-4" />
          </Button>
        </div>

        <div className="space-y-3 overflow-y-auto px-4 py-3 text-sm">
          {ratesAuthRequired ? (
            <p className="rounded-md border border-gray-600 bg-gray-900/60 px-3 py-2 text-gray-400">
              {hasCachedPairs
                ? "Sign in to refresh rates. Showing last loaded rates below."
                : "Sign in to view stored FX rates."}
            </p>
          ) : null}

          {!ratesAuthRequired && softError ? (
            <p className="rounded-md border border-gray-600 bg-gray-900/60 px-3 py-2 text-xs text-amber-400/90">
              {softError}
            </p>
          ) : null}

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
            <div>
              <dt className="text-gray-500">Status</dt>
              <dd className="font-medium text-gray-200">{ratesLoading ? "loading…" : fxStatus || "missing"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">As of</dt>
              <dd className="font-medium text-gray-200">{formatAsOf(asOf)}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Base</dt>
              <dd className="font-medium text-gray-200">{rates.base ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Provider</dt>
              <dd className="font-medium text-gray-200">{rates.provider ?? "—"}</dd>
            </div>
          </dl>

          {rates.lastRefreshError ? (
            <p className="text-xs text-red-500">Last refresh error: {rates.lastRefreshError}</p>
          ) : null}

          <div className="overflow-hidden rounded-md border border-gray-700">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-900/50 text-gray-500">
                <tr>
                  <th className="px-3 py-2 font-medium">Pair</th>
                  <th className="px-3 py-2 text-right font-medium">Rate</th>
                </tr>
              </thead>
              <tbody>
                {pairs.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="px-3 py-4 text-center text-gray-500">
                      {ratesAuthRequired ? "No rates (auth required)" : "No rates available"}
                    </td>
                  </tr>
                ) : (
                  pairs.map(([pair, rate]) => (
                    <tr key={pair} className="border-t border-gray-700">
                      <td className="px-3 py-2 font-medium text-gray-200">{pair}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-gray-300">
                        {formatFxRate(rate)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
