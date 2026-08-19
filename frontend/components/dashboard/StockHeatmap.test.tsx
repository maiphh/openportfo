import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StockHeatmap from "@/components/dashboard/StockHeatmap";

const fetchMarketHeatmap = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchMarketHeatmap: (...args: unknown[]) => fetchMarketHeatmap(...args),
  };
});

const liveSectors = [
  {
    name: "Banks",
    stocks: [{ symbol: "VCB", name: "Vietcombank", changePct: 1.25, marketCap: 400 }],
  },
];

describe("StockHeatmap", () => {
  beforeEach(() => {
    fetchMarketHeatmap.mockReset();
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows a skeleton while loading and never seeds mock tickers", async () => {
    let resolveFetch: (value: unknown) => void = () => {};
    fetchMarketHeatmap.mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );

    render(<StockHeatmap market="stock" />);

    expect(screen.getByTestId("heatmap-skeleton")).toBeInTheDocument();
    expect(screen.queryByText("NVDA")).not.toBeInTheDocument();
    expect(screen.queryByText("Demo data")).not.toBeInTheDocument();
    expect(fetchMarketHeatmap).toHaveBeenCalledWith(
      expect.objectContaining({ market: "stock", exchange: "HOSE" }),
    );

    resolveFetch({ sectors: liveSectors, limit: 100, source: "vnstock" });
    await waitFor(() => {
      expect(screen.getByText("VCB")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("heatmap-skeleton")).not.toBeInTheDocument();
    expect(screen.getByText("HOSE · vnstock")).toBeInTheDocument();
  });

  it("loads crypto heatmap from the crypto market option", async () => {
    fetchMarketHeatmap.mockResolvedValue({
      sectors: [
        {
          name: "Layer 1",
          stocks: [{ symbol: "BTC", name: "Bitcoin", changePct: 2.1, marketCap: 900 }],
        },
      ],
      limit: 100,
      source: "coingecko",
    });

    render(<StockHeatmap market="crypto" />);

    await waitFor(() => {
      expect(screen.getByText("BTC")).toBeInTheDocument();
    });
    expect(fetchMarketHeatmap).toHaveBeenCalledWith(expect.objectContaining({ market: "crypto" }));
    expect(screen.getByText("CoinGecko")).toBeInTheDocument();
  });

  it("shows error + Retry on empty payload and recovers on retry", async () => {
    fetchMarketHeatmap
      .mockResolvedValueOnce({ sectors: [], limit: 100, source: "vnstock" })
      .mockResolvedValueOnce({ sectors: liveSectors, limit: 100, source: "vnstock" });

    render(<StockHeatmap market="stock" />);

    await waitFor(() => {
      expect(screen.getByTestId("heatmap-error")).toBeInTheDocument();
    });
    expect(screen.getByText(/Empty heatmap/i)).toBeInTheDocument();
    expect(screen.queryByText("Demo data")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByText("VCB")).toBeInTheDocument();
    });
    expect(fetchMarketHeatmap).toHaveBeenCalledTimes(2);
  });

  it("shows error + Retry when the request fails", async () => {
    fetchMarketHeatmap.mockRejectedValue(new Error("Heatmap HTTP 502"));

    render(<StockHeatmap market="stock" />);

    await waitFor(() => {
      expect(screen.getByTestId("heatmap-error")).toBeInTheDocument();
    });
    expect(screen.getByText(/Heatmap HTTP 502/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByText("NVDA")).not.toBeInTheDocument();
  });
});
