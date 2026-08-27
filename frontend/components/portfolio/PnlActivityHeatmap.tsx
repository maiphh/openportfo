"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { Button } from "@/components/ui/button";
import {
  HEATMAP_WEEKS,
  PNL_LEGEND_STEPS,
  SNAPSHOTS_EMPTY_COPY,
  buildPnlHeatmapGrid,
  fetchSnapshots,
  heatmapDateWindow,
  isAbortError,
  backendSnapshotsToDailyPnl,
  pnlBucketFill,
  type HeatmapCell,
  type PnlHeatmapFilter,
  type SnapshotDto,
} from "@/lib/portfolio-charts";
import { PortfolioApiError } from "@/lib/portfolio";
import { cn, formatPct, formatPrice } from "@/lib/utils";

/** Cursor-style: label Mon / Wed / Fri only, single letters. */
const WEEKDAY_LABELS = ["", "M", "", "W", "", "F", ""] as const;
const LABEL_GUTTER = 14;
const MONTH_ROW = 14;
/** Cursor contribution cells sit ~2px apart and stretch to the card width. */
const GAP = 2;
const LEGEND_CELL = 10;

const FILTERS: { id: PnlHeatmapFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "gains", label: "Gains" },
  { id: "losses", label: "Losses" },
];

function formatSignedMoney(value: number): string {
  if (value > 0) return `+${formatPrice(value)}`;
  if (value < 0) return `-${formatPrice(Math.abs(value))}`;
  return formatPrice(0);
}

function cellLabel(cell: HeatmapCell, currency: string): string {
  if (!cell.inRange) return cell.date;
  if (cell.dailyPnl == null) return `${cell.date} · no daily PnL`;
  const pct = cell.dailyPnlPct == null ? "" : ` · ${formatPct(cell.dailyPnlPct * 100)}`;
  return `${cell.date} · ${formatSignedMoney(cell.dailyPnl)} ${currency}${pct}`;
}

function HeatmapSkeleton() {
  return (
    <div className="animate-pulse" data-testid="pnl-heatmap-skeleton">
      <div className="mb-3.5 h-3 w-1/2 rounded bg-gray-700/40" style={{ marginLeft: LABEL_GUTTER }} />
      <div className="flex" style={{ paddingLeft: LABEL_GUTTER, gap: GAP }}>
        {Array.from({ length: HEATMAP_WEEKS }).map((_, week) => (
          <div key={week} className="flex min-w-0 flex-1 flex-col" style={{ gap: GAP }}>
            {Array.from({ length: 7 }).map((__, day) => (
              <div key={day} className="aspect-square w-full rounded-[2px] bg-gray-700/50" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PnlActivityHeatmap({ token }: { token: string | null }) {
  const { currency } = useDisplayCurrency();
  const [snapshots, setSnapshots] = useState<SnapshotDto[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [filter, setFilter] = useState<PnlHeatmapFilter>("all");
  const [tip, setTip] = useState<{ text: string; x: number; y: number } | null>(null);
  const [rowHeight, setRowHeight] = useState(11);
  const hostRef = useRef<HTMLDivElement>(null);
  const gridRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const windowDates = useMemo(() => heatmapDateWindow(), []);

  useEffect(() => {
    const el = gridRef.current;
    if (!el) return;
    const measure = () => {
      const first = el.firstElementChild as HTMLElement | null;
      if (!first) return;
      const width = first.getBoundingClientRect().width;
      if (width > 0) setRowHeight(width);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [loading]);

  const load = useCallback(async () => {
    if (!token) {
      setLoading(false);
      setSnapshots(null);
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const next = await fetchSnapshots({
        from: windowDates.from,
        to: windowDates.to,
        currency,
        token,
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setSnapshots(next);
    } catch (err) {
      if (controller.signal.aborted || isAbortError(err)) return;
      setSnapshots(null);
      setError(err instanceof PortfolioApiError || err instanceof Error ? err.message : "Failed to load heatmap");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [currency, token, windowDates.from, windowDates.to]);

  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
  }, [load, reloadKey]);

  const series = useMemo(
    () => backendSnapshotsToDailyPnl(snapshots ?? [], currency),
    [currency, snapshots],
  );

  const grid = useMemo(() => buildPnlHeatmapGrid({ series }), [series]);
  const hasSnapshots = (snapshots?.length ?? 0) > 0;
  const activeDays = useMemo(() => {
    return series.filter((point) => {
      if (point.dailyPnl == null) return false;
      if (filter === "gains") return point.dailyPnl > 0;
      if (filter === "losses") return point.dailyPnl < 0;
      return point.dailyPnl !== 0;
    }).length;
  }, [filter, series]);
  const summary = hasSnapshots
    ? `Daily PnL for the last ${HEATMAP_WEEKS} weeks. ${activeDays} active days (${filter}).`
    : SNAPSHOTS_EMPTY_COPY;

  const showTip = (cellData: HeatmapCell, el: HTMLElement) => {
    const host = hostRef.current?.getBoundingClientRect();
    const rect = el.getBoundingClientRect();
    if (!host) return;
    setTip({
      text: cellLabel(cellData, currency),
      x: rect.left - host.left + rect.width / 2,
      y: rect.top - host.top,
    });
  };

  return (
    <section className="surface-card overflow-hidden p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-[13px] font-medium text-gray-400">Daily PnL</h2>
          <p className="mt-0.5 text-[28px] font-semibold leading-none tracking-tight tabular-nums text-gray-100">
            {loading ? "—" : activeDays}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-0.5" role="tablist" aria-label="PnL filter">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={filter === item.id}
              data-active={filter === item.id ? "true" : "false"}
              className={cn(
                "rounded-md px-2 py-0.5 text-[13px] font-medium transition-colors duration-150",
                filter === item.id
                  ? "bg-gray-700/80 text-gray-100"
                  : "text-gray-500 hover:bg-gray-700/40 hover:text-gray-200",
              )}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <HeatmapSkeleton />
      ) : error ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-8 text-center">
          <p className="text-sm text-red-400">{error}</p>
          <Button type="button" size="sm" variant="outline" onClick={() => setReloadKey((n) => n + 1)}>
            Retry
          </Button>
        </div>
      ) : (
        <div ref={hostRef} className="relative w-full">
          <div className="w-full" role="img" aria-label={summary}>
            <div className="flex w-full">
              <div className="flex shrink-0 flex-col" style={{ width: LABEL_GUTTER }}>
                <div style={{ height: MONTH_ROW }} />
                {WEEKDAY_LABELS.map((label, i) => (
                  <div
                    key={i}
                    className="flex items-center text-[10px] leading-none text-gray-500"
                    style={{ height: rowHeight, marginBottom: i === 6 ? 0 : GAP }}
                  >
                    {label}
                  </div>
                ))}
              </div>

              <div className="min-w-0 flex-1">
                <div className="relative text-[10px] text-gray-500" style={{ height: MONTH_ROW }}>
                  {grid.monthLabels.map((month) => (
                    <span
                      key={`${month.weekIndex}-${month.label}`}
                      className="absolute top-0 leading-none"
                      style={{ left: `${(month.weekIndex / HEATMAP_WEEKS) * 100}%` }}
                    >
                      {month.label}
                    </span>
                  ))}
                </div>
                <div
                  ref={gridRef}
                  className="grid w-full"
                  style={{
                    gridTemplateColumns: `repeat(${HEATMAP_WEEKS}, minmax(0, 1fr))`,
                    gap: GAP,
                  }}
                >
                  {grid.weeks.map((week, weekIndex) => (
                    <div key={weekIndex} className="flex min-w-0 flex-col" style={{ gap: GAP }}>
                      {week.map((day) => {
                        const interactive = day.inRange;
                        return (
                          <button
                            key={day.date}
                            type="button"
                            disabled={!interactive}
                            tabIndex={interactive ? 0 : -1}
                            title={interactive ? cellLabel(day, currency) : undefined}
                            aria-label={interactive ? cellLabel(day, currency) : undefined}
                            data-date={day.date}
                            data-bucket={day.bucket}
                            className="aspect-square w-full rounded-[2px] transition-[filter] duration-150 hover:brightness-125 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal-400 disabled:cursor-default"
                            style={{ background: pnlBucketFill(day.bucket, filter) }}
                            onMouseEnter={(e) => interactive && showTip(day, e.currentTarget)}
                            onMouseLeave={() => setTip(null)}
                            onFocus={(e) => interactive && showTip(day, e.currentTarget)}
                            onBlur={() => setTip(null)}
                          />
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div
            className="mt-3 flex items-center gap-1.5 text-[11px] text-gray-500"
            style={{ paddingLeft: LABEL_GUTTER }}
            aria-hidden
          >
            <span>Fewer</span>
            {PNL_LEGEND_STEPS.map((color) => (
              <span
                key={color}
                className="rounded-[2px]"
                style={{ width: LEGEND_CELL, height: LEGEND_CELL, background: color }}
              />
            ))}
            <span>More</span>
          </div>

          {tip && (
            <div
              role="tooltip"
              className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-md border border-gray-600 bg-gray-900 px-2 py-1 text-[11px] tabular-nums text-gray-100 shadow-lg"
              style={{ left: tip.x, top: tip.y - 6 }}
            >
              {tip.text}
            </div>
          )}
          {!hasSnapshots && (
            <p className="mt-3 text-sm text-gray-500" style={{ paddingLeft: LABEL_GUTTER }}>
              {SNAPSHOTS_EMPTY_COPY}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
