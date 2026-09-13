"use client";

import AssetLink from "@/components/AssetLink";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import type { AssetKind } from "@/lib/asset";
import { describeDonutSlice, pieSlices } from "@/lib/portfolio";
import { formatPct, formatPrice } from "@/lib/utils";

const COLORS = ["#0fedbe", "#3b82f6", "#f59e0b", "#a855f7", "#ef4444", "#22d3ee", "#84cc16"];

export type PieItem = {
  key: string;
  label: string;
  value: number;
  assetType?: AssetKind;
  assetId?: string | null;
};

export default function AllocationPie({
  items,
  currency,
}: {
  items: PieItem[];
  currency: string;
}) {
  const colored = items.map((item, idx) => ({
    ...item,
    color: COLORS[idx % COLORS.length],
  }));
  const slices = pieSlices(colored);
  const total = colored.reduce((sum, i) => sum + Math.max(0, i.value), 0);
  const rows = colored.filter((i) => i.value > 0);

  if (slices.length === 0) {
    return (
      <div className="surface-card flex h-40 items-center justify-center text-sm text-gray-500">
        No priced allocation yet
      </div>
    );
  }

  const cx = 80;
  const cy = 80;
  const outer = 72;
  const inner = 46;

  return (
    <section className="surface-card p-4">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-medium text-gray-200">Allocation</h3>
        <p className="text-xs tabular-nums text-gray-500">
          {rows.length} position{rows.length === 1 ? "" : "s"} · {formatPrice(total)} {currency}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-[9.5rem_minmax(0,1fr)] sm:items-center sm:gap-5">
        <div className="relative mx-auto size-36 shrink-0 sm:mx-0 sm:size-[9.5rem]">
          <svg viewBox="0 0 160 160" className="size-full" aria-label="Portfolio allocation pie">
            {slices.map((slice) => (
              <path
                key={slice.key}
                d={describeDonutSlice(cx, cy, outer, inner, slice.startAngle, slice.endAngle)}
                fill={slice.color}
              />
            ))}
            <circle cx={cx} cy={cy} r={inner - 1} style={{ fill: "var(--color-gray-800)" }} />
          </svg>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-3 text-center">
            <span className="text-[10px] uppercase tracking-wide text-gray-500">Total</span>
            <span className="mt-0.5 max-w-full truncate text-sm font-semibold tabular-nums text-gray-100">
              {formatPrice(total)}
            </span>
            <span className="text-[10px] text-gray-500">{currency}</span>
          </div>
        </div>

        <ul className="min-w-0 space-y-1">
          {rows.map((item) => {
            const pct = total > 0 ? (item.value / total) * 100 : 0;
            const linkId = item.assetId || item.label;
            return (
              <li
                key={item.key}
                className="rounded-lg px-2 py-1.5 transition-colors hover:bg-gray-700/40"
              >
                <div className="flex items-center gap-3">
                  <span className="flex min-w-0 flex-1 items-center gap-2">
                    <span
                      className="inline-block size-2.5 shrink-0 rounded-full"
                      style={{ background: item.color }}
                    />
                    {item.assetType ? (
                      <AssetLink
                        assetType={item.assetType}
                        id={linkId}
                        className="inline-flex min-w-0 items-center gap-2 truncate text-sm text-gray-200"
                      >
                        <CompanyLogo symbol={item.label} size={18} assetType={item.assetType} />
                        <span className="truncate font-medium">{item.label}</span>
                      </AssetLink>
                    ) : (
                      <span className="truncate text-sm font-medium text-gray-200">{item.label}</span>
                    )}
                  </span>
                  <span className="shrink-0 text-right tabular-nums">
                    <span className="block text-sm font-medium text-gray-100">{formatPct(pct)}</span>
                    <span className="block text-[11px] text-gray-500">
                      {formatPrice(item.value)} {currency}
                    </span>
                  </span>
                </div>
                <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-gray-700/80">
                  <div
                    className="h-full rounded-full transition-[width] duration-300"
                    style={{ width: `${Math.max(pct, pct > 0 ? 1.5 : 0)}%`, background: item.color }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
