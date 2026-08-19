"use client";

import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import FxRatesPanel from "@/components/currency/FxRatesPanel";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DISPLAY_CURRENCIES, getRate, rateKey, type DisplayCurrency } from "@/lib/currency";

function formatAsOfShort(asOf: string | null): string {
  if (!asOf) return "asOf —";
  const d = new Date(asOf);
  if (Number.isNaN(d.getTime())) return `asOf ${asOf}`;
  return `asOf ${d.toLocaleDateString()}`;
}

function relevantRateLabel(currency: DisplayCurrency, rates: Record<string, string>, asOf: string | null, status: string) {
  if (status === "missing" || Object.keys(rates).length === 0) {
    return `Rate unavailable · ${formatAsOfShort(asOf)}`;
  }
  if (currency === "VND") {
    const usdVnd = getRate(rates, "USD", "VND");
    if (usdVnd != null) return `1 USD = ${usdVnd.toLocaleString()} VND · ${formatAsOfShort(asOf)}`;
  }
  if (currency === "USD") {
    const vndUsd = getRate(rates, "VND", "USD");
    if (vndUsd != null) return `1 VND = ${vndUsd.toLocaleString(undefined, { maximumFractionDigits: 8 })} USD · ${formatAsOfShort(asOf)}`;
    const usdVnd = getRate(rates, "USD", "VND");
    if (usdVnd != null) return `1 USD = ${usdVnd.toLocaleString()} VND · ${formatAsOfShort(asOf)}`;
  }
  if (currency === "EUR") {
    const usdEur = getRate(rates, "USD", "EUR");
    if (usdEur != null) return `1 USD = ${usdEur.toLocaleString(undefined, { maximumFractionDigits: 6 })} EUR · ${formatAsOfShort(asOf)}`;
    const eurUsd = getRate(rates, "EUR", "USD");
    if (eurUsd != null) return `1 EUR = ${eurUsd.toLocaleString(undefined, { maximumFractionDigits: 6 })} USD · ${formatAsOfShort(asOf)}`;
  }
  const first = Object.keys(rates).sort()[0];
  if (first) return `${first} ${rates[first]} · ${formatAsOfShort(asOf)}`;
  return `Rate unavailable · ${formatAsOfShort(asOf)}`;
}

export default function CurrencySelect() {
  const { currency, setCurrency, rates, asOf, fxStatus } = useDisplayCurrency();
  const [panelOpen, setPanelOpen] = useState(false);

  const tip = useMemo(
    () => relevantRateLabel(currency, rates.rates, asOf, fxStatus),
    [asOf, currency, fxStatus, rates.rates],
  );

  const compactLabel = useMemo(() => {
    const pair = currency === "EUR" ? rateKey("USD", "EUR") : rateKey("USD", "VND");
    const direct = getRate(rates.rates, pair.slice(0, 3), pair.slice(4));
    if (direct != null) {
      const asOfBit = asOf ? ` · ${new Date(asOf).toLocaleDateString()}` : "";
      return `${pair} ${direct}${asOfBit}`;
    }
    if (fxStatus === "missing" || Object.keys(rates.rates).length === 0) return "FX n/a";
    return asOf ? `FX · ${new Date(asOf).toLocaleDateString()}` : "FX";
  }, [asOf, currency, fxStatus, rates.rates]);

  return (
    <>
      <div className="flex items-center gap-1.5">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              title={tip}
              aria-label={`Display currency ${currency}. ${tip}`}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-gray-400 hover:bg-gray-700 hover:text-gray-200"
            >
              {currency}
              <ChevronDown className="size-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {DISPLAY_CURRENCIES.map((code) => (
              <DropdownMenuItem key={code} onClick={() => setCurrency(code)}>
                {code}
                {code === currency ? " · active" : ""}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setPanelOpen(true)}>View FX rates…</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <span className="hidden max-w-[160px] truncate text-[10px] leading-tight text-gray-500 lg:inline" title={tip}>
          {compactLabel}
        </span>
      </div>
      <FxRatesPanel open={panelOpen} onClose={() => setPanelOpen(false)} />
    </>
  );
}
