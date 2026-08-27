"use client";

import type { ReactNode } from "react";
import AssetLink from "@/components/AssetLink";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { Button } from "@/components/ui/button";
import type { ConvertToDisplay } from "@/lib/portfolio";
import { cn, formatPrice } from "@/lib/utils";
import {
  watchlistItemKey,
  watchlistPriceInDisplay,
  type WatchlistItem,
} from "@/lib/watchlist";

function Badge({ children, tone }: { children: ReactNode; tone: "warn" | "muted" }) {
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
        tone === "warn" && "bg-amber-500/15 text-amber-400",
        tone === "muted" && "bg-gray-600/40 text-gray-400",
      )}
    >
      {children}
    </span>
  );
}

export default function WatchlistTable({
  items,
  displayCurrency,
  convertToDisplay,
  onRemove,
  busyKey,
}: {
  items: WatchlistItem[];
  displayCurrency: string;
  convertToDisplay?: ConvertToDisplay;
  onRemove: (item: WatchlistItem) => void;
  busyKey?: string | null;
}) {
  return (
    <div className="table-scroll min-w-0 rounded-xl border border-gray-600" role="region" aria-label="Scrollable watchlist" tabIndex={0}>
      <table className="w-max min-w-full text-left text-sm">
        <thead className="bg-gray-800 text-xs uppercase tracking-wide text-gray-500">
          <tr>
            <th className="px-3 py-3 font-medium">Asset</th>
            <th className="px-3 py-3 font-medium">Price</th>
            <th className="px-3 py-3 font-medium">Status</th>
            <th className="px-3 py-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const key = watchlistItemKey(item);
            const shown = watchlistPriceInDisplay(
              item.price,
              item.currency,
              displayCurrency,
              convertToDisplay,
            );
            return (
              <tr key={key} className="border-t border-gray-700/80 hover:bg-gray-800/50">
                <td className="px-3 py-3">
                  <AssetLink
                    assetType={item.assetType}
                    id={item.assetId || item.symbol}
                    className="flex items-center gap-2.5 font-semibold text-gray-100"
                  >
                    <CompanyLogo symbol={item.symbol} size={20} assetType={item.assetType} />
                    {item.symbol}
                  </AssetLink>
                  <div className="pl-8 text-xs capitalize text-gray-500">{item.assetType}</div>
                </td>
                <td className="px-3 py-3 tabular-nums text-gray-300">
                  {shown.missing || shown.amount == null
                    ? "—"
                    : `${formatPrice(shown.amount)} ${shown.currency}`}
                </td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-1">
                    {shown.missing && <Badge tone="warn">Missing</Badge>}
                    {item.stale && <Badge tone="muted">Stale</Badge>}
                    {!shown.missing && !item.stale && <Badge tone="muted">OK</Badge>}
                  </div>
                </td>
                <td className="px-3 py-3">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-red-400 hover:text-red-300"
                    disabled={busyKey === key}
                    onClick={() => onRemove(item)}
                  >
                    {busyKey === key ? "Removing…" : "Remove"}
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
