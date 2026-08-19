import { afterEach, describe, expect, it } from "vitest";
import {
  convertAmount,
  DEFAULT_DISPLAY_CURRENCY,
  DISPLAY_CURRENCY_STORAGE_KEY,
  getRate,
  holdingCostLabel,
  nativeCurrencyForMarket,
  parseDisplayCurrency,
  readStoredDisplayCurrency,
  writeStoredDisplayCurrency,
} from "@/lib/currency";

describe("parseDisplayCurrency", () => {
  it("defaults invalid and empty values to VND", () => {
    expect(parseDisplayCurrency(null)).toBe("VND");
    expect(parseDisplayCurrency(undefined)).toBe("VND");
    expect(parseDisplayCurrency("")).toBe("VND");
    expect(parseDisplayCurrency("gbp")).toBe("VND");
    expect(parseDisplayCurrency("JPY")).toBe("VND");
    expect(DEFAULT_DISPLAY_CURRENCY).toBe("VND");
  });

  it("accepts VND, USD, EUR case-insensitively", () => {
    expect(parseDisplayCurrency("vnd")).toBe("VND");
    expect(parseDisplayCurrency(" Usd ")).toBe("USD");
    expect(parseDisplayCurrency("EUR")).toBe("EUR");
  });
});

describe("localStorage display currency", () => {
  afterEach(() => {
    window.localStorage.removeItem(DISPLAY_CURRENCY_STORAGE_KEY);
  });

  it("reads default when missing", () => {
    expect(readStoredDisplayCurrency(window.localStorage)).toBe("VND");
  });

  it("persists and restores a valid selection", () => {
    writeStoredDisplayCurrency("EUR", window.localStorage);
    expect(window.localStorage.getItem(DISPLAY_CURRENCY_STORAGE_KEY)).toBe("EUR");
    expect(readStoredDisplayCurrency(window.localStorage)).toBe("EUR");
  });

  it("falls back to VND for invalid stored values", () => {
    window.localStorage.setItem(DISPLAY_CURRENCY_STORAGE_KEY, "BTC");
    expect(readStoredDisplayCurrency(window.localStorage)).toBe("VND");
  });
});

describe("getRate / convertAmount", () => {
  const rates = { USD_VND: "25000", USD_EUR: "0.92" };

  it("returns 1 for same currency", () => {
    expect(getRate(rates, "VND", "VND")).toBe(1);
  });

  it("uses direct and inverse pairs", () => {
    expect(getRate(rates, "USD", "VND")).toBe(25000);
    expect(getRate(rates, "VND", "USD")).toBeCloseTo(1 / 25000);
    expect(getRate(rates, "USD", "EUR")).toBe(0.92);
  });

  it("triangulates via USD base when cross pair is absent", () => {
    expect(getRate(rates, "VND", "EUR")).toBeCloseTo((1 / 25000) * 0.92);
    expect(getRate(rates, "EUR", "VND")).toBeCloseTo((1 / 0.92) * 25000);
    expect(convertAmount(25000, "VND", "EUR", rates)).toBeCloseTo(0.92);
  });

  it("returns null when a triangulation leg is missing", () => {
    expect(getRate({ USD_VND: "25000" }, "VND", "EUR")).toBeNull();
    expect(convertAmount(100, "VND", "EUR", { USD_VND: "25000" })).toBeNull();
  });

  it("converts amounts when rate exists", () => {
    expect(convertAmount(2, "USD", "VND", rates)).toBe(50000);
  });
});

describe("market native + holding label helpers", () => {
  it("maps market boards to native quote currencies", () => {
    expect(nativeCurrencyForMarket("stock")).toBe("VND");
    expect(nativeCurrencyForMarket("crypto")).toBe("USD");
  });

  it("labels holding cost in session currency", () => {
    expect(holdingCostLabel("USD")).toBe("Avg cost (USD)");
  });
});
