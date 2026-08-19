"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { fetchMarketQuotes, type MarketKind } from "@/lib/api";
import { convertAmount, nativeCurrencyForMarket } from "@/lib/currency";
import { CRYPTO_QUOTE_GROUPS, QUOTE_GROUPS, type QuoteGroup, type QuoteRow } from "@/lib/mock-data";
import { cn, formatPct, formatPrice, formatSigned } from "@/lib/utils";

const COLUMNS = ["Name", "Value", "Change", "Chg%", "Open", "High", "Low", "Prev"] as const;

function toneClass(value: number) {
  if (value > 0) return "text-emerald-400";
  if (value < 0) return "text-red-500";
  return "text-gray-500";
}

function mockGroups(market: MarketKind) {
  return market === "crypto" ? CRYPTO_QUOTE_GROUPS : QUOTE_GROUPS;
}

function mapMoney(
  amount: number,
  native: string,
  display: string,
  rates: Record<string, string>,
): { value: number; converted: boolean } {
  if (native === display) return { value: amount, converted: true };
  const converted = convertAmount(amount, native, display, rates);
  if (converted == null) return { value: amount, converted: false };
  return { value: converted, converted: true };
}

function mapRow(
  row: QuoteRow,
  native: string,
  display: string,
  rates: Record<string, string>,
): QuoteRow & { moneyConverted: boolean } {
  const value = mapMoney(row.value, native, display, rates);
  const change = mapMoney(row.change, native, display, rates);
  const open = mapMoney(row.open, native, display, rates);
  const high = mapMoney(row.high, native, display, rates);
  const low = mapMoney(row.low, native, display, rates);
  const prev = mapMoney(row.prev, native, display, rates);
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

export default function MarketQuotes({ market = "stock" }: { market?: MarketKind }) {
  const { currency, rates, fxStatus } = useDisplayCurrency();
  const native = nativeCurrencyForMarket(market);
  const [groups, setGroups] = useState<QuoteGroup[]>(() => mockGroups(market));
  const [source, setSource] = useState<"mock" | "live" | "loading">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setSource("loading");
    setError(null);
    setGroups(mockGroups(market));
    fetchMarketQuotes({ market, exchange: "HOSE", limit: 80, signal: controller.signal })
      .then((data) => {
        if (!data.groups.length) {
          throw new Error("Empty quotes");
        }
        setGroups(data.groups);
        setSource("live");
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setGroups(mockGroups(market));
        setSource("mock");
        setError(err instanceof Error ? err.message : "Quotes unavailable");
      });
    return () => controller.abort();
  }, [market]);

  const displayGroups = useMemo(() => {
    return groups.map((group) => ({
      ...group,
      rows: group.rows.map((row) => mapRow(row, native, currency, rates.rates)),
    }));
  }, [currency, groups, native, rates.rates]);

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
        <div className="text-[11px] text-gray-500">
          {source === "loading" ? (market === "crypto" ? "Loading crypto quotes…" : "Loading VN quotes…") : null}
          {source === "live" ? (market === "crypto" ? "CoinGecko" : "HOSE · vnstock") : null}
          {source === "mock" ? `Demo data${error ? ` (${error})` : ""}` : null}
          {showNativeFallback ? ` · showing ${native} (rate unavailable)` : null}
        </div>
      </div>
      <div className="overflow-hidden rounded-lg border border-gray-600 bg-gray-800">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
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
                        <span className="flex items-center gap-2.5">
                          <CompanyLogo symbol={row.symbol} size={20} />
                          <span className="text-gray-200">{row.name}</span>
                        </span>
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
          </table>
        </div>
      </div>
    </div>
  );
}

function getAnyRowConverted(
  groups: Array<{ rows: Array<{ moneyConverted: boolean }> }>,
): boolean {
  return groups.some((g) => g.rows.some((r) => r.moneyConverted));
}
