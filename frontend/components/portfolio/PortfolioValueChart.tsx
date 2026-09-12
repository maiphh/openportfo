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
    <section className="surface-card min-w-0 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-sm font-medium text-gray-200">Portfolio value</h2>
          {last != null && !loading && !error && series.length >= 2 ? (
            <p className="mt-1 flex min-w-0 flex-wrap items-baseline gap-x-2 break-words text-2xl font-semibold tracking-tight tabular-nums text-gray-100">
              <span className="break-all">
                {formatPrice(last)}{" "}
                <span className="text-sm font-medium text-gray-500">{currency}</span>
              </span>
              {change != null && (
                <span className={cn("text-sm font-medium break-words", change > 0 && "text-teal-400", change < 0 && "text-red-400")}>
                  {formatSignedMoney(change)}
                </span>
              )}
            </p>
          ) : (
            <p className="mt-0.5 text-xs text-gray-500">Value over the selected range</p>
          )}
        </div>
        <div className="segment-group" role="tablist" aria-label="Chart range">
          {PERFORMANCE_RANGES.map((item) => (
            <button
              key={item}
              type="button"
              role="tab"
              aria-selected={range === item}
              data-active={range === item ? "true" : "false"}
              disabled={loading}
              className="segment-item disabled:opacity-50"
              onClick={() => setRange(parsePerformanceRange(item))}
            >
              {item}
            </button>
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
        <ValueSvg points={valued} labels={axis} currency={currency} last={last} range={range} />
      )}
    </section>
  );
}

function ValueSvg({
  points,
  labels,
  currency,
  last,
  range,
  height = 200,
}: {
  points: { date: string; marketValue: number }[];
  labels: [string, string];
  currency: string;
  last: number | null;
  range: PerformanceRange;
  height?: number;
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const data = points.map((point) => point.marketValue);
  const width = 640;
  const padX = 8;
  const padY = 12;
  const bottomPad = 28;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = Math.max(max - min, 0.0001);

  const coords = data.map((value, i) => {
    const x = padX + (i / Math.max(data.length - 1, 1)) * (width - padX * 2);
    const y = padY + (1 - (value - min) / span) * (height - padY * 2);
    return { x, y };
  });

  const line = coords.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" ");
  const area = `${line} L ${coords[coords.length - 1].x} ${height} L ${coords[0].x} ${height} Z`;
  const lastLabel = last == null ? "" : `, last ${formatPrice(last)} ${currency}`;

  const indexFromClientX = (clientX: number): number => {
    const el = wrapRef.current;
    if (!el) return 0;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0) return 0;
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    const svgX = ratio * width;
    const frac = (svgX - padX) / (width - padX * 2);
    return Math.min(data.length - 1, Math.max(0, Math.round(frac * (data.length - 1))));
  };

  const hovered = hoverIndex != null ? points[hoverIndex] : null;
  const hoverCoord = hoverIndex != null ? coords[hoverIndex] : null;
  // Clamp tooltip so it never overflows the card on narrow widths.
  const tooltipLeftPct =
    hoverCoord != null ? Math.min(88, Math.max(12, (hoverCoord.x / width) * 100)) : 50;

  return (
    <div ref={wrapRef} className="relative min-w-0">
      <svg
        viewBox={`0 0 ${width} ${height + bottomPad}`}
        className="h-auto w-full"
        role="img"
        aria-label={`Portfolio value, ${range}${lastLabel}`}
        tabIndex={0}
        onMouseMove={(event) => setHoverIndex(indexFromClientX(event.clientX))}
        onMouseLeave={() => setHoverIndex(null)}
        onTouchStart={(event) => {
          if (event.touches.length > 0) setHoverIndex(indexFromClientX(event.touches[0].clientX));
        }}
        onTouchMove={(event) => {
          if (event.touches.length > 0) setHoverIndex(indexFromClientX(event.touches[0].clientX));
        }}
        onTouchEnd={() => setHoverIndex(null)}
        onKeyDown={(event) => {
          if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault();
            setHoverIndex((prev) => {
              const base = prev ?? data.length - 1;
              const next = event.key === "ArrowLeft" ? base - 1 : base + 1;
              return Math.min(data.length - 1, Math.max(0, next));
            });
          } else if (event.key === "Escape") {
            setHoverIndex(null);
          }
        }}
      >
        <defs>
          <linearGradient id="portfolio-value-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" style={{ stopColor: "var(--color-teal-400)" }} stopOpacity="0.22" />
            <stop offset="100%" style={{ stopColor: "var(--color-teal-400)" }} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#portfolio-value-fill)" />
        <path d={line} fill="none" style={{ stroke: "var(--color-teal-400)" }} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
        {hoverCoord != null ? (
          <g>
            <line
              x1={hoverCoord.x}
              x2={hoverCoord.x}
              y1={padY}
              y2={height}
              style={{ stroke: "var(--color-gray-500)" }}
              strokeWidth="1"
              strokeDasharray="3 3"
              opacity="0.7"
            />
            <circle
              cx={hoverCoord.x}
              cy={hoverCoord.y}
              r="4"
              style={{ fill: "var(--color-teal-400)", stroke: "var(--color-gray-900)" }}
              strokeWidth="1.5"
            />
          </g>
        ) : null}
        {labels.map((label, i) => {
          const anchor = i === 0 ? "start" : "end";
          const ax = i === 0 ? padX : width - padX;
          return (
            <text key={label} x={ax} y={height + 20} textAnchor={anchor} style={{ fill: "var(--color-gray-500)" }} fontSize="11">
              {label}
            </text>
          );
        })}
      </svg>
      {hovered && hoverCoord ? (
        <div
          role="status"
          className="pointer-events-none absolute top-0 z-10 -translate-x-1/2 rounded-md border border-gray-600 bg-gray-900/95 px-2.5 py-1.5 text-center shadow-xl"
          style={{ left: `${tooltipLeftPct}%` }}
        >
          <p className="text-[11px] whitespace-nowrap text-gray-400">{hovered.date}</p>
          <p className="text-sm font-semibold whitespace-nowrap tabular-nums text-gray-100">
            {formatPrice(hovered.marketValue)}{" "}
            <span className="text-[11px] font-medium text-gray-500">{currency}</span>
          </p>
        </div>
      ) : null}
    </div>
  );
}
