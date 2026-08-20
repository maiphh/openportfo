"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { Button } from "@/components/ui/button";
import {
  DEFAULT_PERFORMANCE_RANGE,
  PERFORMANCE_RANGE_AXIS,
  PERFORMANCE_RANGES,
  SNAPSHOTS_EMPTY_COPY,
  fetchPortfolioPerformance,
  isAbortError,
  parsePerformanceRange,
  backendValuedPoints,
  type PerformanceRange,
  type PerformanceResponse,
} from "@/lib/portfolio-charts";
import { PortfolioApiError } from "@/lib/portfolio";
import { cn, formatPrice } from "@/lib/utils";

function ChartSkeleton() {
  return (
    <div
      className="h-[220px] animate-pulse rounded-lg border border-gray-700 bg-gray-900/40"
      data-testid="portfolio-value-skeleton"
    />
  );
}

function formatSignedMoney(value: number): string {
  if (value > 0) return `+${formatPrice(value)}`;
  if (value < 0) return `-${formatPrice(Math.abs(value))}`;
  return formatPrice(0);
}

export default function PortfolioValueChart({ token }: { token: string | null }) {
  const { currency } = useDisplayCurrency();
  const [range, setRange] = useState<PerformanceRange>(DEFAULT_PERFORMANCE_RANGE);
  const [data, setData] = useState<PerformanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    if (!token) {
      setLoading(false);
      setData(null);
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const next = await fetchPortfolioPerformance({ range, currency, token, signal: controller.signal });
      if (controller.signal.aborted) return;
      setData(next);
    } catch (err) {
      if (controller.signal.aborted || isAbortError(err)) return;
      setData(null);
      setError(err instanceof PortfolioApiError || err instanceof Error ? err.message : "Failed to load chart");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [currency, range, token]);

  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
  }, [load, reloadKey]);

  const valued = useMemo(
    () => backendValuedPoints(data?.points ?? [], currency),
    [currency, data?.points],
  );

  const series = valued.map((point) => point.marketValue);
  const last = series.length ? series[series.length - 1] : null;
  const first = series.length ? series[0] : null;
  const change = last != null && first != null ? last - first : null;
  const axis = PERFORMANCE_RANGE_AXIS[range];

  return (
    <section className="rounded-xl border border-gray-600 bg-gray-800/60 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-medium text-gray-200">Portfolio value</h2>
          {last != null && !loading && !error && series.length >= 2 && (
            <p className="mt-0.5 text-sm tabular-nums text-gray-300">
              {formatPrice(last)} {currency}
              {change != null && (
                <span className={cn("ml-2", change > 0 && "text-teal-400", change < 0 && "text-red-400")}>
                  {formatSignedMoney(change)}
                </span>
              )}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Chart range">
          {PERFORMANCE_RANGES.map((item) => (
            <Button
              key={item}
              type="button"
              size="sm"
              role="tab"
              aria-selected={range === item}
              variant={range === item ? "default" : "outline"}
              disabled={loading}
              onClick={() => setRange(parsePerformanceRange(item))}
            >
              {item}
            </Button>
          ))}
        </div>
      </div>

      {loading ? (
        <ChartSkeleton />
      ) : error ? (
        <div className="flex h-[220px] flex-col items-center justify-center gap-3 rounded-lg border border-red-500/30 bg-red-500/5 px-4 text-center">
          <p className="text-sm text-red-400">{error}</p>
          <Button type="button" size="sm" variant="outline" onClick={() => setReloadKey((n) => n + 1)}>
            Retry
          </Button>
        </div>
      ) : series.length < 2 ? (
        <div className="flex h-[220px] items-center justify-center rounded-lg border border-dashed border-gray-600 bg-gray-900/40 px-4 text-center text-sm text-gray-500">
          {SNAPSHOTS_EMPTY_COPY}
        </div>
      ) : (
        <ValueSvg data={series} labels={axis} currency={currency} last={last} range={range} />
      )}
    </section>
  );
}

function ValueSvg({
  data,
  labels,
  currency,
  last,
  range,
  height = 200,
}: {
  data: number[];
  labels: [string, string];
  currency: string;
  last: number | null;
  range: PerformanceRange;
  height?: number;
}) {
  const width = 640;
  const padX = 8;
  const padY = 12;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = Math.max(max - min, 0.0001);

  const points = data.map((value, i) => {
    const x = padX + (i / Math.max(data.length - 1, 1)) * (width - padX * 2);
    const y = padY + (1 - (value - min) / span) * (height - padY * 2);
    return { x, y };
  });

  const line = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" ");
  const area = `${line} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z`;
  const lastLabel = last == null ? "" : `, last ${formatPrice(last)} ${currency}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height + 22}`}
      className="h-auto w-full"
      role="img"
      aria-label={`Portfolio value, ${range}${lastLabel}`}
    >
      <defs>
        <linearGradient id="portfolio-value-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0FEDBE" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#0FEDBE" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#portfolio-value-fill)" />
      <path d={line} fill="none" stroke="#0FEDBE" strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
      {labels.map((label, i) => {
        const x = padX + (i / Math.max(labels.length - 1, 1)) * (width - padX * 2);
        return (
          <text key={label} x={x} y={height + 16} textAnchor="middle" fill="#9095A1" fontSize="11">
            {label}
          </text>
        );
      })}
    </svg>
  );
}
