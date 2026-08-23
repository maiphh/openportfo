"use client";

import { useState } from "react";
import { useT } from "@/components/LanguageProvider";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { refreshFxRates } from "@/lib/fx";
import type { AuthProfileController } from "@/lib/use-auth-profile";

export default function FxTab({ auth }: { auth: AuthProfileController }) {
  const t = useT();
  const { rates, ratesLoading, ratesError, refreshRates, replaceRates } = useDisplayCurrency();
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const isAdmin = auth.profile?.role === "admin";
  const rows = Object.entries(rates.rates);
  const statusKey = rates.status === "fresh"
    ? "settings.fxStatusFresh"
    : rates.status === "stale"
      ? "settings.fxStatusStale"
      : "settings.fxStatusMissing";
  const refresh = async () => {
    if (!auth.token || refreshing) return;
    setRefreshing(true); setRefreshError(null);
    try {
      const result = await refreshFxRates({ token: auth.token });
      if (result.ok) { replaceRates(result.data); }
      else {
        if (Object.keys(result.data.rates).length) replaceRates(result.data);
        setRefreshError(t("settings.fxRefreshError"));
        if (result.authRequired) void auth.reloadProfile();
      }
    } catch {
      setRefreshError(t("settings.fxRefreshError"));
    } finally {
      setRefreshing(false);
    }
  };
  return (
    <section className="space-y-4" aria-busy={ratesLoading || refreshing}>
      <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm text-gray-300">{rates.base ? `${t("settings.fxBase")}: ${rates.base}` : t("settings.fxUnavailable")}</p><p className="text-xs text-gray-500">{rates.asOf || t("settings.fxNoTimestamp")} · {rates.provider || "—"}</p><p role="status" aria-label={t("settings.fxStatusLabel")} className="mt-1 text-xs text-gray-400">{t(statusKey)}</p></div>{isAdmin ? <button type="button" onClick={() => void refresh()} disabled={refreshing} className="rounded-md border border-gray-600 px-3 py-2 text-sm text-gray-200 disabled:opacity-50">{refreshing ? t("settings.refreshing") : t("settings.refreshRates")}</button> : null}</div>
      {ratesError || refreshError ? <p role="alert" className="text-sm text-red-300">{refreshError || ratesError}</p> : null}
      {rows.length ? <div className="overflow-x-auto rounded-lg border border-gray-700"><table className="w-full text-left text-sm"><thead className="bg-gray-800 text-xs uppercase text-gray-500"><tr><th className="px-3 py-2">{t("settings.fxPair")}</th><th className="px-3 py-2">{t("settings.fxRate")}</th></tr></thead><tbody>{rows.map(([pair, rate]) => <tr key={pair} className="border-t border-gray-700"><td className="px-3 py-2 text-gray-300">{pair}</td><td className="px-3 py-2 text-gray-100">{rate}</td></tr>)}</tbody></table></div> : <p className="rounded-lg border border-dashed border-gray-700 p-6 text-sm text-gray-500">{t("settings.fxEmpty")}</p>}
      <button type="button" onClick={() => void refreshRates()} className="text-sm text-teal-300 underline">{t("settings.retryRates")}</button>
    </section>
  );
}
