import MarketQuotes from "@/components/dashboard/MarketQuotes";
import StockHeatmap from "@/components/dashboard/StockHeatmap";
import TopStories from "@/components/dashboard/TopStories";
import type { MarketKind } from "@/lib/api";

export default function MarketDashboard({ market }: { market: MarketKind }) {
  return (
    <div className="home-wrapper flex min-h-screen">
      <section className="w-full">
        <StockHeatmap market={market} />
      </section>
      <section className="home-section">
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
