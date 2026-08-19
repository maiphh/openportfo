import { afterEach, describe, expect, it, vi } from "vitest";
import {
  DEFAULT_DISPLAY_FRACTION_DIGITS,
  displayFractionDigits,
  formatPct,
  formatPrice,
  formatQty,
  formatSigned,
  parseDisplayFractionDigits,
} from "@/lib/number-format";
import { formatPct as formatPctFromUtils, formatPrice as formatPriceFromUtils } from "@/lib/utils";

describe("parseDisplayFractionDigits", () => {
  it("defaults missing and invalid values to 2", () => {
    expect(DEFAULT_DISPLAY_FRACTION_DIGITS).toBe(2);
    expect(parseDisplayFractionDigits(undefined)).toBe(2);
    expect(parseDisplayFractionDigits(null)).toBe(2);
    expect(parseDisplayFractionDigits("")).toBe(2);
    expect(parseDisplayFractionDigits("nope")).toBe(2);
    expect(parseDisplayFractionDigits("2.5")).toBe(2);
    expect(parseDisplayFractionDigits(-1)).toBe(2);
    expect(parseDisplayFractionDigits(9)).toBe(2);
  });

  it("accepts integers 0–8", () => {
    expect(parseDisplayFractionDigits(0)).toBe(0);
    expect(parseDisplayFractionDigits(" 4 ")).toBe(4);
    expect(parseDisplayFractionDigits(8)).toBe(8);
  });
});

describe("display formatters", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("defaults to 2 fraction digits with en-US grouping", () => {
    expect(displayFractionDigits()).toBe(2);
    expect(formatPrice(1234.5)).toBe("1,234.50");
    expect(formatPrice(0.000012)).toBe("0.00");
    expect(formatSigned(-12.3)).toBe("-12.30");
    expect(formatSigned(12.3)).toBe("+12.30");
    expect(formatSigned(0)).toBe("0.00");
    expect(formatPct(1.234)).toBe("+1.23%");
    expect(formatPct(-1.2)).toBe("-1.20%");
  });

  it("honors NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS=0 (rounded)", () => {
    vi.stubEnv("NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS", "0");
    expect(displayFractionDigits()).toBe(0);
    expect(formatPrice(1234.5)).toBe("1,235");
    expect(formatSigned(-12.3)).toBe("-12");
    expect(formatPct(1.234)).toBe("+1%");
  });

  it("honors NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS override", () => {
    vi.stubEnv("NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS", "4");
    expect(formatPrice(1.2)).toBe("1.2000");
    expect(formatSigned(-12.3)).toBe("-12.3000");
    expect(formatPct(1.234)).toBe("+1.2340%");
  });

  it("falls back to 2 when the env value is invalid", () => {
    vi.stubEnv("NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS", "nope");
    expect(displayFractionDigits()).toBe(2);
    expect(formatPrice(1)).toBe("1.00");
    expect(formatPct(1.234)).toBe("+1.23%");
  });

  it("keeps a trailing % on formatPct", () => {
    expect(formatPct(0)).toBe("0.00%");
    expect(formatPct(1.234).endsWith("%")).toBe(true);
  });

  it("does not throw on non-finite values", () => {
    expect(() => formatPrice(Number.NaN)).not.toThrow();
    expect(() => formatSigned(Number.POSITIVE_INFINITY)).not.toThrow();
    expect(formatSigned(Number.NaN)).toBe("0.00");
  });

  it("formats integer qty without forced decimals and fractional qty with the digit config", () => {
    expect(formatQty(10)).toBe("10");
    expect(formatQty("10.0")).toBe("10");
    expect(formatQty("1.5")).toBe("1.50");
    expect(formatQty("not-a-qty")).toBe("not-a-qty");
  });

  it("re-exports formatPrice / formatSigned / formatPct from utils", () => {
    expect(formatPriceFromUtils(1234.5)).toBe("1,234.50");
    expect(formatPctFromUtils(1.234)).toBe("+1.23%");
  });
});
