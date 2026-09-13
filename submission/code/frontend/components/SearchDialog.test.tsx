import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SearchDialog from "@/components/SearchDialog";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import type { LiveSearchOutcome } from "@/lib/asset-search";
import type { AssetSearchHit } from "@/lib/portfolio";

const searchLiveCatalog = vi.fn<(...args: unknown[]) => Promise<LiveSearchOutcome>>();

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

vi.mock("@/lib/asset-search", async () => {
  const actual = await vi.importActual<typeof import("@/lib/asset-search")>("@/lib/asset-search");
  return {
    ...actual,
    searchLiveCatalog: (...args: unknown[]) => searchLiveCatalog(...args),
  };
});

const stockHit: AssetSearchHit = {
  symbol: "VNM",
  name: "Vinamilk",
  assetId: "VNM",
  assetType: "stock",
};

const cryptoHit: AssetSearchHit = {
  symbol: "BTC",
  name: "Bitcoin",
  assetId: "bitcoin",
  assetType: "crypto",
};

function emptyOutcome(overrides: Partial<LiveSearchOutcome> = {}): LiveSearchOutcome {
  return { hits: [], failedTypes: [], authRequired: false, ...overrides };
}

describe("SearchDialog", () => {
  beforeEach(() => {
    searchLiveCatalog.mockReset();
    searchLiveCatalog.mockResolvedValue(emptyOutcome());
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  });

  afterEach(() => {
    cleanup();
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  });

  it("does not fetch on empty query and shows helper copy", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    render(<SearchDialog open onClose={() => undefined} />);

    expect(await screen.findByText("Type to search")).toBeInTheDocument();
    expect(screen.queryByText("No mock matches")).not.toBeInTheDocument();
    expect(screen.queryByText("JPMorgan Chase")).not.toBeInTheDocument();

    await new Promise((resolve) => setTimeout(resolve, 350));
    expect(searchLiveCatalog).not.toHaveBeenCalled();
  });

  it("debounces then searches live catalog", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    searchLiveCatalog.mockResolvedValue(emptyOutcome({ hits: [stockHit, cryptoHit] }));

    render(<SearchDialog open onClose={() => undefined} />);
    const input = await screen.findByPlaceholderText("Search symbols or companies");
    fireEvent.change(input, { target: { value: "VNM" } });

    expect(searchLiveCatalog).not.toHaveBeenCalled();

    await waitFor(() => expect(searchLiveCatalog).toHaveBeenCalledTimes(1));
    expect(searchLiveCatalog).toHaveBeenCalledWith(
      expect.objectContaining({ q: "VNM", token: "fake:alice" }),
    );

    expect(await screen.findByRole("link", { name: /VNM/ })).toHaveAttribute("href", "/asset?type=stock&id=VNM");
    expect(screen.getByRole("link", { name: /BTC/ })).toHaveAttribute("href", "/asset?type=crypto&id=bitcoin");
    expect(screen.getByText("Stock")).toBeInTheDocument();
    expect(screen.getByText("Crypto")).toBeInTheDocument();
    expect(screen.queryByText(/68,420/)).not.toBeInTheDocument();
  });

  it("shows sign-in empty state on 401 and does not dump mock results", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    searchLiveCatalog.mockResolvedValue(emptyOutcome({ authRequired: true }));

    render(<SearchDialog open onClose={() => undefined} />);
    fireEvent.change(await screen.findByPlaceholderText("Search symbols or companies"), {
      target: { value: "btc" },
    });

    expect(await screen.findByText("Sign in to search")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByText("No mock matches")).not.toBeInTheDocument();
    expect(screen.queryByText("Bitcoin")).not.toBeInTheDocument();
    expect(screen.queryByText("Apple")).not.toBeInTheDocument();
  });

  it("shows sign-in empty state when unauthenticated without fetching", async () => {
    render(<SearchDialog open onClose={() => undefined} />);

    expect(await screen.findByText("Sign in to search")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Search symbols or companies"), {
      target: { value: "VNM" },
    });
    await new Promise((resolve) => setTimeout(resolve, 350));
    expect(searchLiveCatalog).not.toHaveBeenCalled();
    expect(screen.queryByText("Vinamilk")).not.toBeInTheDocument();
  });
});
