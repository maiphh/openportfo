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
import {
  DEFAULT_FX_BASE,
  DISPLAY_CURRENCIES,
  getRate,
  rateKey,
  type DisplayCurrency,
} from "@/lib/currency";
import { formatPrice } from "@/lib/utils";

function formatAsOfShort(asOf: string | null): string {
  if (!asOf) return "asOf —";
  const d = new Date(asOf);
  if (Number.isNaN(d.getTime())) return `asOf ${asOf}`;
  return `asOf ${d.toLocaleDateString()}`;
}

function formatAsOfCompact(asOf: string | null): string | null {
  if (!asOf) return null;
  const d = new Date(asOf);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString();
}

function relevantRateLabel(
  currency: DisplayCurrency,
  rates: Record<string, string>,
  asOf: string | null,
  status: string,
  base: string,
) {
  if (status === "missing" || Object.keys(rates).length === 0) {
    return `Rate unavailable · ${formatAsOfShort(asOf)}`;
  }
  if (currency === "VND") {
    const usdVnd = getRate(rates, "USD", "VND", base);
    if (usdVnd != null) return `1 USD = ${formatPrice(usdVnd)} VND · ${formatAsOfShort(asOf)}`;
  }
  if (currency === "USD") {
    const vndUsd = getRate(rates, "VND", "USD", base);
    if (vndUsd != null) {
      return `1 VND = ${formatPrice(vndUsd)} USD · ${formatAsOfShort(asOf)}`;
    }
    const usdVnd = getRate(rates, "USD", "VND", base);
    if (usdVnd != null) return `1 USD = ${formatPrice(usdVnd)} VND · ${formatAsOfShort(asOf)}`;
  }
  if (currency === "EUR") {
    const usdEur = getRate(rates, "USD", "EUR", base);
    if (usdEur != null) {
      return `1 USD = ${formatPrice(usdEur)} EUR · ${formatAsOfShort(asOf)}`;
    }
    const eurUsd = getRate(rates, "EUR", "USD", base);
    if (eurUsd != null) {
      return `1 EUR = ${formatPrice(eurUsd)} USD · ${formatAsOfShort(asOf)}`;
    }
  }
  const first = Object.keys(rates).sort()[0];
  if (first) {
    const n = Number(rates[first]);
    const shown = Number.isFinite(n) ? formatPrice(n) : rates[first];
    return `${first} ${shown} · ${formatAsOfShort(asOf)}`;
  }
  return `Rate unavailable · ${formatAsOfShort(asOf)}`;
}

export default function CurrencySelect() {
  const { currency, setCurrency, rates, asOf, fxStatus } = useDisplayCurrency();
  const [panelOpen, setPanelOpen] = useState(false);
  const fxBase = rates.base?.trim() || DEFAULT_FX_BASE;

  const tip = useMemo(
    () => relevantRateLabel(currency, rates.rates, asOf, fxStatus, fxBase),
    [asOf, currency, fxBase, fxStatus, rates.rates],
  );

  const compactLabel = useMemo(() => {
    const quoteTo = currency === "EUR" ? "EUR" : "VND";
    const pair = rateKey("USD", quoteTo);
    const direct = getRate(rates.rates, "USD", quoteTo, fxBase);
    const asOfBit = formatAsOfCompact(asOf);
    if (direct != null) {
      return asOfBit ? `${pair} ${formatPrice(direct)} · ${asOfBit}` : `${pair} ${formatPrice(direct)}`;
    }
    if (fxStatus === "missing" || Object.keys(rates.rates).length === 0) return "FX n/a";
    return asOfBit ? `FX · ${asOfBit}` : "FX";
  }, [asOf, currency, fxBase, fxStatus, rates.rates]);

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
