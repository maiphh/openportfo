import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PortfolioValueChart from "@/components/portfolio/PortfolioValueChart";
import type { PerformanceResponse } from "@/lib/portfolio-charts";

const fetchPortfolioPerformance = vi.fn();

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
    convertToDisplay: (amount: number) => amount,
    asOf: null,
    fxStatus: "missing",
  }),
}));

vi.mock("@/lib/portfolio-charts", async () => {
  const actual = await vi.importActual<typeof import("@/lib/portfolio-charts")>("@/lib/portfolio-charts");
  return {
    ...actual,
    fetchPortfolioPerformance: (...args: unknown[]) => fetchPortfolioPerformance(...args),
  };
});

function payload(): PerformanceResponse {
  return {
    range: "1w",
    from: "2026-09-01",
    to: "2026-09-08",
    startValue: "100",
    endValue: "120",
    change: "20",
    changePercent: "0.2",
    currency: "USD",
    points: [
      { date: "2026-09-01", marketValue: "100", currency: "USD" },
      { date: "2026-09-02", marketValue: "110", currency: "USD" },
      { date: "2026-09-08", marketValue: "120", currency: "USD" },
    ],
  };
}

describe("PortfolioValueChart hover + overflow (BL-033)", () => {
  beforeEach(() => {
    fetchPortfolioPerformance.mockReset();
    fetchPortfolioPerformance.mockResolvedValue(payload());
  });

  afterEach(() => cleanup());

  it("shows a hover tooltip with date + value", async () => {
    const rectSpy = vi.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue({
      left: 0,
      top: 0,
      right: 640,
      bottom: 200,
      width: 640,
      height: 200,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    } as DOMRect);
    try {
      render(<PortfolioValueChart token="fake:alice" />);

      const chart = await screen.findByRole("img", { name: /Portfolio value/i });
      // Middle of a 3-point series maps to the second point (2026-09-02 / 110).
      fireEvent.mouseMove(chart, { clientX: 320 });

      expect(await screen.findByRole("status")).toHaveTextContent("2026-09-02");
      expect(screen.getByRole("status")).toHaveTextContent("110");
    } finally {
      rectSpy.mockRestore();
    }
  });

  it("anchors axis labels inside the viewBox so edge text does not clip", async () => {
    const { container } = render(<PortfolioValueChart token="fake:alice" />);
    await screen.findByRole("img", { name: /Portfolio value/i });

    const texts = Array.from(container.querySelectorAll("svg text"));
    expect(texts.length).toBeGreaterThanOrEqual(2);
    expect(texts[0].getAttribute("text-anchor")).toBe("start");
    expect(texts[texts.length - 1].getAttribute("text-anchor")).toBe("end");
  });
});
