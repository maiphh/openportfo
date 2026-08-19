import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StockHeatmap from "@/components/dashboard/StockHeatmap";
import { writeHeatmapCache } from "@/lib/markets-cache";

const fetchMarketHeatmap = vi.fn();

vi.mock("next/link", () => ({
  default({
    href,
    children,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  },
}));

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

const cryptoSectors = [
  {
    name: "Layer 1",
    stocks: [{ symbol: "BTC", name: "Bitcoin", changePct: 2.1, marketCap: 900 }],
  },
];

describe("StockHeatmap", () => {
  beforeEach(() => {
    sessionStorage.clear();
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
    sessionStorage.clear();
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
      expect.objectContaining({ market: "stock", exchange: "HOSE", signal: expect.any(AbortSignal) }),
    );

    resolveFetch({ sectors: liveSectors, limit: 100, source: "vnstock" });
    await waitFor(() => {
      expect(screen.getByText("VCB")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("heatmap-skeleton")).not.toBeInTheDocument();
    expect(screen.getByText("HOSE · vnstock")).toBeInTheDocument();
  });

  it("loads crypto heatmap without a stock exchange option", async () => {
    fetchMarketHeatmap.mockResolvedValue({
      sectors: cryptoSectors,
      limit: 100,
      source: "coingecko",
    });

    render(<StockHeatmap market="crypto" />);

    await waitFor(() => {
      expect(screen.getByText("BTC")).toBeInTheDocument();
    });
    expect(fetchMarketHeatmap).toHaveBeenCalledWith(
      expect.objectContaining({ market: "crypto", signal: expect.any(AbortSignal) }),
    );
    expect(fetchMarketHeatmap.mock.calls[0]?.[0]).not.toHaveProperty("exchange");
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

  it("treats sectors with no stocks as empty", async () => {
    fetchMarketHeatmap.mockResolvedValue({
      sectors: [{ name: "Banks", stocks: [] }],
      limit: 100,
      source: "vnstock",
    });

    render(<StockHeatmap market="stock" />);

    await waitFor(() => {
      expect(screen.getByTestId("heatmap-error")).toBeInTheDocument();
    });
    expect(screen.getByText(/Empty heatmap/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
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

  it("ignores a late stock resolve after switching to crypto", async () => {
    let resolveStock: (value: unknown) => void = () => {};
    let resolveCrypto: (value: unknown) => void = () => {};

    fetchMarketHeatmap
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveStock = resolve;
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveCrypto = resolve;
          }),
      );

    const { rerender } = render(<StockHeatmap market="stock" />);
    expect(screen.getByTestId("heatmap-skeleton")).toBeInTheDocument();

    rerender(<StockHeatmap market="crypto" />);
    expect(screen.getByTestId("heatmap-skeleton")).toBeInTheDocument();
    expect(fetchMarketHeatmap).toHaveBeenCalledTimes(2);

    resolveStock({ sectors: liveSectors, limit: 100, source: "vnstock" });
    await waitFor(() => {
      expect(screen.queryByText("VCB")).not.toBeInTheDocument();
    });
    expect(screen.queryByTestId("heatmap-error")).not.toBeInTheDocument();
    expect(screen.getByTestId("heatmap-skeleton")).toBeInTheDocument();

    resolveCrypto({ sectors: cryptoSectors, limit: 100, source: "coingecko" });
    await waitFor(() => {
      expect(screen.getByText("BTC")).toBeInTheDocument();
    });
    expect(screen.queryByText("VCB")).not.toBeInTheDocument();
  });

  it("paints a session-cached board without a skeleton and writes cache after live fetch", async () => {
    fetchMarketHeatmap.mockResolvedValue({
      sectors: liveSectors,
      limit: 100,
      source: "vnstock",
    });

    const { unmount } = render(<StockHeatmap market="stock" />);
    await waitFor(() => {
      expect(screen.getByText("VCB")).toBeInTheDocument();
    });
    expect(sessionStorage.getItem("artryx.markets.heatmap.stock")).toBeTruthy();
    unmount();

    fetchMarketHeatmap.mockReturnValue(new Promise(() => {}));
    render(<StockHeatmap market="stock" />);
    expect(screen.getByText("VCB")).toBeInTheDocument();
    expect(screen.queryByTestId("heatmap-skeleton")).not.toBeInTheDocument();
    expect(screen.getByText("cached (updating…)")).toBeInTheDocument();
  });

  it("keeps the cached board and offers Retry when revalidation fails", async () => {
    writeHeatmapCache("stock", { sectors: liveSectors, limit: 100, source: "vnstock" });
    fetchMarketHeatmap.mockRejectedValue(new Error("Heatmap HTTP 502"));

    render(<StockHeatmap market="stock" />);

    await waitFor(() => {
      expect(screen.getByText("cached (refresh failed)")).toBeInTheDocument();
    });
    expect(screen.getByText("VCB")).toBeInTheDocument();
    expect(screen.queryByTestId("heatmap-skeleton")).not.toBeInTheDocument();
    expect(screen.queryByTestId("heatmap-error")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByText("NVDA")).not.toBeInTheDocument();
  });

  it("treats an empty live payload as failure and keeps the cached board", async () => {
    writeHeatmapCache("stock", { sectors: liveSectors, limit: 100, source: "vnstock" });
    fetchMarketHeatmap.mockResolvedValue({ sectors: [], limit: 100, source: "vnstock" });

    render(<StockHeatmap market="stock" />);

    await waitFor(() => {
      expect(screen.getByText("cached (refresh failed)")).toBeInTheDocument();
    });
    expect(screen.getByText("VCB")).toBeInTheDocument();
    expect(screen.queryByTestId("heatmap-error")).not.toBeInTheDocument();
  });
});
