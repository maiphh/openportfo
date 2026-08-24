import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PortfolioDashboard from "@/components/portfolio/PortfolioDashboard";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import { PortfolioApiError, type PortfolioResponse } from "@/lib/portfolio";

const fetchPortfolio = vi.fn();
const exportPortfolioCsv = vi.fn();
const triggerBlobDownload = vi.fn();

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
    currency: "USD",
    setCurrency: () => {},
    rates: { base: "USD", rates: {}, asOf: null, provider: null, status: "missing" },
    ratesLoading: false,
    ratesAuthRequired: false,
    ratesError: null,
    refreshRates: async () => {},
    rateToDisplay: () => null,
    convertToDisplay: (amount: number, native: string) => (native === "USD" ? amount : null),
    asOf: null,
    fxStatus: "missing",
  }),
}));

vi.mock("@/components/portfolio/PortfolioValueChart", () => ({
  default: () => <div data-testid="value-chart" />,
}));

vi.mock("@/components/portfolio/PnlActivityHeatmap", () => ({
  default: () => <div data-testid="heatmap" />,
}));

vi.mock("@/lib/portfolio", async () => {
  const actual = await vi.importActual<typeof import("@/lib/portfolio")>("@/lib/portfolio");
  return {
    ...actual,
    fetchPortfolio: (...args: unknown[]) => fetchPortfolio(...args),
    refreshPortfolio: vi.fn(),
    exportPortfolioCsv: (...args: unknown[]) => exportPortfolioCsv(...args),
    triggerBlobDownload: (...args: unknown[]) => triggerBlobDownload(...args),
  };
});

function portfolioPayload(overrides: Partial<PortfolioResponse> = {}): PortfolioResponse {
  return {
    lines: [
      {
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
        pnlPercent: "0.3333333333333333333333333333",
        missingPrice: false,
        stale: false,
      },
    ],
    totalsByCurrency: {
      USD: { marketValue: "40000", costBasis: "30000", pnl: "10000", pnlPercent: "0.3333" },
    },
    totalsDisplay: null,
    fx: { status: "missing", rates: {} },
    asOf: "2026-08-09T12:00:00+00:00",
    displayCurrency: "USD",
    ...overrides,
  };
}

describe("PortfolioDashboard CSV export", () => {
  beforeEach(() => {
    fetchPortfolio.mockReset();
    exportPortfolioCsv.mockReset();
    triggerBlobDownload.mockReset();
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:alice");
    fetchPortfolio.mockResolvedValue(portfolioPayload());
    exportPortfolioCsv.mockResolvedValue({
      blob: new Blob(["symbol,assetType\r\nBTC,crypto\r\n"], { type: "text/csv" }),
      filename: "openportfo-portfolio-20260823.csv",
    });
  });

  afterEach(() => {
    cleanup();
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  });

  it("renders Export CSV next to Refresh", async () => {
    render(<PortfolioDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /export csv/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /^refresh$/i })).toBeInTheDocument();
  });

  it("downloads a blob without reload and shows success toast", async () => {
    const hrefBefore = window.location.href;
    render(<PortfolioDashboard />);
    await waitFor(() => {
      expect(fetchPortfolio).toHaveBeenCalled();
      expect(screen.getByRole("button", { name: /export csv/i })).not.toBeDisabled();
    });
    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    await waitFor(() => {
      expect(exportPortfolioCsv).toHaveBeenCalledTimes(1);
    });
    expect(exportPortfolioCsv).toHaveBeenCalledWith(
      expect.objectContaining({
        displayCurrency: "USD",
        currency: "USD",
        assetType: "all",
        token: "fake:alice",
      }),
    );
    await waitFor(() => {
      expect(triggerBlobDownload).toHaveBeenCalledTimes(1);
    });
    expect(triggerBlobDownload.mock.calls[0][1]).toBe("openportfo-portfolio-20260823.csv");
    expect(window.location.href).toBe(hrefBefore);
    expect(await screen.findByRole("status")).toHaveTextContent(/csv downloaded/i);
  });

  it("shows Exporting… while the request is in flight", async () => {
    let resolveExport: (value: { blob: Blob; filename: string }) => void = () => undefined;
    exportPortfolioCsv.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveExport = resolve;
        }),
    );

    render(<PortfolioDashboard />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /export csv/i })).not.toBeDisabled();
    });
    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    expect(await screen.findByRole("button", { name: /exporting/i })).toBeDisabled();

    resolveExport({
      blob: new Blob(["x"], { type: "text/csv" }),
      filename: "openportfo-portfolio-20260823.csv",
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /export csv/i })).not.toBeDisabled();
    });
  });

  it("shows an error toast when export fails", async () => {
    exportPortfolioCsv.mockRejectedValue(new PortfolioApiError(400, "format must be csv"));

    render(<PortfolioDashboard />);
    await waitFor(() => {
      expect(fetchPortfolio).toHaveBeenCalled();
      expect(screen.getByRole("button", { name: /export csv/i })).not.toBeDisabled();
    });
    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/format must be csv/i);
    expect(triggerBlobDownload).not.toHaveBeenCalled();
  });

  it("toasts when the portfolio is empty", async () => {
    fetchPortfolio.mockResolvedValue(portfolioPayload({ lines: [] }));

    render(<PortfolioDashboard />);
    await screen.findByText(/no holdings yet/i);
    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/no holdings to export/i);
    await waitFor(() => {
      expect(exportPortfolioCsv).toHaveBeenCalled();
    });
  });
});
