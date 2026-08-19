"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  convertAmount,
  DEFAULT_DISPLAY_CURRENCY,
  DEFAULT_FX_BASE,
  emptyFxRates,
  getRate,
  parseDisplayCurrency,
  readStoredDisplayCurrency,
  writeStoredDisplayCurrency,
  type DisplayCurrency,
  type FxRatesPayload,
} from "@/lib/currency";
import { AUTH_TOKEN_STORAGE_KEY, fetchFxRates, readAuthToken } from "@/lib/fx";

export type CurrencyContextValue = {
  currency: DisplayCurrency;
  setCurrency: (next: DisplayCurrency) => void;
  rates: FxRatesPayload;
  ratesLoading: boolean;
  ratesAuthRequired: boolean;
  ratesError: string | null;
  refreshRates: () => Promise<void>;
  /** Replace stored rates in session (admin refresh success). */
  replaceRates: (data: FxRatesPayload) => void;
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
  const [ratesError, setRatesError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const hasLoadedRatesRef = useRef(false);
  const lastTokenRef = useRef<string | null>(null);

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
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setRatesLoading(true);
    setRatesError(null);

    try {
      const token = readAuthToken();
      lastTokenRef.current = token;
      const result = await fetchFxRates({
        token,
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;

      setRatesAuthRequired(result.authRequired);
      if (result.ok) {
        setRates(result.data);
        hasLoadedRatesRef.current = Object.keys(result.data.rates).length > 0 || result.data.status !== "missing";
        setRatesError(null);
      } else if (!hasLoadedRatesRef.current) {
        setRates(result.data);
        setRatesError(result.authRequired ? "auth_required" : `http_${result.status}`);
      } else {
        // Keep last-good rates; surface auth/error separately.
        setRatesError(result.authRequired ? "auth_required" : `http_${result.status}`);
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      if (!hasLoadedRatesRef.current) {
        setRates(emptyFxRates("missing"));
      }
      setRatesError(err instanceof Error ? err.message : "fetch_failed");
    } finally {
      if (!controller.signal.aborted) {
        setRatesLoading(false);
      }
    }
  }, []);

  const replaceRates = useCallback((data: FxRatesPayload) => {
    setRates(data);
    hasLoadedRatesRef.current = Object.keys(data.rates).length > 0 || data.status !== "missing";
    setRatesError(null);
    setRatesAuthRequired(false);
  }, []);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    void refreshRates();
  }, [hydrated, refreshRates]);

  // Re-fetch when auth token appears (other tab via storage; same tab via focus/visibility).
  useEffect(() => {
    if (!hydrated) return;

    const maybeRefreshForAuth = () => {
      const token = readAuthToken();
      if (token !== lastTokenRef.current) {
        void refreshRates();
      }
    };

    const onStorage = (event: StorageEvent) => {
      if (event.key === AUTH_TOKEN_STORAGE_KEY) {
        void refreshRates();
      }
    };

    const onVisibility = () => {
      if (document.visibilityState === "visible") maybeRefreshForAuth();
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", maybeRefreshForAuth);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", maybeRefreshForAuth);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [hydrated, refreshRates]);

  const fxBase = rates.base?.trim() || DEFAULT_FX_BASE;

  const rateToDisplay = useCallback(
    (nativeCurrency: string) => getRate(rates.rates, nativeCurrency, currency, fxBase),
    [currency, fxBase, rates.rates],
  );

  const convertToDisplay = useCallback(
    (amount: number, nativeCurrency: string) =>
      convertAmount(amount, nativeCurrency, currency, rates.rates, fxBase),
    [currency, fxBase, rates.rates],
  );

  const value = useMemo<CurrencyContextValue>(
    () => ({
      currency,
      setCurrency,
      rates,
      ratesLoading,
      ratesAuthRequired,
      ratesError,
      refreshRates,
      replaceRates,
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
      ratesError,
      ratesLoading,
      refreshRates,
      replaceRates,
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
