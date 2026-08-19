"use client";

import { Fragment, useEffect, useState } from "react";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { Button } from "@/components/ui/button";
import { fetchMarketQuotes, type MarketKind } from "@/lib/api";
import type { QuoteGroup } from "@/types/markets";
import { cn, formatPct, formatPrice, formatSigned } from "@/lib/utils";

const COLUMNS = ["Name", "Value", "Change", "Chg%", "Open", "High", "Low", "Prev"] as const;

type LoadState = "loading" | "live" | "error";

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

export default function MarketQuotes({ market = "stock" }: { market?: MarketKind }) {
  const [groups, setGroups] = useState<QuoteGroup[]>([]);
  const [source, setSource] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setSource("loading");
    setError(null);
    setGroups([]);
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
        setGroups([]);
        setSource("error");
        setError(err instanceof Error ? err.message : "Quotes unavailable");
      });
    return () => controller.abort();
  }, [market, reloadKey]);

  return (
    <div className="w-full">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-2">
        <h3 className="text-2xl font-semibold text-gray-100">Market Quotes</h3>
        <div className="text-[11px] text-gray-500">
          {source === "loading" ? (market === "crypto" ? "Loading crypto quotes…" : "Loading VN quotes…") : null}
          {source === "live" ? (market === "crypto" ? "CoinGecko" : "HOSE · vnstock") : null}
        </div>
      </div>
      <div className="overflow-hidden rounded-lg border border-gray-600 bg-gray-800">
        {source === "error" ? (
          <div className="flex flex-col items-center justify-center gap-3 px-4 py-16 text-center" data-testid="quotes-error">
            <p className="text-sm text-gray-400">{error ?? "Quotes unavailable"}</p>
            <Button type="button" variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          </div>
        ) : (
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
              {source === "loading" ? <QuotesSkeleton /> : null}
              {source === "live" ? (
                <tbody>
                  {groups.map((group) => (
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
              ) : null}
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
