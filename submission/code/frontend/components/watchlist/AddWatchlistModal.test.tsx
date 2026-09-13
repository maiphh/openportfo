import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AddWatchlistModal from "@/components/watchlist/AddWatchlistModal";

const searchLiveCatalog = vi.fn();

vi.mock("@/lib/asset-search", async () => {
  const actual = await vi.importActual<typeof import("@/lib/asset-search")>("@/lib/asset-search");
  return {
    ...actual,
    searchLiveCatalog: (...args: unknown[]) => searchLiveCatalog(...args),
  };
});

const stockHit = { symbol: "VNM", name: "Vinamilk", assetId: "VNM", assetType: "stock" as const };
const cryptoHit = { symbol: "BTC", name: "Bitcoin", assetId: "bitcoin", assetType: "crypto" as const };

describe("AddWatchlistModal unified search (BL-033)", () => {
  beforeEach(() => {
    searchLiveCatalog.mockReset();
    searchLiveCatalog.mockResolvedValue({ hits: [], failedTypes: [], authRequired: false });
  });

  afterEach(() => cleanup());

  it("has no type toggle and uses a single unified placeholder", () => {
    render(<AddWatchlistModal open onClose={() => undefined} onSubmit={() => undefined} />);
    expect(screen.getByPlaceholderText(/e\.g\. VNM, FPT, BTC/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "VN stock" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Crypto" })).not.toBeInTheDocument();
  });

  it("searches both types with one query and shows badges", async () => {
    searchLiveCatalog.mockResolvedValue({ hits: [stockHit, cryptoHit], failedTypes: [], authRequired: false });
    render(<AddWatchlistModal open onClose={() => undefined} onSubmit={() => undefined} />);

    fireEvent.change(screen.getByPlaceholderText(/e\.g\. VNM, FPT, BTC/i), { target: { value: "v" } });

    await waitFor(() => expect(searchLiveCatalog).toHaveBeenCalledTimes(1));
    expect(searchLiveCatalog).toHaveBeenCalledWith(expect.objectContaining({ q: "v" }));
    expect(await screen.findByText("Vinamilk")).toBeInTheDocument();
    expect(screen.getByText("Bitcoin")).toBeInTheDocument();
    expect(screen.getByText("Stock")).toBeInTheDocument();
    expect(screen.getByText("Crypto")).toBeInTheDocument();
  });

  it("keeps other results and warns when one type fails", async () => {
    searchLiveCatalog.mockResolvedValue({ hits: [cryptoHit], failedTypes: ["stock"], authRequired: false });
    render(<AddWatchlistModal open onClose={() => undefined} onSubmit={() => undefined} />);

    fireEvent.change(screen.getByPlaceholderText(/e\.g\. VNM, FPT, BTC/i), { target: { value: "btc" } });

    expect(await screen.findByText(/Stock search failed/i)).toBeInTheDocument();
    expect(screen.getByText("Bitcoin")).toBeInTheDocument();
  });
});
