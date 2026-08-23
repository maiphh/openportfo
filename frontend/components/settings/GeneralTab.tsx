"use client";

import { useEffect, useMemo, useState } from "react";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { useT } from "@/components/LanguageProvider";
import type { AuthProfileController } from "@/lib/use-auth-profile";
import { updateUserSettings } from "@/lib/settings-api";
import { normalizeKeyword, validKeywordList } from "@/lib/user-settings-schema";

export default function GeneralTab({ auth }: { auth: AuthProfileController }) {
  const t = useT();
  const { currency, setCurrency } = useDisplayCurrency();
  const profile = auth.profile;
  const [keywords, setKeywords] = useState<string[]>(profile?.newsKeywords ?? []);
  const [keywordInput, setKeywordInput] = useState("");
  const [emailOptIn, setEmailOptIn] = useState(profile?.emailOptIn ?? false);
  const [preferredCurrency, setPreferredCurrency] = useState(profile?.preferredCurrency ?? currency);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setKeywords(profile?.newsKeywords ?? []);
    setEmailOptIn(profile?.emailOptIn ?? false);
    setPreferredCurrency(profile?.preferredCurrency ?? currency);
  }, [profile?.emailOptIn, profile?.newsKeywords, profile?.preferredCurrency, currency]);

  const initial = useMemo(
    () => ({
      keywords: profile?.newsKeywords ?? [],
      emailOptIn: profile?.emailOptIn ?? false,
      preferredCurrency: profile?.preferredCurrency ?? currency,
    }),
    [currency, profile?.emailOptIn, profile?.newsKeywords, profile?.preferredCurrency],
  );
  const dirty = JSON.stringify({ keywords, emailOptIn, preferredCurrency: preferredCurrency || null }) !== JSON.stringify(initial);
  const valid = validKeywordList(keywords);

  const addKeyword = () => {
    const value = normalizeKeyword(keywordInput);
    if (!value || keywords.some((item) => item.toLocaleLowerCase() === value.toLocaleLowerCase()) || keywords.length >= 20) return;
    setKeywords((current) => [...current, value]);
    setKeywordInput("");
  };

  const save = async () => {
    if (!auth.token || !dirty || !valid || busy) return;
    setBusy(true); setError(null); setSuccess(false);
    try {
      const updated = await updateUserSettings(auth.token, {
        newsKeywords: keywords,
        emailOptIn,
        preferredCurrency: preferredCurrency === "USD" || preferredCurrency === "VND" || preferredCurrency === "EUR" ? preferredCurrency : null,
      });
      auth.replaceProfile(updated);
      if (updated.preferredCurrency === "USD" || updated.preferredCurrency === "VND" || updated.preferredCurrency === "EUR") setCurrency(updated.preferredCurrency);
      setSuccess(true);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : t("settings.saveError"));
    } finally { setBusy(false); }
  };

  return (
    <form className="space-y-5" onSubmit={(event) => { event.preventDefault(); void save(); }} aria-busy={busy}>
      <div>
        <label htmlFor="settings-currency" className="mb-1 block text-sm font-medium text-gray-200">{t("settings.currency")}</label>
        <select id="settings-currency" value={preferredCurrency || "USD"} onChange={(event) => setPreferredCurrency(event.target.value)} className="w-full rounded-md border border-gray-600 bg-gray-900 px-3 py-2 text-gray-100">
          <option value="USD">USD</option><option value="VND">VND</option><option value="EUR">EUR</option>
        </select>
      </div>
      <label className="flex items-center gap-2 text-sm text-gray-200"><input type="checkbox" checked={emailOptIn} onChange={(event) => setEmailOptIn(event.target.checked)} /> {t("settings.emailOptIn")}</label>
      <div>
        <label htmlFor="settings-keyword" className="mb-1 block text-sm font-medium text-gray-200">{t("settings.keywords")}</label>
        <div className="flex gap-2"><input id="settings-keyword" value={keywordInput} onChange={(event) => setKeywordInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addKeyword(); } }} aria-invalid={!valid} aria-describedby={!valid ? "settings-keywords-error" : undefined} className="min-w-0 flex-1 rounded-md border border-gray-600 bg-gray-900 px-3 py-2 text-gray-100" /><button type="button" onClick={addKeyword} className="rounded-md border border-gray-600 px-3 py-2 text-sm text-gray-200">{t("settings.add")}</button></div>
        <div className="mt-2 flex flex-wrap gap-2">{keywords.map((item, index) => <button type="button" key={`${item}-${index}`} onClick={() => setKeywords((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="rounded-full bg-gray-700 px-3 py-1 text-xs text-gray-200">{item} ×</button>)}</div>
        {!valid ? <p id="settings-keywords-error" role="alert" className="mt-2 text-sm text-red-300">{t("settings.invalidKeywords")}</p> : null}
      </div>
      {error ? <p role="alert" className="text-sm text-red-300">{error}</p> : null}
      {success ? <p role="status" className="text-sm text-teal-300">{t("settings.saved")}</p> : null}
      <div className="flex gap-2"><button type="submit" disabled={!dirty || !valid || busy} className="rounded-md bg-teal-400 px-4 py-2 text-sm font-medium text-teal-950 disabled:cursor-not-allowed disabled:opacity-50">{busy ? t("settings.saving") : t("settings.save")}</button><button type="button" disabled={!dirty || busy} onClick={() => { setKeywords(initial.keywords); setEmailOptIn(initial.emailOptIn); setPreferredCurrency(initial.preferredCurrency ?? currency); }} className="rounded-md border border-gray-600 px-4 py-2 text-sm text-gray-200 disabled:opacity-50">{t("settings.reset")}</button></div>
    </form>
  );
}
