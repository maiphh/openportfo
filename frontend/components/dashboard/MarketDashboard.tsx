import MarketQuotes from "@/components/dashboard/MarketQuotes";
import StockHeatmap from "@/components/dashboard/StockHeatmap";
import TopStories from "@/components/dashboard/TopStories";
import type { MarketKind } from "@/lib/api";

export default function MarketDashboard({ market }: { market: MarketKind }) {
  return (
    <div className="home-wrapper flex min-h-screen">
      <header className="page-enter flex w-full flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">Markets</p>
        <h1 className="page-title">{market === "crypto" ? "Crypto" : "Vietnam stocks"}</h1>
        <p className="max-w-2xl text-sm text-gray-500">
          {market === "crypto"
            ? "Live category heatmap and quotes from CoinGecko."
            : "HOSE industry heatmap and quote board powered by vnstock."}
        </p>
      </header>
      <section className="page-enter stagger-1 w-full">
        <StockHeatmap market={market} />
      </section>
      <section className="home-section page-enter stagger-2">
        <div className="min-w-0 xl:col-span-2">
          <MarketQuotes market={market} />
        </div>
        <div className="min-w-0 xl:col-span-1">
          <TopStories />
        </div>
      </section>
    </div>
  );
}
