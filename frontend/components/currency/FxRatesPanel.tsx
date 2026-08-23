"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import { X } from "lucide-react";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { Button } from "@/components/ui/button";
import { fetchAuthMe, readAuthToken } from "@/lib/auth";
import { refreshFxRates } from "@/lib/fx";
import { formatPrice } from "@/lib/utils";
import type { AuthProfileController } from "@/lib/use-auth-profile";

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

function focusableElements(root: HTMLElement | null): HTMLElement[] {
  if (!root) return [];
  return Array.from(
    root.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );
}

function trapTab(
  event: { key: string; shiftKey: boolean; preventDefault: () => void },
  root: HTMLElement | null,
): void {
  // Focus is trapped by the root key handler and the window fallback below.
  if (event.key !== "Tab") return;
  const items = focusableElements(root);
  if (items.length === 0) return;
  const first = items[0]!;
  const last = items[items.length - 1]!;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  } else if (!root?.contains(document.activeElement)) {
    event.preventDefault();
    first.focus();
  }
}

export default function FxRatesPanel({
  open,
  onClose,
  returnFocusRef,
  auth,
}: {
  open: boolean;
  onClose: () => void;
  returnFocusRef?: RefObject<HTMLElement | null>;
  auth?: AuthProfileController;
}) {
  const {
    rates,
    ratesLoading,
    ratesAuthRequired,
    ratesError,
    refreshRates,
    replaceRates,
    fxStatus,
    asOf,
  } = useDisplayCurrency();

  const [isAdmin, setIsAdmin] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const wasOpenRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    closeButtonRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (open) {
      wasOpenRef.current = true;
      return;
    }
    if (wasOpenRef.current) {
      wasOpenRef.current = false;
      returnFocusRef?.current?.focus();
    }
  }, [open, returnFocusRef]);

  useEffect(() => {
    if (!open) return;
    void refreshRates();
  }, [open, refreshRates]);

  useEffect(() => {
    if (!open) return;
    if (auth) {
      setIsAdmin(auth.profile?.role === "admin");
      return;
    }
    let cancelled = false;
    const token = readAuthToken();
    if (!token) {
      setIsAdmin(false);
      return;
    }

    void fetchAuthMe({ token })
      .then((me) => {
        if (!cancelled) setIsAdmin(me.role === "admin");
      })
      .catch(() => {
        if (!cancelled) setIsAdmin(false);
      });

    return () => {
      cancelled = true;
    };
  }, [auth, open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const onTab = (event: KeyboardEvent) => {
      trapTab(event, dialogRef.current);
    };
    window.addEventListener("keydown", onTab);
    return () => window.removeEventListener("keydown", onTab);
  }, [open]);

  async function onRefreshRates() {
    const token = readAuthToken();
    if (!token || refreshing) return;
    setRefreshing(true);
    setRefreshError(null);
    try {
      const result = await refreshFxRates({ token });
      if (result.status === 403) {
        setIsAdmin(false);
        setRefreshError("Admin only");
        return;
      }
      if (result.ok) {
        replaceRates(result.data);
        setRefreshError(null);
        return;
      }
      setRefreshError(result.error || result.data.lastRefreshError || `HTTP ${result.status}`);
    } catch {
      setRefreshError("Could not refresh rates. Showing last loaded data.");
    } finally {
      setRefreshing(false);
    }
  }

  if (!open) return null;

  const pairs = Object.entries(rates.rates).sort(([a], [b]) => a.localeCompare(b));
  const hasCachedPairs = pairs.length > 0;
  const softError = describeRatesError(ratesError);

  return (
    <div
      ref={dialogRef}
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="fx-rates-title"
      onKeyDown={(event) => trapTab(event, dialogRef.current)}
    >
      <button type="button" className="absolute inset-0 bg-black/60" aria-label="Close rates panel" onClick={onClose} />
      <div className="relative z-10 flex max-h-[min(80vh,560px)] w-full max-w-lg flex-col overflow-hidden rounded-lg border border-gray-600 bg-gray-800 shadow-xl">
        <div className="flex items-center justify-between gap-3 border-b border-gray-700 px-4 py-3">
          <div>
            <h2 id="fx-rates-title" className="text-base font-semibold text-gray-100">
              Exchange rates
            </h2>
            <p className="text-[11px] text-gray-500">
              {isAdmin ? "Stored admin rates" : "Read-only · stored admin rates"}
            </p>
          </div>
          <div className="flex items-center gap-1">
            {isAdmin ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void onRefreshRates()}
                disabled={refreshing}
                aria-busy={refreshing}
              >
                {refreshing ? "Refreshing…" : "Refresh rates"}
              </Button>
            ) : null}
            <Button ref={closeButtonRef} type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close">
              <X className="size-4" />
            </Button>
          </div>
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

          {refreshError ? (
            <p className="rounded-md border border-red-900/50 bg-gray-900/60 px-3 py-2 text-xs text-red-400">
              {refreshError}
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

          <div className="table-scroll min-w-0 rounded-md border border-gray-700" role="region" aria-label="Scrollable exchange rates" tabIndex={0}>
            <table className="w-max min-w-full text-left text-xs">
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
