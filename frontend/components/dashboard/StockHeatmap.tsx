"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import AssetLink from "@/components/AssetLink";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { Button } from "@/components/ui/button";
import { fetchMarketHeatmap, type MarketKind } from "@/lib/api";
import { rememberLogosFromHeatmap } from "@/lib/logo-cache";
import { readHeatmapCache, writeHeatmapCache } from "@/lib/markets-cache";
import { layoutTreemap, type TreemapRect } from "@/lib/treemap";
import type { HeatmapSector } from "@/types/markets";
import { cn, formatPct, heatmapColor } from "@/lib/utils";

type LoadState = "loading" | "updating" | "live" | "stale" | "error";

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
      imageUrl: stock.imageUrl,
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

function HeatmapSkeleton() {
  return (
    <div
      className="relative h-[min(72vh,820px)] min-h-[560px] w-full animate-pulse bg-gray-800 p-3"
      data-testid="heatmap-skeleton"
    >
      <div className="grid h-full grid-cols-4 grid-rows-3 gap-2">
        {Array.from({ length: 12 }).map((_, index) => (
          <div key={index} className="rounded-sm bg-gray-700/60" />
        ))}
      </div>
    </div>
  );
}

export default function StockHeatmap({ market = "stock" }: { market?: MarketKind }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 1200, height: 720 });
  const [hover, setHover] = useState<TreemapRect | null>(null);
  const [sectorsData, setSectorsData] = useState<HeatmapSector[]>([]);
  const [source, setSource] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

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
  }, [source]);

  useLayoutEffect(() => {
    const cached = readHeatmapCache(market);
    if (cached) {
      setSectorsData(cached.payload.sectors);
      setSource("updating");
      setError(null);
    } else {
      setSectorsData([]);
      setSource("loading");
      setError(null);
    }
    setHover(null);
  }, [market, reloadKey]);

  useEffect(() => {
    const controller = new AbortController();
    fetchMarketHeatmap({
      market,
      limit: 100,
      signal: controller.signal,
      ...(market === "stock" ? { exchange: "HOSE" } : {}),
    })
      .then((data) => {
        if (controller.signal.aborted) return;
        const hasStocks = data.sectors.some((sector) => sector.stocks.length > 0);
        if (!hasStocks) {
          throw new Error("Empty heatmap");
        }
        writeHeatmapCache(market, data);
        setSectorsData(data.sectors);
        setSource("live");
        setError(null);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        const cached = readHeatmapCache(market);
        if (cached) {
          setSectorsData(cached.payload.sectors);
          setSource("stale");
          setError(err instanceof Error ? err.message : "Heatmap unavailable");
          return;
        }
        setSectorsData([]);
        setSource("error");
        setError(err instanceof Error ? err.message : "Heatmap unavailable");
      });
    return () => controller.abort();
  }, [market, reloadKey]);

  useEffect(() => {
    if (sectorsData.length === 0) return;
    rememberLogosFromHeatmap(
      market,
      sectorsData.flatMap((sector) => sector.stocks),
    );
  }, [market, sectorsData]);

  const showBoard = source === "live" || source === "updating" || source === "stale";

  const laid = useMemo(
    () => layoutTreemap(sectorNodes(sectorsData), size.width, size.height, 2),
    [sectorsData, size.height, size.width],
  );
  const cells = useMemo(() => flatten(laid).filter((node) => node.symbol), [laid]);
  const sectors = laid;

  return (
    <div className="w-full">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-sm font-medium text-gray-200">
            {market === "crypto" ? "Crypto heatmap" : "Stock heatmap"}
          </h3>
          <p className="mt-0.5 text-xs text-gray-500">
            {market === "crypto" ? "Sized by market cap · 24h change" : "Sized by liquidity · session change"}
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-gray-500">
          {source === "loading" ? (market === "crypto" ? "Loading crypto market…" : "Loading VN market…") : null}
          {source === "updating" ? "cached (updating…)" : null}
          {source === "stale" ? "cached (refresh failed)" : null}
          {source === "live" ? (market === "crypto" ? "CoinGecko" : "HOSE · vnstock") : null}
          {source === "stale" ? (
            <Button type="button" variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          ) : null}
        </div>
      </div>
      <div className="surface-card overflow-hidden">
        {source === "loading" ? <HeatmapSkeleton /> : null}
        {source === "error" ? (
          <div
            className="flex h-[min(72vh,820px)] min-h-[560px] flex-col items-center justify-center gap-3 bg-gray-800/40 px-4 text-center"
            data-testid="heatmap-error"
          >
            <p className="text-sm text-gray-400">{error ?? "Heatmap unavailable"}</p>
            <Button type="button" variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          </div>
        ) : null}
        {showBoard ? (
          <>
            <div ref={hostRef} className="relative h-[min(72vh,820px)] min-h-[560px] w-full bg-gray-900/40">
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
                  <AssetLink
                    key={cell.id}
                    assetType={market}
                    id={cell.symbol!}
                    onMouseEnter={() => setHover(cell)}
                    onMouseLeave={() => setHover((current) => (current?.id === cell.id ? null : current))}
                    className="absolute overflow-hidden text-left text-inherit transition-opacity hover:brightness-125 hover:text-inherit"
                    style={{
                      left: cell.x,
                      top: cell.y,
                      width: cell.width,
                      height: cell.height,
                      background: heatmapColor(pct),
                    }}
                    title={cell.symbol}
                  >
                    <span className="flex h-full flex-col items-center justify-center gap-1 px-1 text-center">
                      {showLogo ? (
                        <CompanyLogo
                          symbol={cell.symbol!}
                          size={28}
                          assetType={market}
                          src={cell.imageUrl}
                        />
                      ) : null}
                      {showSymbol ? (
                        <span className="text-[11px] font-semibold leading-none text-white/95">{cell.symbol}</span>
                      ) : null}
                      {showPct ? (
                        <span className="text-[11px] font-medium leading-none text-white/90">{formatPct(pct)}</span>
                      ) : null}
                    </span>
                  </AssetLink>
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
                  <div className="flex items-center gap-2 font-semibold">
                    <CompanyLogo
                      symbol={hover.symbol}
                      size={16}
                      assetType={market}
                      src={hover.imageUrl}
                    />
                    {hover.symbol}
                  </div>
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
          </>
        ) : null}
      </div>
    </div>
  );
}
