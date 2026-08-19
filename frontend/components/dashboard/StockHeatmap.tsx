"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { fetchMarketHeatmap, type MarketKind } from "@/lib/api";
import { CRYPTO_HEATMAP_SECTORS, HEATMAP_SECTORS, type HeatmapSector } from "@/lib/mock-data";
import { layoutTreemap, type TreemapRect } from "@/lib/treemap";
import { cn, formatPct, heatmapColor } from "@/lib/utils";

function sectorNodes(sectors: HeatmapSector[]) {
  return sectors.map((sector) => ({
    id: sector.name,
    value: sector.stocks.reduce((sum, stock) => sum + stock.marketCap, 0),
    children: sector.stocks.map((stock) => ({
      id: `${sector.name}:${stock.symbol}`,
      value: stock.marketCap,
      symbol: stock.symbol,
      changePct: stock.changePct,
      sector: sector.name,
    })),
  }));
}

function flatten(nodes: TreemapRect[]): TreemapRect[] {
  const out: TreemapRect[] = [];
  for (const node of nodes) {
    out.push(node);
    if (node.children) out.push(...flatten(node.children));
  }
  return out;
}

function mockSectors(market: MarketKind) {
  return market === "crypto" ? CRYPTO_HEATMAP_SECTORS : HEATMAP_SECTORS;
}

export default function StockHeatmap({ market = "stock" }: { market?: MarketKind }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 1200, height: 720 });
  const [hover, setHover] = useState<TreemapRect | null>(null);
  const [sectorsData, setSectorsData] = useState<HeatmapSector[]>(() => mockSectors(market));
  const [source, setSource] = useState<"mock" | "live" | "loading">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const el = hostRef.current;
    if (!el) return;
    const measure = () => {
      const rect = el.getBoundingClientRect();
      setSize({ width: Math.max(320, rect.width), height: Math.max(480, rect.height) });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setSource("loading");
    setError(null);
    setSectorsData(mockSectors(market));
    fetchMarketHeatmap({ market, exchange: "HOSE", limit: 100, signal: controller.signal })
      .then((data) => {
        if (!data.sectors.length) {
          throw new Error("Empty heatmap");
        }
        setSectorsData(data.sectors);
        setSource("live");
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setSectorsData(mockSectors(market));
        setSource("mock");
        setError(err instanceof Error ? err.message : "Heatmap unavailable");
      });
    return () => controller.abort();
  }, [market]);

  const laid = useMemo(
    () => layoutTreemap(sectorNodes(sectorsData), size.width, size.height, 2),
    [sectorsData, size.height, size.width],
  );
  const cells = useMemo(() => flatten(laid).filter((node) => node.symbol), [laid]);
  const sectors = laid;

  return (
    <div className="w-full">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-2">
        <h3 className="text-2xl font-semibold text-gray-100">
          {market === "crypto" ? "Crypto Heatmap" : "Stock Heatmap"}
        </h3>
        <div className="text-[11px] text-gray-500">
          {source === "loading" ? (market === "crypto" ? "Loading crypto market…" : "Loading VN market…") : null}
          {source === "live" ? (market === "crypto" ? "CoinGecko" : "HOSE · vnstock") : null}
          {source === "mock" ? `Demo data${error ? ` (${error})` : ""}` : null}
        </div>
      </div>
      <div className="overflow-hidden rounded-lg border border-gray-600 bg-gray-800">
        <div ref={hostRef} className="relative h-[min(72vh,820px)] min-h-[560px] w-full bg-[#141414]">
          {sectors.map((sector) => (
            <div
              key={sector.id}
              className="pointer-events-none absolute overflow-hidden text-[10px] font-medium uppercase tracking-wide text-gray-500"
              style={{ left: sector.x, top: sector.y, width: sector.width, height: 16, padding: "2px 6px" }}
            >
              {sector.width > 72 ? sector.id : ""}
            </div>
          ))}
          {cells.map((cell) => {
            const pct = cell.changePct ?? 0;
            const showLogo = cell.width > 92 && cell.height > 72;
            const showSymbol = cell.width > 42 && cell.height > 32;
            const showPct = cell.width > 54 && cell.height > 44;
            return (
              <button
                key={cell.id}
                type="button"
                onMouseEnter={() => setHover(cell)}
                onMouseLeave={() => setHover((current) => (current?.id === cell.id ? null : current))}
                className="absolute overflow-hidden text-left transition-opacity hover:brightness-125"
                style={{
                  left: cell.x,
                  top: cell.y,
                  width: cell.width,
                  height: cell.height,
                  background: heatmapColor(pct),
                }}
              >
                <span className="flex h-full flex-col items-center justify-center gap-1 px-1 text-center">
                  {showLogo ? <CompanyLogo symbol={cell.symbol!} size={28} /> : null}
                  {showSymbol ? (
                    <span className="text-[11px] font-semibold leading-none text-white/95">{cell.symbol}</span>
                  ) : null}
                  {showPct ? (
                    <span className="text-[11px] font-medium leading-none text-white/90">{formatPct(pct)}</span>
                  ) : null}
                </span>
              </button>
            );
          })}
          {hover?.symbol ? (
            <div
              className="pointer-events-none absolute z-10 rounded-md border border-gray-600 bg-gray-900/95 px-3 py-2 text-xs text-gray-200 shadow-lg"
              style={{
                left: Math.min(hover.x + hover.width + 8, size.width - 180),
                top: Math.min(hover.y + 8, size.height - 64),
              }}
            >
              <div className="font-semibold">{hover.symbol}</div>
              <div className="text-gray-500">{hover.sector}</div>
              <div className={cn(hover.changePct && hover.changePct > 0 ? "text-teal-400" : "text-red-500")}>
                {formatPct(hover.changePct ?? 0)}
              </div>
            </div>
          ) : null}
        </div>
        <div className="flex items-center gap-3 border-t border-gray-700 px-4 py-2">
          <span className="text-[11px] text-gray-500">-5.5%</span>
          <div
            className="h-2 flex-1 rounded-sm"
            style={{
              background:
                "linear-gradient(90deg, rgb(122,22,32) 0%, rgb(32,32,36) 50%, rgb(14,98,56) 100%)",
            }}
          />
          <span className="text-[11px] text-gray-500">5.5%</span>
        </div>
      </div>
    </div>
  );
}
