import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import MarketQuotes from "@/components/dashboard/MarketQuotes";

const fetchMarketQuotes = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchMarketQuotes: (...args: unknown[]) => fetchMarketQuotes(...args),
  };
});

const liveGroups = [
  {
    name: "BANKS",
    rows: [
      {
        symbol: "VCB",
        name: "Vietcombank",
        value: 90,
        change: 1,
        changePct: 1.1,
        open: 89,
        high: 91,
        low: 88,
        prev: 89,
      },
    ],
  },
];

describe("MarketQuotes", () => {
  beforeEach(() => {
    fetchMarketQuotes.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("shows a skeleton while loading and never seeds mock tickers", async () => {
    let resolveFetch: (value: unknown) => void = () => {};
    fetchMarketQuotes.mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );

    render(<MarketQuotes market="stock" />);

    expect(screen.getByTestId("quotes-skeleton")).toBeInTheDocument();
    expect(screen.queryByText("Apple")).not.toBeInTheDocument();
    expect(screen.queryByText("Demo data")).not.toBeInTheDocument();
    expect(fetchMarketQuotes).toHaveBeenCalledWith(
      expect.objectContaining({ market: "stock", exchange: "HOSE" }),
    );

    resolveFetch({ groups: liveGroups, limit: 80, source: "vnstock" });
    await waitFor(() => {
      expect(screen.getByText("Vietcombank")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("quotes-skeleton")).not.toBeInTheDocument();
    expect(screen.getByText("HOSE · vnstock")).toBeInTheDocument();
  });

  it("loads crypto quotes from the crypto market option", async () => {
    fetchMarketQuotes.mockResolvedValue({
      groups: [
        {
          name: "MAJOR",
          rows: [
            {
              symbol: "BTC",
              name: "Bitcoin",
              value: 97000,
              change: 100,
              changePct: 0.1,
              open: 96900,
              high: 98000,
              low: 96000,
              prev: 96900,
            },
          ],
        },
      ],
      limit: 80,
      source: "coingecko",
    });

    render(<MarketQuotes market="crypto" />);

    await waitFor(() => {
      expect(screen.getByText("Bitcoin")).toBeInTheDocument();
    });
    expect(fetchMarketQuotes).toHaveBeenCalledWith(expect.objectContaining({ market: "crypto" }));
    expect(screen.getByText("CoinGecko")).toBeInTheDocument();
  });

  it("shows error + Retry on empty payload and recovers on retry", async () => {
    fetchMarketQuotes
      .mockResolvedValueOnce({ groups: [], limit: 80, source: "vnstock" })
      .mockResolvedValueOnce({ groups: liveGroups, limit: 80, source: "vnstock" });

    render(<MarketQuotes market="stock" />);

    await waitFor(() => {
      expect(screen.getByTestId("quotes-error")).toBeInTheDocument();
    });
    expect(screen.getByText(/Empty quotes/i)).toBeInTheDocument();
    expect(screen.queryByText("Demo data")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByText("Vietcombank")).toBeInTheDocument();
    });
    expect(fetchMarketQuotes).toHaveBeenCalledTimes(2);
  });

  it("shows error + Retry when the request fails", async () => {
    fetchMarketQuotes.mockRejectedValue(new Error("Quotes HTTP 503"));

    render(<MarketQuotes market="stock" />);

    await waitFor(() => {
      expect(screen.getByTestId("quotes-error")).toBeInTheDocument();
    });
    expect(screen.getByText(/Quotes HTTP 503/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByText("Apple")).not.toBeInTheDocument();
  });
});
