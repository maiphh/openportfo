import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import WatchlistTable from "@/components/watchlist/WatchlistTable";
import type { WatchlistItem } from "@/lib/watchlist";
import { formatPrice } from "@/lib/utils";

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

function item(overrides: Partial<WatchlistItem> = {}): WatchlistItem {
  return {
    userId: "alice",
    assetType: "crypto",
    symbol: "BTC",
    assetId: "bitcoin",
    price: "40000",
    currency: "USD",
    stale: false,
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
});

describe("WatchlistTable", () => {
  it("links symbols through AssetLink", () => {
    render(
      <WatchlistTable
        items={[item(), item({ assetType: "stock", symbol: "VNM", assetId: "VNM", currency: "VND", price: "90" })]}
        displayCurrency="USD"
        onRemove={() => undefined}
      />,
    );

    expect(screen.getByRole("link", { name: /BTC/ })).toHaveAttribute("href", "/crypto/bitcoin");
    expect(screen.getByRole("link", { name: /VNM/ })).toHaveAttribute("href", "/stock/VNM");
  });

  it("converts native quotes into the session currency", () => {
    render(
      <WatchlistTable
        items={[item()]}
        displayCurrency="EUR"
        convertToDisplay={(amount) => amount * 0.92}
        onRemove={() => undefined}
      />,
    );

    expect(screen.getByText(`${formatPrice(36800)} EUR`)).toBeInTheDocument();
  });

  it("shows em dash and a missing badge when the quote is absent", () => {
    render(
      <WatchlistTable
        items={[item({ price: null, currency: null })]}
        displayCurrency="VND"
        onRemove={() => undefined}
      />,
    );

    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText("Missing")).toBeInTheDocument();
  });

  it("shows a stale badge when the cache is stale", () => {
    render(
      <WatchlistTable items={[item({ stale: true })]} displayCurrency="USD" onRemove={() => undefined} />,
    );

    expect(screen.getByText("Stale")).toBeInTheDocument();
  });

  it("calls onRemove for the row", () => {
    const onRemove = vi.fn();
    const row = item();
    render(<WatchlistTable items={[row]} displayCurrency="USD" onRemove={onRemove} />);

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(onRemove).toHaveBeenCalledWith(row);
  });
});
