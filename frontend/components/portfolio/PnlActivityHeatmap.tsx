"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { Button } from "@/components/ui/button";
import {
  HEATMAP_WEEKS,
  PNL_BUCKET_COLORS,
  SNAPSHOTS_EMPTY_COPY,
  buildPnlHeatmapGrid,
  fetchSnapshots,
  heatmapDateWindow,
  isAbortError,
  backendSnapshotsToDailyPnl,
  type HeatmapCell,
  type SnapshotDto,
} from "@/lib/portfolio-charts";
import { PortfolioApiError } from "@/lib/portfolio";
import { formatPct, formatPrice } from "@/lib/utils";

const WEEKDAY_LABELS = ["", "Mon", "", "Wed", "", "Fri", ""] as const;
const CELL = 11;
const GAP = 3;
const COL = CELL + GAP;

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
    <div className="animate-pulse overflow-x-auto" data-testid="pnl-heatmap-skeleton">
      <div className="flex gap-[3px]">
        {Array.from({ length: 20 }).map((_, week) => (
          <div key={week} className="flex flex-col gap-[3px]">
            {Array.from({ length: 7 }).map((__, day) => (
              <div key={day} className="size-[11px] rounded-[2px] bg-gray-700/60" />
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
  const [tip, setTip] = useState<{ text: string; x: number; y: number } | null>(null);
  const hostRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const windowDates = useMemo(() => heatmapDateWindow(), []);

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
  const upDays = series.filter((p) => (p.dailyPnl ?? 0) > 0).length;
  const downDays = series.filter((p) => (p.dailyPnl ?? 0) < 0).length;
  const summary = hasSnapshots
    ? `Daily PnL for the last ${HEATMAP_WEEKS} weeks. ${upDays} up days, ${downDays} down days.`
    : SNAPSHOTS_EMPTY_COPY;

  const showTip = (cell: HeatmapCell, el: HTMLElement) => {
    const host = hostRef.current?.getBoundingClientRect();
    const rect = el.getBoundingClientRect();
    if (!host) return;
    setTip({
      text: cellLabel(cell, currency),
      x: rect.left - host.left + rect.width / 2,
      y: rect.top - host.top,
    });
  };

  return (
    <section className="rounded-xl border border-gray-600 bg-gray-800/60 p-4">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-sm font-medium text-gray-200">Daily PnL</h2>
          <p className="mt-0.5 text-xs text-gray-500">Last {HEATMAP_WEEKS} weeks · day-over-day market value</p>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-gray-500" aria-hidden>
          <span>Loss</span>
          {(["down-4", "down-3", "down-2", "down-1", "empty", "up-1", "up-2", "up-3", "up-4"] as const).map((bucket) => (
            <span
              key={bucket}
              className="size-[11px] rounded-[2px]"
              style={{ background: PNL_BUCKET_COLORS[bucket] }}
            />
          ))}
          <span>Gain</span>
        </div>
      </div>

      {loading ? (
        <HeatmapSkeleton />
      ) : error ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-10 text-center">
          <p className="text-sm text-red-400">{error}</p>
          <Button type="button" size="sm" variant="outline" onClick={() => setReloadKey((n) => n + 1)}>
            Retry
          </Button>
        </div>
      ) : (
        <div ref={hostRef} className="relative">
          <div className="overflow-x-auto pb-1">
            <div
              className="inline-flex"
              role="img"
              aria-label={summary}
            >
              <div className="mr-1 flex w-7 shrink-0 flex-col">
                <div className="h-4" />
                {WEEKDAY_LABELS.map((label, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-end pr-1 text-[10px] leading-none text-gray-500"
                    style={{ height: CELL, marginBottom: i === 6 ? 0 : GAP }}
                  >
                    {label}
                  </div>
                ))}
              </div>
              <div>
                <div className="relative h-4 text-[10px] text-gray-500">
                  {grid.monthLabels.map((month) => (
                    <span
                      key={`${month.weekIndex}-${month.label}`}
                      className="absolute top-0"
                      style={{ left: month.weekIndex * COL }}
                    >
                      {month.label}
                    </span>
                  ))}
                </div>
                <div className="flex" style={{ gap: GAP }}>
                  {grid.weeks.map((week, weekIndex) => (
                    <div key={weekIndex} className="flex flex-col" style={{ gap: GAP }}>
                      {week.map((cell) => {
                        const interactive = cell.inRange;
                        return (
                          <button
                            key={cell.date}
                            type="button"
                            disabled={!interactive}
                            tabIndex={interactive ? 0 : -1}
                            title={interactive ? cellLabel(cell, currency) : undefined}
                            aria-label={interactive ? cellLabel(cell, currency) : undefined}
                            data-date={cell.date}
                            data-bucket={cell.bucket}
                            className="rounded-[2px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal-400 disabled:cursor-default"
                            style={{
                              width: CELL,
                              height: CELL,
                              background: PNL_BUCKET_COLORS[cell.bucket],
                            }}
                            onMouseEnter={(e) => interactive && showTip(cell, e.currentTarget)}
                            onMouseLeave={() => setTip(null)}
                            onFocus={(e) => interactive && showTip(cell, e.currentTarget)}
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
            <p className="mt-3 text-sm text-gray-500">{SNAPSHOTS_EMPTY_COPY}</p>
          )}
        </div>
      )}
    </section>
  );
}
