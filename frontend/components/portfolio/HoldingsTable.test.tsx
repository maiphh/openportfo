import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HoldingsTable from "@/components/portfolio/HoldingsTable";
import type { PortfolioLine } from "@/lib/portfolio";
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

function line(overrides: Partial<PortfolioLine> = {}): PortfolioLine {
  return {
    userId: "alice",
    assetType: "crypto",
    symbol: "BTC",
    assetId: "bitcoin",
    qty: "1",
    avgCost: "30000",
    currency: "USD",
    price: "40000",
    marketValue: "40000",
    costBasis: "30000",
    pnl: "10000",
    pnlPercent: "0.3333",
    missingPrice: false,
    stale: false,
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
});

describe("HoldingsTable unit FX", () => {
  it("shows Avg cost and Price in display currency when API fields exist", () => {
    render(
      <HoldingsTable
        lines={[
          line({
            avgCostDisplay: "27600",
            priceDisplay: "36800",
            marketValueDisplay: "40000",
            pnlDisplay: "9200",
          }),
        ]}
        displayCurrency="EUR"
        onEdit={() => undefined}
        onDelete={() => undefined}
      />,
    );

    expect(screen.getByText(`${formatPrice(27600)} EUR`)).toBeInTheDocument();
    expect(screen.getByText(`${formatPrice(36800)} EUR`)).toBeInTheDocument();
    expect(screen.queryByText(/USD/)).not.toBeInTheDocument();
  });

  it("falls back to convertToDisplay when API unit fields are absent", () => {
    render(
      <HoldingsTable
        lines={[line({ marketValueDisplay: "40000", pnlDisplay: "10000" })]}
        displayCurrency="EUR"
        convertToDisplay={(amount) => amount * 0.92}
        onEdit={() => undefined}
        onDelete={() => undefined}
      />,
    );

    expect(screen.getByText(`${formatPrice(27600)} EUR`)).toBeInTheDocument();
    expect(screen.getByText(`${formatPrice(36800)} EUR`)).toBeInTheDocument();
  });

  it("keeps native amounts and currency when FX is missing", () => {
    render(
      <HoldingsTable
        lines={[line()]}
        displayCurrency="EUR"
        convertToDisplay={() => null}
        onEdit={() => undefined}
        onDelete={() => undefined}
      />,
    );

    expect(screen.getByText(`${formatPrice(30000)} USD`)).toBeInTheDocument();
    expect(screen.getAllByText(`${formatPrice(40000)} USD`).length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText(/EUR/)).not.toBeInTheDocument();
  });

  it("shows em dash for Price when quote is missing", () => {
    render(
      <HoldingsTable
        lines={[
          line({
            price: null,
            priceDisplay: null,
            missingPrice: true,
            marketValue: null,
            avgCostDisplay: "27600",
          }),
        ]}
        displayCurrency="EUR"
        onEdit={() => undefined}
        onDelete={() => undefined}
      />,
    );

    expect(screen.getByText(`${formatPrice(27600)} EUR`)).toBeInTheDocument();
    const cells = screen.getAllByRole("cell");
    expect(cells.some((cell) => cell.textContent === "—")).toBe(true);
  });
});
