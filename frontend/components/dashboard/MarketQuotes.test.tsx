import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import MarketQuotes from "@/components/dashboard/MarketQuotes";

const fetchMarketQuotes = vi.fn();

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

vi.mock("@/components/currency/CurrencyProvider", () => ({
  useDisplayCurrency: () => ({
    currency: "VND",
    setCurrency: () => {},
    rates: { base: "USD", rates: {}, asOf: null, provider: null, status: "missing" },
    ratesLoading: false,
    ratesAuthRequired: false,
    ratesError: null,
    refreshRates: async () => {},
    rateToDisplay: () => null,
    convertToDisplay: () => null,
    asOf: null,
    fxStatus: "missing",
  }),
}));

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

const cryptoGroups = [
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
      expect.objectContaining({ market: "stock", exchange: "HOSE", signal: expect.any(AbortSignal) }),
    );

    resolveFetch({ groups: liveGroups, limit: 80, source: "vnstock" });
    await waitFor(() => {
      expect(screen.getByText("Vietcombank")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("quotes-skeleton")).not.toBeInTheDocument();
    expect(screen.getByText("HOSE · vnstock")).toBeInTheDocument();
  });

  it("loads crypto quotes without a stock exchange option", async () => {
    fetchMarketQuotes.mockResolvedValue({
      groups: cryptoGroups,
      limit: 80,
      source: "coingecko",
    });

    render(<MarketQuotes market="crypto" />);

    await waitFor(() => {
      expect(screen.getByText("Bitcoin")).toBeInTheDocument();
    });
    expect(fetchMarketQuotes).toHaveBeenCalledWith(
      expect.objectContaining({ market: "crypto", signal: expect.any(AbortSignal) }),
    );
    expect(fetchMarketQuotes.mock.calls[0]?.[0]).not.toHaveProperty("exchange");
    expect(screen.getByText(/CoinGecko/)).toBeInTheDocument();
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

  it("treats groups with no rows as empty", async () => {
    fetchMarketQuotes.mockResolvedValue({
      groups: [{ name: "BANKS", rows: [] }],
      limit: 80,
      source: "vnstock",
    });

    render(<MarketQuotes market="stock" />);

    await waitFor(() => {
      expect(screen.getByTestId("quotes-error")).toBeInTheDocument();
    });
    expect(screen.getByText(/Empty quotes/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
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

  it("ignores a late stock resolve after switching to crypto", async () => {
    let resolveStock: (value: unknown) => void = () => {};
    let resolveCrypto: (value: unknown) => void = () => {};

    fetchMarketQuotes
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

    const { rerender } = render(<MarketQuotes market="stock" />);
    expect(screen.getByTestId("quotes-skeleton")).toBeInTheDocument();

    rerender(<MarketQuotes market="crypto" />);
    expect(screen.getByTestId("quotes-skeleton")).toBeInTheDocument();
    expect(fetchMarketQuotes).toHaveBeenCalledTimes(2);

    resolveStock({ groups: liveGroups, limit: 80, source: "vnstock" });
    await waitFor(() => {
      expect(screen.queryByText("Vietcombank")).not.toBeInTheDocument();
    });
    expect(screen.queryByTestId("quotes-error")).not.toBeInTheDocument();
    expect(screen.getByTestId("quotes-skeleton")).toBeInTheDocument();

    resolveCrypto({ groups: cryptoGroups, limit: 80, source: "coingecko" });
    await waitFor(() => {
      expect(screen.getByText("Bitcoin")).toBeInTheDocument();
    });
    expect(screen.queryByText("Vietcombank")).not.toBeInTheDocument();
  });
});
