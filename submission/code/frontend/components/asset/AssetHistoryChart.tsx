"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { ChartCandlestick, ChartLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  buildCandles,
  type ChartMode,
  type ChartPricePoint,
  type ChartRange,
} from "@/lib/asset";
import { cn, formatPrice } from "@/lib/utils";

const TEAL = "#2dd4bf";
const RED = "#ef4444";
const GRID = "rgba(75, 85, 99, 0.35)";
const TEXT = "#9ca3af";

function formatChartDate(t: string | null | undefined): string {
  if (!t) return "—";
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return t;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatParamTime(time: Time): string {
  if (typeof time === "string") return formatChartDate(time);
  if (typeof time === "number") {
    return formatChartDate(new Date(time * 1000).toISOString());
  }
  if (time && typeof time === "object" && "year" in time) {
    const m = String(time.month).padStart(2, "0");
    const d = String(time.day).padStart(2, "0");
    return formatChartDate(`${time.year}-${m}-${d}`);
  }
  return "—";
}

function toUtcSeconds(t: string | null, fallbackIndex: number): UTCTimestamp {
  if (t) {
    const ms = Date.parse(t);
    if (Number.isFinite(ms)) return Math.floor(ms / 1000) as UTCTimestamp;
  }
  return (1_700_000_000 + fallbackIndex * 86_400) as UTCTimestamp;
}

function dayTime(t: string | null, fallbackIndex: number): Time {
  if (t) {
    const ms = Date.parse(t);
    if (Number.isFinite(ms)) {
      return new Date(ms).toISOString().slice(0, 10);
    }
    if (/^\d{4}-\d{2}-\d{2}/.test(t)) return t.slice(0, 10);
  }
  return toUtcSeconds(null, fallbackIndex);
}

function toLineData(points: ChartPricePoint[]) {
  const seen = new Set<number>();
  const data: { time: UTCTimestamp; value: number }[] = [];
  points.forEach((point, i) => {
    let time = toUtcSeconds(point.t, i);
    while (seen.has(time)) time = ((time as number) + 1) as UTCTimestamp;
    seen.add(time);
    data.push({ time, value: point.price });
  });
  return data;
}

function toCandleData(points: ChartPricePoint[]) {
  const candles = buildCandles(points);
  const seen = new Set<string | number>();
  const data: {
    time: Time;
    open: number;
    high: number;
    low: number;
    close: number;
  }[] = [];

  candles.forEach((c, i) => {
    let time = dayTime(c.t, i);
    const key = typeof time === "object" ? JSON.stringify(time) : time;
    if (seen.has(key)) {
      time = toUtcSeconds(c.t, i);
    }
    seen.add(typeof time === "object" ? JSON.stringify(time) : time);
    data.push({
      time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    });
  });
  return data;
}

type TooltipState = {
  left: number;
  title: string;
  rows: { label: string; value: string }[];
};

export default function AssetHistoryChart({
  points,
  range,
  currency,
  mode,
  onModeChange,
  height = 260,
}: {
  points: ChartPricePoint[];
  range: ChartRange;
  currency?: string;
  mode: ChartMode;
  onModeChange: (mode: ChartMode) => void;
  height?: number;
}) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | ISeriesApi<"Candlestick"> | null>(null);

  const lineData = useMemo(() => toLineData(points), [points]);
  const candleData = useMemo(() => toCandleData(points), [points]);
  const currencyLabel = currency?.trim() || "";

  useEffect(() => {
    const el = containerRef.current;
    if (!el || points.length < 2) return;

    const chart = createChart(el, {
      autoSize: true,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: TEXT,
        fontSize: 11,
      },
      grid: {
        vertLines: { color: GRID },
        horzLines: { color: GRID },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: "rgba(156, 163, 175, 0.55)",
          labelBackgroundColor: "#111827",
        },
        horzLine: {
          color: "rgba(156, 163, 175, 0.55)",
          labelBackgroundColor: "#111827",
        },
      },
      rightPriceScale: {
        borderVisible: false,
        scaleMargins: { top: 0.12, bottom: 0.08 },
      },
      timeScale: {
        borderVisible: false,
        timeVisible: range === "7d",
        secondsVisible: false,
      },
      localization: {
        priceFormatter: (price: number) => formatPrice(price),
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    });
    chartRef.current = chart;

    let series: ISeriesApi<"Area"> | ISeriesApi<"Candlestick">;
    if (mode === "line") {
      series = chart.addSeries(AreaSeries, {
        lineColor: TEAL,
        topColor: "rgba(45, 212, 191, 0.28)",
        bottomColor: "rgba(45, 212, 191, 0)",
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 5,
        crosshairMarkerBorderColor: "#111827",
        crosshairMarkerBackgroundColor: TEAL,
      });
      series.setData(lineData);
    } else {
      series = chart.addSeries(CandlestickSeries, {
        upColor: TEAL,
        downColor: RED,
        borderUpColor: TEAL,
        borderDownColor: RED,
        wickUpColor: TEAL,
        wickDownColor: RED,
      });
      series.setData(candleData);
    }
    seriesRef.current = series;
    chart.timeScale().fitContent();

    chart.subscribeCrosshairMove((param) => {
      if (
        param.time === undefined ||
        !param.point ||
        param.point.x < 0 ||
        param.point.y < 0
      ) {
        setTooltip(null);
        return;
      }

      const raw = param.seriesData.get(series);
      if (!raw) {
        setTooltip(null);
        return;
      }

      const width = el.clientWidth || 1;
      const leftPct = Math.min(Math.max((param.point.x / width) * 100, 12), 88);
      const title = formatParamTime(param.time);

      if (mode === "line" && "value" in raw && typeof raw.value === "number") {
        setTooltip({
          left: leftPct,
          title,
          rows: [
            {
              label: "Price",
              value: `${formatPrice(raw.value)}${currencyLabel ? ` ${currencyLabel}` : ""}`,
            },
          ],
        });
        return;
      }

      if (
        mode === "candle" &&
        "open" in raw &&
        "high" in raw &&
        "low" in raw &&
        "close" in raw
      ) {
        setTooltip({
          left: leftPct,
          title,
          rows: [
            { label: "Open", value: formatPrice(Number(raw.open)) },
            { label: "High", value: formatPrice(Number(raw.high)) },
            { label: "Low", value: formatPrice(Number(raw.low)) },
            { label: "Close", value: formatPrice(Number(raw.close)) },
          ],
        });
        return;
      }

      setTooltip(null);
    });

    return () => {
      setTooltip(null);
      seriesRef.current = null;
      chartRef.current = null;
      chart.remove();
    };
  }, [candleData, currencyLabel, height, lineData, mode, points.length, range]);

  if (points.length < 2) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-gray-600 bg-gray-900/40 text-sm text-gray-500"
        style={{ height }}
      >
        No chart data for this range.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-end gap-1" role="tablist" aria-label="Chart style">
        <Button
          type="button"
          size="sm"
          variant={mode === "line" ? "default" : "outline"}
          role="tab"
          aria-selected={mode === "line"}
          onClick={() => onModeChange("line")}
        >
          <ChartLine className="h-3.5 w-3.5" aria-hidden />
          Line
        </Button>
        <Button
          type="button"
          size="sm"
          variant={mode === "candle" ? "default" : "outline"}
          role="tab"
          aria-selected={mode === "candle"}
          onClick={() => onModeChange("candle")}
        >
          <ChartCandlestick className="h-3.5 w-3.5" aria-hidden />
          Candle
        </Button>
      </div>

      <div className="relative" role="img" aria-label={`Asset price history ${mode} chart (${range})`}>
        <div ref={containerRef} className="w-full" style={{ height }} />
        {tooltip && (
          <div
            className={cn(
              "pointer-events-none absolute top-2 z-10 min-w-[9.5rem] -translate-x-1/2 rounded-md border border-gray-600 bg-gray-950/95 px-2.5 py-2 shadow-lg",
            )}
            style={{ left: `${tooltip.left}%` }}
            role="tooltip"
          >
            <p className="text-[11px] font-medium text-gray-300">{tooltip.title}</p>
            <dl className="mt-1 space-y-0.5">
              {tooltip.rows.map((row) => (
                <div key={row.label} className="flex items-baseline justify-between gap-3 text-[11px]">
                  <dt className="text-gray-500">{row.label}</dt>
                  <dd className="tabular-nums text-gray-100">{row.value}</dd>
                </div>
              ))}
            </dl>
            {mode === "candle" && currencyLabel ? (
              <p className="mt-1 text-[10px] text-gray-500">{currencyLabel}</p>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
