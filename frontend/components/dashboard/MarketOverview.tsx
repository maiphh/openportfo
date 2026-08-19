"use client";

import { useMemo, useState } from "react";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import Sparkline from "@/components/dashboard/Sparkline";
import {
  OVERVIEW_TABS,
  RANGES,
  sparklineFor,
  type OverviewTab,
  type RangeKey,
} from "@/lib/mock-data";
import { cn, formatPct, formatPrice, formatSigned } from "@/lib/utils";

const TABS: OverviewTab[] = ["Financial", "Technology", "Services"];

function toneClass(value: number) {
  if (value > 0) return "text-teal-400";
  if (value < 0) return "text-red-500";
  return "text-gray-500";
}

export default function MarketOverview() {
  const [tab, setTab] = useState<OverviewTab>("Financial");
  const [range, setRange] = useState<RangeKey>("1Y");
  const rows = OVERVIEW_TABS[tab];
  const [selected, setSelected] = useState(rows[0].symbol);
  const active = rows.find((row) => row.symbol === selected) ?? rows[0];
  const spark = useMemo(() => sparklineFor(active.symbol, range), [active.symbol, range]);

  return (
    <div className="w-full">
      <h3 className="mb-5 text-2xl font-semibold text-gray-100">Market Overview</h3>
      <div className="overflow-hidden rounded-lg border border-gray-600 bg-gray-800">
        <div className="flex gap-5 border-b border-gray-600 px-4 pt-3 text-sm">
          {TABS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setTab(item);
                setSelected(OVERVIEW_TABS[item][0].symbol);
              }}
              className={cn(
                "pb-2.5 font-medium transition-colors",
                tab === item ? "border-b-2 border-teal-400 text-gray-100" : "text-gray-500 hover:text-gray-300",
              )}
            >
              {item}
            </button>
          ))}
        </div>

        <div className="px-3 pt-3">
          <Sparkline data={spark} range={range} />
        </div>

        <div className="flex items-center gap-2 px-4 py-2 text-xs text-gray-500">
          {RANGES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setRange(item)}
              className={cn(
                "rounded px-2 py-1 font-medium",
                range === item ? "bg-gray-600 text-gray-100" : "hover:text-gray-300",
              )}
            >
              {item}
            </button>
          ))}
        </div>

        <ul>
          {rows.map((row) => {
            const isActive = row.symbol === active.symbol;
            return (
              <li key={row.symbol}>
                <button
                  type="button"
                  onClick={() => setSelected(row.symbol)}
                  className={cn(
                    "flex w-full items-center gap-3 border-t border-gray-700 px-4 py-2.5 text-left transition-colors",
                    isActive ? "bg-teal-400/5" : "hover:bg-gray-700/40",
                  )}
                >
                  <CompanyLogo symbol={row.symbol} size={22} />
                  <span className="w-14 shrink-0 text-sm font-semibold text-gray-200">{row.symbol}</span>
                  <span className="min-w-0 flex-1 truncate text-sm text-gray-500">{row.name}</span>
                  <span className="w-[4.5rem] text-right text-sm tabular-nums text-gray-200">
                    {formatPrice(row.value)}
                  </span>
                  <span className={cn("w-12 text-right text-sm tabular-nums", toneClass(row.change))}>
                    {formatSigned(row.change)}
                  </span>
                  <span className={cn("w-14 text-right text-sm tabular-nums", toneClass(row.changePct))}>
                    {formatPct(row.changePct)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
