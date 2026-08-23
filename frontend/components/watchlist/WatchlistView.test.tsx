import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import WatchlistView from "@/components/watchlist/WatchlistView";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import { WatchlistApiError, type WatchlistItem } from "@/lib/watchlist";

const fetchWatchlist = vi.fn();
const addWatchlist = vi.fn();
const removeWatchlist = vi.fn();
const searchAssets = vi.fn();

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
    convertToDisplay: (amount: number, native: string) => (native === "VND" ? amount : null),
    asOf: null,
    fxStatus: "missing",
  }),
}));

vi.mock("@/lib/watchlist", async () => {
  const actual = await vi.importActual<typeof import("@/lib/watchlist")>("@/lib/watchlist");
  return {
    ...actual,
    fetchWatchlist: (...args: unknown[]) => fetchWatchlist(...args),
    addWatchlist: (...args: unknown[]) => addWatchlist(...args),
    removeWatchlist: (...args: unknown[]) => removeWatchlist(...args),
  };
});

vi.mock("@/lib/portfolio", async () => {
  const actual = await vi.importActual<typeof import("@/lib/portfolio")>("@/lib/portfolio");
  return {
    ...actual,
    searchAssets: (...args: unknown[]) => searchAssets(...args),
  };
});

function item(overrides: Partial<WatchlistItem> = {}): WatchlistItem {
  return {
    userId: "alice",
    assetType: "crypto",
    symbol: "BTC",
    assetId: "bitcoin",
    price: "97000",
    currency: "USD",
    stale: false,
    ...overrides,
  };
}

const vnmHit = {
  symbol: "VNM",
  name: "Vinamilk",
  assetId: "VNM",
  assetType: "stock" as const,
};

async function typeAndPick(symbol: string, type: "stock" | "crypto" = "stock") {
  fireEvent.click(screen.getAllByRole("button", { name: "Add to watchlist" })[0]);
  fireEvent.click(screen.getByRole("button", { name: type === "crypto" ? "Crypto" : "VN stock" }));
  const input = screen.getByPlaceholderText(type === "crypto" ? /e\.g\. BTC/i : /e\.g\. VNM/i);
  fireEvent.change(input, { target: { value: symbol } });
  await waitFor(() => {
    expect(screen.getByRole("button", { name: new RegExp(symbol) })).toBeInTheDocument();
  });
  fireEvent.click(screen.getByRole("button", { name: new RegExp(symbol) }));
}

function submitAdd() {
  const buttons = screen.getAllByRole("button", { name: /^Add to watchlist$/i });
  fireEvent.click(buttons[buttons.length - 1]);
}

describe("WatchlistView", () => {
  beforeEach(() => {
    fetchWatchlist.mockReset();
    addWatchlist.mockReset();
    removeWatchlist.mockReset();
    searchAssets.mockReset();
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  });

  afterEach(() => {
    cleanup();
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  });

  it("does not fetch watchlist data when unauthenticated", async () => {
    render(<WatchlistView />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Watchlist" })).toBeInTheDocument();
    });
    expect(screen.getByText(/Bearer access token/i)).toBeInTheDocument();
    expect(fetchWatchlist).not.toHaveBeenCalled();
  });

  it("loads items for an authenticated user", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    fetchWatchlist.mockResolvedValue([item()]);

    render(<WatchlistView />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /BTC/ })).toBeInTheDocument();
    });
    expect(fetchWatchlist).toHaveBeenCalledTimes(1);
  });

  it("adds a search-resolved asset and shows the new row", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    fetchWatchlist.mockResolvedValueOnce([]).mockResolvedValueOnce([
      item({
        assetType: "stock",
        symbol: "VNM",
        assetId: "VNM",
        price: "90",
        currency: "VND",
      }),
    ]);
    searchAssets.mockResolvedValue([vnmHit]);
    addWatchlist.mockResolvedValue({
      userId: "alice",
      assetType: "stock",
      symbol: "VNM",
      assetId: "VNM",
      stale: false,
    });

    render(<WatchlistView />);

    await waitFor(() => {
      expect(screen.getByText(/No names on your watchlist yet/i)).toBeInTheDocument();
    });

    await typeAndPick("VNM", "stock");
    submitAdd();

    await waitFor(() => {
      expect(addWatchlist).toHaveBeenCalledWith(
        { assetType: "stock", symbol: "VNM", assetId: "VNM" },
        expect.objectContaining({ token: "fake:alice" }),
      );
    });
    await waitFor(() => {
      expect(screen.getByRole("link", { name: /VNM/ })).toBeInTheDocument();
    });
    expect(fetchWatchlist).toHaveBeenCalledTimes(2);
  });

  it("shows a 409 inline error and leaves the list unchanged", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    const existing = [item()];
    fetchWatchlist.mockResolvedValue(existing);
    searchAssets.mockResolvedValue([
      { symbol: "BTC", name: "Bitcoin", assetId: "bitcoin", assetType: "crypto" },
    ]);
    addWatchlist.mockRejectedValue(new WatchlistApiError(409, "Watchlist item already exists"));

    render(<WatchlistView />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /BTC/ })).toBeInTheDocument();
    });

    await typeAndPick("BTC", "crypto");
    submitAdd();

    await waitFor(() => {
      expect(screen.getByText("Watchlist item already exists")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /BTC/ })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. BTC/i)).toBeInTheDocument();
    expect(fetchWatchlist).toHaveBeenCalledTimes(1);
  });

  it("removes a row after DELETE 204", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    fetchWatchlist.mockResolvedValue([item()]);
    removeWatchlist.mockResolvedValue(undefined);

    render(<WatchlistView />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /BTC/ })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    await waitFor(() => {
      expect(removeWatchlist).toHaveBeenCalledWith(
        "crypto",
        "BTC",
        expect.objectContaining({ token: "fake:alice" }),
      );
    });
    await waitFor(() => {
      expect(screen.queryByRole("link", { name: /BTC/ })).not.toBeInTheDocument();
    });
  });

  it("shows error + retry when the list request fails", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    fetchWatchlist.mockRejectedValueOnce(new Error("Watchlist HTTP 503")).mockResolvedValueOnce([item()]);

    render(<WatchlistView />);

    await waitFor(() => {
      expect(screen.getByTestId("watchlist-error")).toHaveTextContent("Watchlist HTTP 503");
    });

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /BTC/ })).toBeInTheDocument();
    });
    expect(fetchWatchlist).toHaveBeenCalledTimes(2);
  });
});
