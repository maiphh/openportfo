"use client";

import AssetLink from "@/components/AssetLink";
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

  if (slices.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center rounded-xl border border-gray-600 bg-gray-800/60 text-sm text-gray-500">
        No priced allocation yet
      </div>
    );
  }

  const cx = 80;
  const cy = 80;
  const outer = 70;
  const inner = 40;

  return (
    <div className="rounded-xl border border-gray-600 bg-gray-800/60 p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-200">Allocation</h3>
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        <svg viewBox="0 0 160 160" className="h-40 w-40 shrink-0" aria-label="Portfolio allocation pie">
          {slices.map((slice) => (
            <path
              key={slice.key}
              d={describeDonutSlice(cx, cy, outer, inner, slice.startAngle, slice.endAngle)}
              fill={slice.color}
            />
          ))}
          <circle cx={cx} cy={cy} r={inner - 2} style={{ fill: "var(--color-gray-800)" }} />
        </svg>
        <ul className="w-full space-y-2 text-sm">
          {colored
            .filter((i) => i.value > 0)
            .map((item) => {
              const pct = total > 0 ? (item.value / total) * 100 : 0;
              const linkId = item.assetId || item.label;
              return (
                <li key={item.key} className="flex items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="inline-block size-2.5 shrink-0 rounded-full" style={{ background: item.color }} />
                    {item.assetType ? (
                      <AssetLink assetType={item.assetType} id={linkId} className="truncate text-gray-300">
                        {item.label}
                      </AssetLink>
                    ) : (
                      <span className="truncate text-gray-300">{item.label}</span>
                    )}
                  </span>
                  <span className="shrink-0 tabular-nums text-gray-400">
                    {formatPct(pct)} · {formatPrice(item.value)} {currency}
                  </span>
                </li>
              );
            })}
        </ul>
      </div>
    </div>
  );
}
