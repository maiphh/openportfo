"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  convertAmount,
  DEFAULT_DISPLAY_CURRENCY,
  emptyFxRates,
  getRate,
  parseDisplayCurrency,
  readStoredDisplayCurrency,
  writeStoredDisplayCurrency,
  type DisplayCurrency,
  type FxRatesPayload,
} from "@/lib/currency";
import { fetchFxRates, readAuthToken } from "@/lib/fx";

export type CurrencyContextValue = {
  currency: DisplayCurrency;
  setCurrency: (next: DisplayCurrency) => void;
  rates: FxRatesPayload;
  ratesLoading: boolean;
  ratesAuthRequired: boolean;
  refreshRates: () => Promise<void>;
  /** Multiplier native→display, or null when unavailable. */
  rateToDisplay: (nativeCurrency: string) => number | null;
  convertToDisplay: (amount: number, nativeCurrency: string) => number | null;
  asOf: string | null;
  fxStatus: string;
};

const CurrencyContext = createContext<CurrencyContextValue | null>(null);

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<DisplayCurrency>(DEFAULT_DISPLAY_CURRENCY);
  const [hydrated, setHydrated] = useState(false);
  const [rates, setRates] = useState<FxRatesPayload>(() => emptyFxRates());
  const [ratesLoading, setRatesLoading] = useState(false);
  const [ratesAuthRequired, setRatesAuthRequired] = useState(false);

  useEffect(() => {
    setCurrencyState(readStoredDisplayCurrency());
    setHydrated(true);
  }, []);

  const setCurrency = useCallback((next: DisplayCurrency) => {
    const parsed = parseDisplayCurrency(next);
    setCurrencyState(parsed);
    writeStoredDisplayCurrency(parsed);
  }, []);

  const refreshRates = useCallback(async () => {
    const controller = new AbortController();
    setRatesLoading(true);
    try {
      const result = await fetchFxRates({
        token: readAuthToken(),
        signal: controller.signal,
      });
      setRates(result.data);
      setRatesAuthRequired(result.authRequired);
    } catch {
      setRates(emptyFxRates("missing"));
      setRatesAuthRequired(false);
    } finally {
      setRatesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    void refreshRates();
  }, [hydrated, refreshRates]);

  const rateToDisplay = useCallback(
    (nativeCurrency: string) => getRate(rates.rates, nativeCurrency, currency),
    [currency, rates.rates],
  );

  const convertToDisplay = useCallback(
    (amount: number, nativeCurrency: string) =>
      convertAmount(amount, nativeCurrency, currency, rates.rates),
    [currency, rates.rates],
  );

  const value = useMemo<CurrencyContextValue>(
    () => ({
      currency,
      setCurrency,
      rates,
      ratesLoading,
      ratesAuthRequired,
      refreshRates,
      rateToDisplay,
      convertToDisplay,
      asOf: rates.asOf,
      fxStatus: rates.status || "missing",
    }),
    [
      convertToDisplay,
      currency,
      rateToDisplay,
      rates,
      ratesAuthRequired,
      ratesLoading,
      refreshRates,
      setCurrency,
    ],
  );

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useDisplayCurrency(): CurrencyContextValue {
  const ctx = useContext(CurrencyContext);
  if (!ctx) {
    throw new Error("useDisplayCurrency must be used within CurrencyProvider");
  }
  return ctx;
}

/** Optional subscribe — returns null outside provider (for shared libs). */
export function useDisplayCurrencyOptional(): CurrencyContextValue | null {
  return useContext(CurrencyContext);
}
