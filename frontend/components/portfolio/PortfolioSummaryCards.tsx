"use client";

import { parseMoney, type PortfolioResponse } from "@/lib/portfolio";
import { cn, formatMoney, formatPct } from "@/lib/utils";

function moneyLabel(value: number | null, currency: string): string {
  if (value == null) return "—";
  return `${formatMoney(value, currency)} ${currency}`;
}

function formatNative(value: string | null | undefined, currency: string): string {
  const n = parseMoney(value);
  return n == null ? "—" : formatMoney(n, currency);
}

function formatNativeSigned(value: string | null | undefined, currency: string): string {
  const n = parseMoney(value);
  return n == null
    ? "—"
    : `${n > 0 ? "+" : n < 0 ? "-" : ""}${formatMoney(Math.abs(n), currency)}`;
}

export default function PortfolioSummaryCards({
  data,
  fallbackCurrency,
}: {
  data: PortfolioResponse;
  fallbackCurrency: string;
}) {
  const display = data.totalsDisplay;
  const currency = display?.currency || data.displayCurrency || fallbackCurrency;
  const mv = parseMoney(display?.marketValue);
  const cost = parseMoney(display?.costBasis);
  const pnl = parseMoney(display?.pnl);
  const pnlPct = parseMoney(display?.pnlPercent);
  const fxOk = Boolean(display) && data.fx?.status !== "missing";

  const cards = [
    { label: "Market value", value: moneyLabel(mv, currency) },
    { label: "Cost basis", value: moneyLabel(cost, currency) },
    {
      label: "PnL",
      value: pnl == null ? "—" : `${pnl > 0 ? "+" : pnl < 0 ? "-" : ""}${formatMoney(Math.abs(pnl), currency)} ${currency}`,
      tone: pnl == null ? "flat" : pnl > 0 ? "up" : pnl < 0 ? "down" : "flat",
    },
    {
      label: "PnL %",
      // API stores fraction (pnl/cost); show as percent points.
      value: pnlPct == null ? "—" : formatPct(pnlPct * 100),
      tone: pnlPct == null ? "flat" : pnlPct > 0 ? "up" : pnlPct < 0 ? "down" : "flat",
    },
  ] as const;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-xl border border-gray-600 bg-gray-800/60 p-4">
            <div className="text-xs uppercase tracking-wide text-gray-500">{card.label}</div>
            <div
              className={cn(
                "mt-2 text-lg font-semibold tabular-nums text-gray-100",
                "tone" in card && card.tone === "up" && "text-teal-400",
                "tone" in card && card.tone === "down" && "text-red-500",
              )}
            >
              {card.value}
            </div>
          </div>
        ))}
      </div>
      {!fxOk && (
        <p className="text-xs text-amber-400/90">
          Unified totals unavailable (FX {data.fx?.status || "missing"}). Native totals still shown per currency below
          when present.
        </p>
      )}
      {Object.keys(data.totalsByCurrency || {}).length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs text-gray-500">
          {Object.entries(data.totalsByCurrency).map(([cur, tot]) => (
            <span key={cur} className="rounded-md border border-gray-600 px-2 py-1">
              {cur}: MV {formatNative(tot.marketValue, cur)} · PnL {formatNativeSigned(tot.pnl, cur)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
