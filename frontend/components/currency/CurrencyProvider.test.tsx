import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CurrencyProvider, useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { DISPLAY_CURRENCY_STORAGE_KEY, type DisplayCurrency } from "@/lib/currency";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import { fetchFxRates } from "@/lib/fx";

vi.mock("@/lib/fx", async () => {
  const actual = await vi.importActual<typeof import("@/lib/fx")>("@/lib/fx");
  return {
    ...actual,
    fetchFxRates: vi.fn(),
  };
});

const fetchFxRatesMock = vi.mocked(fetchFxRates);

const okPayload = {
  data: {
    base: "USD",
    rates: { USD_VND: "25000", USD_EUR: "0.92" },
    asOf: "2026-08-01T00:00:00Z",
    provider: "test",
    status: "fresh",
  },
  ok: true as const,
  status: 200,
  authRequired: false,
};

let latestSetCurrency: ((next: DisplayCurrency) => void) | null = null;
let latestRefresh: (() => Promise<void>) | null = null;

function Probe() {
  const { currency, setCurrency, rateToDisplay, fxStatus, refreshRates, ratesError } = useDisplayCurrency();
  latestSetCurrency = setCurrency;
  latestRefresh = refreshRates;
  return (
    <div>
      <span data-testid="currency">{currency}</span>
      <span data-testid="fx-status">{fxStatus}</span>
      <span data-testid="usd-rate">{String(rateToDisplay("USD"))}</span>
      <span data-testid="vnd-eur">{String(rateToDisplay("VND"))}</span>
      <span data-testid="rates-error">{ratesError ?? ""}</span>
    </div>
  );
}

describe("CurrencyProvider", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
    latestSetCurrency = null;
    latestRefresh = null;
    fetchFxRatesMock.mockReset();
    fetchFxRatesMock.mockResolvedValue(okPayload);
  });

  afterEach(() => {
    cleanup();
    window.sessionStorage.clear();
    window.localStorage.clear();
    latestSetCurrency = null;
    latestRefresh = null;
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

  it("keeps last-good rates when a later refresh fails", async () => {
    render(
      <CurrencyProvider>
        <Probe />
      </CurrencyProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("fx-status")).toHaveTextContent("fresh");
      expect(screen.getByTestId("usd-rate")).toHaveTextContent("25000");
    });

    fetchFxRatesMock.mockResolvedValueOnce({
      data: { base: null, rates: {}, asOf: null, provider: null, status: "missing" },
      ok: false,
      status: 503,
      authRequired: false,
    });

    await act(async () => {
      await latestRefresh!();
    });

    expect(screen.getByTestId("fx-status")).toHaveTextContent("fresh");
    expect(screen.getByTestId("usd-rate")).toHaveTextContent("25000");
    expect(screen.getByTestId("rates-error")).toHaveTextContent("http_503");
  });

  it("triangulates VND→EUR via USD when display is EUR", async () => {
    window.localStorage.setItem(DISPLAY_CURRENCY_STORAGE_KEY, "EUR");
    render(
      <CurrencyProvider>
        <Probe />
      </CurrencyProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("currency")).toHaveTextContent("EUR");
      expect(Number(screen.getByTestId("vnd-eur").textContent)).toBeCloseTo((1 / 25000) * 0.92);
    });
  });

  it("refetches when access token changes on focus", async () => {
    render(
      <CurrencyProvider>
        <Probe />
      </CurrencyProvider>,
    );

    await waitFor(() => {
      expect(fetchFxRatesMock).toHaveBeenCalled();
    });
    const callsAfterMount = fetchFxRatesMock.mock.calls.length;

    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:u1");
    await act(async () => {
      window.dispatchEvent(new Event("focus"));
    });

    await waitFor(() => {
      expect(fetchFxRatesMock.mock.calls.length).toBeGreaterThan(callsAfterMount);
    });
  });
});
