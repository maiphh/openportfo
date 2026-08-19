/** Display-only number formatting (BL-012). Does not change stored/API precision. */

export const DEFAULT_DISPLAY_FRACTION_DIGITS = 2;
export const DISPLAY_FRACTION_DIGITS_MIN = 0;
export const DISPLAY_FRACTION_DIGITS_MAX = 8;

const LOCALE = "en-US";

/** Integer 0–8; invalid / missing → 2. Never throws. */
export function parseDisplayFractionDigits(raw: unknown): number {
  if (raw == null || raw === "") return DEFAULT_DISPLAY_FRACTION_DIGITS;
  const n = typeof raw === "number" ? raw : Number(String(raw).trim());
  if (
    !Number.isInteger(n) ||
    n < DISPLAY_FRACTION_DIGITS_MIN ||
    n > DISPLAY_FRACTION_DIGITS_MAX
  ) {
    return DEFAULT_DISPLAY_FRACTION_DIGITS;
  }
  return n;
}

export function displayFractionDigits(): number {
  return parseDisplayFractionDigits(process.env.NEXT_PUBLIC_DISPLAY_FRACTION_DIGITS);
}

function resolveDigits(digits?: number): number {
  if (digits === undefined) return displayFractionDigits();
  return parseDisplayFractionDigits(digits);
}

export function formatPrice(value: number, digits?: number): string {
  const places = resolveDigits(digits);
  return Number(value).toLocaleString(LOCALE, {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  });
}

export function formatSigned(value: number, digits?: number): string {
  const places = resolveDigits(digits);
  if (!Number.isFinite(value) || value === 0) {
    return formatPrice(0, places);
  }
  const abs = formatPrice(Math.abs(value), places);
  return value > 0 ? `+${abs}` : `-${abs}`;
}

export function formatPct(value: number, digits?: number): string {
  return `${formatSigned(value, digits)}%`;
}

/** Integer counts stay whole; fractional qty uses the shared digit config. */
export function formatQty(value: number | string): string {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return value === "" ? "" : String(value);
  if (Number.isInteger(n)) {
    return n.toLocaleString(LOCALE, { maximumFractionDigits: 0 });
  }
  return formatPrice(n);
}
