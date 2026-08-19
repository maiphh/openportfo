"use client";

import type { ReactNode } from "react";
import type { PortfolioLine } from "@/lib/portfolio";
import { parseMoney } from "@/lib/portfolio";
import { cn, formatPct, formatPrice, formatSigned } from "@/lib/utils";
import { Button } from "@/components/ui/button";

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

export default function HoldingsTable({
  lines,
  displayCurrency,
  onEdit,
  onDelete,
  busyKey,
}: {
  lines: PortfolioLine[];
  displayCurrency: string;
  onEdit: (line: PortfolioLine) => void;
  onDelete: (line: PortfolioLine) => void;
  busyKey?: string | null;
}) {
  if (lines.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-600 bg-gray-800/40 px-4 py-10 text-center text-sm text-gray-500">
        No holdings match this filter.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-600">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-gray-800 text-xs uppercase tracking-wide text-gray-500">
          <tr>
            <th className="px-3 py-3 font-medium">Asset</th>
            <th className="px-3 py-3 font-medium">Qty</th>
            <th className="px-3 py-3 font-medium">Avg cost</th>
            <th className="px-3 py-3 font-medium">Price</th>
            <th className="px-3 py-3 font-medium">Market value</th>
            <th className="px-3 py-3 font-medium">PnL</th>
            <th className="px-3 py-3 font-medium">Alloc</th>
            <th className="px-3 py-3 font-medium">Status</th>
            <th className="px-3 py-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => {
            const key = `${line.assetType}:${line.symbol}`;
            const mv = parseMoney(line.marketValueDisplay) ?? parseMoney(line.marketValue);
            const pnl = parseMoney(line.pnlDisplay) ?? parseMoney(line.pnl);
            const pnlPct = parseMoney(line.pnlPercent);
            const alloc = parseMoney(line.allocation);
            const price = parseMoney(line.price);
            const avg = parseMoney(line.avgCost);
            const showDisplay = line.marketValueDisplay != null;
            const moneyCur = showDisplay ? displayCurrency : line.currency;

            return (
              <tr key={key} className="border-t border-gray-700/80 hover:bg-gray-800/50">
                <td className="px-3 py-3">
                  <div className="font-semibold text-gray-100">{line.symbol}</div>
                  <div className="text-xs capitalize text-gray-500">{line.assetType}</div>
                </td>
                <td className="px-3 py-3 tabular-nums text-gray-300">{line.qty}</td>
                <td className="px-3 py-3 tabular-nums text-gray-300">
                  {avg == null ? "—" : `${formatPrice(avg)} ${line.currency}`}
                </td>
                <td className="px-3 py-3 tabular-nums text-gray-300">
                  {price == null ? "—" : `${formatPrice(price)} ${line.currency}`}
                </td>
                <td className="px-3 py-3 tabular-nums text-gray-200">
                  {mv == null ? "—" : `${formatPrice(mv)} ${moneyCur}`}
                </td>
                <td
                  className={cn(
                    "px-3 py-3 tabular-nums",
                    pnl == null && "text-gray-500",
                    pnl != null && pnl > 0 && "text-teal-400",
                    pnl != null && pnl < 0 && "text-red-500",
                    pnl === 0 && "text-gray-300",
                  )}
                >
                  {pnl == null ? "—" : `${formatSigned(pnl)} ${moneyCur}`}
                  {pnlPct != null && (
                    <div className="text-xs opacity-80">{formatPct(pnlPct * 100)}</div>
                  )}
                </td>
                <td className="px-3 py-3 tabular-nums text-gray-400">
                  {alloc == null ? "—" : formatPct(alloc * 100)}
                </td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-1">
                    {line.missingPrice && <Badge tone="warn">Missing price</Badge>}
                    {line.stale && <Badge tone="muted">Stale</Badge>}
                    {!line.missingPrice && !line.stale && <Badge tone="muted">OK</Badge>}
                  </div>
                </td>
                <td className="px-3 py-3">
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={busyKey === key}
                      onClick={() => onEdit(line)}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-red-400 hover:text-red-300"
                      disabled={busyKey === key}
                      onClick={() => onDelete(line)}
                    >
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
