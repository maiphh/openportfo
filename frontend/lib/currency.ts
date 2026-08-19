/** Session display currency (BL-003). Persisted in localStorage only. */

export const DISPLAY_CURRENCIES = ["VND", "USD", "EUR"] as const;
export type DisplayCurrency = (typeof DISPLAY_CURRENCIES)[number];

export const DEFAULT_DISPLAY_CURRENCY: DisplayCurrency = "VND";
export const DISPLAY_CURRENCY_STORAGE_KEY = "artryx.displayCurrency";

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
  storage: Pick<Storage, "getItem"> | null | undefined = typeof window !== "undefined" ? window.localStorage : null,
): DisplayCurrency {
  if (!storage) return DEFAULT_DISPLAY_CURRENCY;
  try {
    return parseDisplayCurrency(storage.getItem(DISPLAY_CURRENCY_STORAGE_KEY));
  } catch {
    return DEFAULT_DISPLAY_CURRENCY;
  }
}

export function writeStoredDisplayCurrency(
  currency: DisplayCurrency,
  storage: Pick<Storage, "setItem"> | null | undefined = typeof window !== "undefined" ? window.localStorage : null,
): void {
  if (!storage) return;
  try {
    storage.setItem(DISPLAY_CURRENCY_STORAGE_KEY, currency);
  } catch {
    // Quota / private mode — preference still lives in React state for the session.
  }
}

export function rateKey(src: string, dst: string): string {
  return `${src.toUpperCase()}_${dst.toUpperCase()}`;
}

/** Resolve SRC→DST multiplier from flat stored rates (direct or inverse). */
export function getRate(
  rates: Record<string, string | number> | null | undefined,
  src: string,
  dst: string,
): number | null {
  const srcU = src.trim().toUpperCase();
  const dstU = dst.trim().toUpperCase();
  if (!srcU || !dstU) return null;
  if (srcU === dstU) return 1;
  if (!rates) return null;

  const direct = rates[rateKey(srcU, dstU)];
  if (direct != null && direct !== "") {
    const n = Number(direct);
    return Number.isFinite(n) ? n : null;
  }

  const inverse = rates[rateKey(dstU, srcU)];
  if (inverse != null && inverse !== "") {
    const n = Number(inverse);
    if (Number.isFinite(n) && n !== 0) return 1 / n;
  }
  return null;
}

export function convertAmount(
  amount: number,
  src: string,
  dst: string,
  rates: Record<string, string | number> | null | undefined,
): number | null {
  if (!Number.isFinite(amount)) return null;
  const rate = getRate(rates, src, dst);
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
