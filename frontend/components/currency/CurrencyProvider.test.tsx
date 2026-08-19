import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CurrencyProvider, useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { DISPLAY_CURRENCY_STORAGE_KEY, type DisplayCurrency } from "@/lib/currency";

vi.mock("@/lib/fx", async () => {
  const actual = await vi.importActual<typeof import("@/lib/fx")>("@/lib/fx");
  return {
    ...actual,
    fetchFxRates: vi.fn(async () => ({
      data: {
        base: "USD",
        rates: { USD_VND: "25000" },
        asOf: "2026-08-01T00:00:00Z",
        provider: "test",
        status: "fresh",
      },
      ok: true,
      status: 200,
      authRequired: false,
    })),
  };
});

let latestSetCurrency: ((next: DisplayCurrency) => void) | null = null;

function Probe() {
  const { currency, setCurrency, rateToDisplay, fxStatus } = useDisplayCurrency();
  latestSetCurrency = setCurrency;
  return (
    <div>
      <span data-testid="currency">{currency}</span>
      <span data-testid="fx-status">{fxStatus}</span>
      <span data-testid="usd-rate">{String(rateToDisplay("USD"))}</span>
    </div>
  );
}

describe("CurrencyProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    latestSetCurrency = null;
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    latestSetCurrency = null;
  });

  it("hydrates from localStorage and persists changes", async () => {
    window.localStorage.setItem(DISPLAY_CURRENCY_STORAGE_KEY, "USD");
    render(
      <CurrencyProvider>
        <Probe />
      </CurrencyProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("currency")).toHaveTextContent("USD");
    });

    expect(latestSetCurrency).not.toBeNull();
    await act(async () => {
      latestSetCurrency!("EUR");
    });
    expect(screen.getByTestId("currency")).toHaveTextContent("EUR");
    expect(window.localStorage.getItem(DISPLAY_CURRENCY_STORAGE_KEY)).toBe("EUR");
  });

  it("exposes rate helpers from loaded FX payload", async () => {
    render(
      <CurrencyProvider>
        <Probe />
      </CurrencyProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("fx-status")).toHaveTextContent("fresh");
      expect(screen.getByTestId("usd-rate")).toHaveTextContent("25000");
    });
  });
});
