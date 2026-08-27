"use client";

import { Fragment, useEffect, useLayoutEffect, useMemo, useState } from "react";
import AssetLink from "@/components/AssetLink";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { Button } from "@/components/ui/button";
import { fetchMarketQuotes, type MarketKind } from "@/lib/api";
import { convertAmount, DEFAULT_FX_BASE, nativeCurrencyForMarket } from "@/lib/currency";
import { readQuotesCache, writeQuotesCache } from "@/lib/markets-cache";
import type { QuoteGroup, QuoteRow } from "@/types/markets";
import { cn, formatPct, formatPrice, formatSigned } from "@/lib/utils";

const COLUMNS = ["Name", "Value", "Change", "Chg%", "Open", "High", "Low", "Prev"] as const;

type LoadState = "loading" | "updating" | "live" | "stale" | "error";

function toneClass(value: number) {
  if (value > 0) return "text-emerald-400";
  if (value < 0) return "text-red-500";
  return "text-gray-500";
}

function QuotesSkeleton() {
  return (
    <tbody data-testid="quotes-skeleton">
      {Array.from({ length: 8 }).map((_, row) => (
        <tr key={row} className="border-t border-gray-700">
          {COLUMNS.map((column, col) => (
            <td key={column} className="px-3 py-3">
              <div
                className={cn(
                  "h-3 animate-pulse rounded bg-gray-700/60",
                  col === 0 ? "w-28" : "ml-auto w-12",
                )}
              />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

function mapMoney(
  amount: number,
  native: string,
  display: string,
  rates: Record<string, string>,
  base: string,
): { value: number; converted: boolean } {
  if (native === display) return { value: amount, converted: true };
  const converted = convertAmount(amount, native, display, rates, base);
  if (converted == null) return { value: amount, converted: false };
  return { value: converted, converted: true };
}

function mapRow(
  row: QuoteRow,
  native: string,
  display: string,
  rates: Record<string, string>,
  base: string,
): QuoteRow & { moneyConverted: boolean } {
  const value = mapMoney(row.value, native, display, rates, base);
  const change = mapMoney(row.change, native, display, rates, base);
  const open = mapMoney(row.open, native, display, rates, base);
  const high = mapMoney(row.high, native, display, rates, base);
  const low = mapMoney(row.low, native, display, rates, base);
  const prev = mapMoney(row.prev, native, display, rates, base);
  return {
    ...row,
    value: value.value,
    change: change.value,
    open: open.value,
    high: high.value,
    low: low.value,
    prev: prev.value,
    moneyConverted: value.converted && change.converted && open.converted && high.converted && low.converted && prev.converted,
  };
}

function getAnyRowConverted(
  groups: Array<{ rows: Array<{ moneyConverted: boolean }> }>,
): boolean {
  return groups.some((g) => g.rows.some((r) => r.moneyConverted));
}

export default function MarketQuotes({ market = "stock" }: { market?: MarketKind }) {
  const { currency, rates, fxStatus } = useDisplayCurrency();
  const native = nativeCurrencyForMarket(market);
  const fxBase = rates.base?.trim() || DEFAULT_FX_BASE;
  const [groups, setGroups] = useState<QuoteGroup[]>([]);
  const [source, setSource] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useLayoutEffect(() => {
    const cached = readQuotesCache(market);
    if (cached) {
      setGroups(cached.payload.groups);
      setSource("updating");
      setError(null);
    } else {
      setGroups([]);
      setSource("loading");
      setError(null);
    }
  }, [market, reloadKey]);

  useEffect(() => {
    const controller = new AbortController();
    fetchMarketQuotes({
      market,
      limit: 80,
      signal: controller.signal,
      ...(market === "stock" ? { exchange: "HOSE" } : {}),
    })
      .then((data) => {
        if (controller.signal.aborted) return;
        const hasRows = data.groups.some((group) => group.rows.length > 0);
        if (!hasRows) {
          throw new Error("Empty quotes");
        }
        writeQuotesCache(market, data);
        setGroups(data.groups);
        setSource("live");
        setError(null);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        const cached = readQuotesCache(market);
        if (cached) {
          setGroups(cached.payload.groups);
          setSource("stale");
          setError(err instanceof Error ? err.message : "Quotes unavailable");
          return;
        }
        setGroups([]);
        setSource("error");
        setError(err instanceof Error ? err.message : "Quotes unavailable");
      });
    return () => controller.abort();
  }, [market, reloadKey]);

  const showBoard = source === "live" || source === "updating" || source === "stale";

  const displayGroups = useMemo(() => {
    return groups.map((group) => ({
      ...group,
      rows: group.rows.map((row) => mapRow(row, native, currency, rates.rates, fxBase)),
    }));
  }, [currency, fxBase, groups, native, rates.rates]);

  const conversionOk =
    native === currency || (fxStatus !== "missing" && getAnyRowConverted(displayGroups));
  const showNativeFallback = native !== currency && !conversionOk;

  return (
    <div className="w-full">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-2">
        <h3 className="text-2xl font-semibold text-gray-100">
          Market Quotes
          <span className="ml-2 text-sm font-medium text-gray-500">{currency}</span>
        </h3>
        <div className="flex items-center gap-2 text-[11px] text-gray-500">
          {source === "loading" ? (market === "crypto" ? "Loading crypto quotes…" : "Loading VN quotes…") : null}
          {source === "updating" ? "cached (updating…)" : null}
          {source === "stale" ? "cached (refresh failed)" : null}
          {source === "live" ? (market === "crypto" ? "CoinGecko" : "HOSE · vnstock") : null}
          {showNativeFallback ? ` · showing ${native} (rate unavailable)` : null}
          {source === "stale" ? (
            <Button type="button" variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          ) : null}
        </div>
      </div>
      <div className="min-w-0 max-w-full overflow-hidden rounded-lg border border-gray-600 bg-gray-800">
        {source === "error" ? (
          <div className="flex flex-col items-center justify-center gap-3 px-4 py-16 text-center" data-testid="quotes-error">
            <p className="text-sm text-gray-400">{error ?? "Quotes unavailable"}</p>
            <Button type="button" variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          </div>
        ) : (
          <div className="table-scroll" role="region" aria-label="Scrollable market quotes" tabIndex={0}>
            <table className="w-max min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-gray-600 text-gray-500">
                  {COLUMNS.map((column, index) => (
                    <th
                      key={column}
                      className={cn(
                        "px-3 py-2.5 font-medium",
                        index === 0 ? "text-left" : "text-right",
                      )}
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              {source === "loading" ? <QuotesSkeleton /> : null}
              {showBoard ? (
                <tbody>
                  {displayGroups.map((group) => (
                    <Fragment key={group.name}>
                      <tr className="bg-gray-800">
                        <td colSpan={8} className="px-3 py-2 text-[11px] font-semibold tracking-[0.14em] text-gray-500">
                          {group.name}
                        </td>
                      </tr>
                      {group.rows.map((row) => (
                        <tr key={`${group.name}-${row.symbol}`} className="border-t border-gray-700 hover:bg-gray-700/40">
                          <td className="px-3 py-2">
                            <AssetLink
                              assetType={market}
                              id={row.symbol}
                              className="flex items-center gap-2.5 text-gray-200 hover:text-teal-400"
                            >
                              <CompanyLogo symbol={row.symbol} size={20} assetType={market} />
                              <span>
                                <span className="font-medium">{row.symbol}</span>
                                <span className="ml-2 text-gray-400">{row.name}</span>
                              </span>
                            </AssetLink>
                          </td>
                          <td className="px-3 py-2 text-right tabular-nums text-gray-200">{formatPrice(row.value)}</td>
                          <td className={cn("px-3 py-2 text-right tabular-nums", toneClass(row.change))}>
                            {formatSigned(row.change)}
                          </td>
                          <td className={cn("px-3 py-2 text-right tabular-nums", toneClass(row.changePct))}>
                            {formatPct(row.changePct)}
                          </td>
                          <td className="px-3 py-2 text-right tabular-nums text-gray-400">{formatPrice(row.open)}</td>
                          <td className="px-3 py-2 text-right tabular-nums text-gray-400">{formatPrice(row.high)}</td>
                          <td className="px-3 py-2 text-right tabular-nums text-gray-400">{formatPrice(row.low)}</td>
                          <td className="px-3 py-2 text-right tabular-nums text-gray-400">{formatPrice(row.prev)}</td>
                        </tr>
                      ))}
                    </Fragment>
                  ))}
                </tbody>
              ) : null}
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
