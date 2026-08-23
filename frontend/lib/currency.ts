/** Session display currency (BL-003). Persisted in localStorage only. */

export const DISPLAY_CURRENCIES = ["VND", "USD", "EUR"] as const;
export type DisplayCurrency = (typeof DISPLAY_CURRENCIES)[number];

export const DEFAULT_DISPLAY_CURRENCY: DisplayCurrency = "VND";
export const DISPLAY_CURRENCY_STORAGE_KEY = "openportfo.displayCurrency";
export const DEFAULT_FX_BASE = "USD";

export type FxRatesPayload = {
  base: string | null;
  rates: Record<string, string>;
  asOf: string | null;
  provider: string | null;
  status: string;
  lastRefreshStatus?: string | null;
  lastRefreshError?: string | null;
  updatedBy?: string | null;
};

export function isDisplayCurrency(value: unknown): value is DisplayCurrency {
  return typeof value === "string" && (DISPLAY_CURRENCIES as readonly string[]).includes(value);
}

/** Parse a stored/user value; invalid → VND. */
export function parseDisplayCurrency(value: unknown): DisplayCurrency {
  if (typeof value !== "string") return DEFAULT_DISPLAY_CURRENCY;
  const normalized = value.trim().toUpperCase();
  return isDisplayCurrency(normalized) ? normalized : DEFAULT_DISPLAY_CURRENCY;
}

export function readStoredDisplayCurrency(
  storage?: Pick<Storage, "getItem"> | null,
): DisplayCurrency {
  let source = storage;
  if (source === undefined && typeof window !== "undefined") {
    try {
      source = window.localStorage;
    } catch {
      source = null;
    }
  }
  if (!source) return DEFAULT_DISPLAY_CURRENCY;
  try {
    return parseDisplayCurrency(source.getItem(DISPLAY_CURRENCY_STORAGE_KEY));
  } catch {
    return DEFAULT_DISPLAY_CURRENCY;
  }
}

export function writeStoredDisplayCurrency(
  currency: DisplayCurrency,
  storage?: Pick<Storage, "setItem"> | null,
): void {
  let target = storage;
  if (target === undefined && typeof window !== "undefined") {
    try {
      target = window.localStorage;
    } catch {
      target = null;
    }
  }
  if (!target) return;
  try {
    target.setItem(DISPLAY_CURRENCY_STORAGE_KEY, currency);
  } catch {
    // Quota / private mode — preference still lives in React state for the session.
  }
}

export function rateKey(src: string, dst: string): string {
  return `${src.toUpperCase()}_${dst.toUpperCase()}`;
}

function parseRateNumber(value: string | number | undefined): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/** Direct SRC_DST or inverse DST_SRC only (no triangulation). */
export function lookupDirectOrInverse(
  rates: Record<string, string | number> | null | undefined,
  src: string,
  dst: string,
): number | null {
  const srcU = src.trim().toUpperCase();
  const dstU = dst.trim().toUpperCase();
  if (!srcU || !dstU || !rates) return null;
  if (srcU === dstU) return 1;

  const direct = parseRateNumber(rates[rateKey(srcU, dstU)]);
  if (direct != null) return direct;

  const inverse = parseRateNumber(rates[rateKey(dstU, srcU)]);
  if (inverse != null && inverse !== 0) return 1 / inverse;
  return null;
}

/**
 * Resolve SRC→DST multiplier from flat stored rates.
 * Tries direct/inverse, then triangulation via `base` (admin store is USD-based).
 */
export function getRate(
  rates: Record<string, string | number> | null | undefined,
  src: string,
  dst: string,
  base: string = DEFAULT_FX_BASE,
): number | null {
  const srcU = src.trim().toUpperCase();
  const dstU = dst.trim().toUpperCase();
  if (!srcU || !dstU) return null;
  if (srcU === dstU) return 1;
  if (!rates) return null;

  const direct = lookupDirectOrInverse(rates, srcU, dstU);
  if (direct != null) return direct;

  const baseU = (base || DEFAULT_FX_BASE).trim().toUpperCase() || DEFAULT_FX_BASE;
  if (srcU === baseU || dstU === baseU) return null;

  const toBase = lookupDirectOrInverse(rates, srcU, baseU);
  const fromBase = lookupDirectOrInverse(rates, baseU, dstU);
  if (toBase == null || fromBase == null) return null;
  return toBase * fromBase;
}

export function convertAmount(
  amount: number,
  src: string,
  dst: string,
  rates: Record<string, string | number> | null | undefined,
  base: string = DEFAULT_FX_BASE,
): number | null {
  if (!Number.isFinite(amount)) return null;
  const rate = getRate(rates, src, dst, base);
  if (rate == null) return null;
  return amount * rate;
}

/** Markets board native quote currency (API has no displayCurrency today). */
export function nativeCurrencyForMarket(market: "stock" | "crypto"): "VND" | "USD" {
  return market === "crypto" ? "USD" : "VND";
}

export function emptyFxRates(status = "missing"): FxRatesPayload {
  return {
    base: null,
    rates: {},
    asOf: null,
    provider: null,
    status,
  };
}

/** Holding avg-cost field label in session currency (BL-001 consumes). */
export function holdingCostLabel(currency: DisplayCurrency): string {
  return `Avg cost (${currency})`;
}
