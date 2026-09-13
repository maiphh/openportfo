"use client";

import Link from "next/link";
import { Coins, Languages, LogIn, LogOut, Moon, Sun, X } from "lucide-react";
import { useEffect, useRef, useState, type RefObject } from "react";
import { usePathname } from "next/navigation";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import UserAvatar from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import { DISPLAY_CURRENCIES, type DisplayCurrency } from "@/lib/currency";
import { profileDisplayName } from "@/lib/auth";
import { useLanguage, useT } from "@/components/LanguageProvider";
import { useTheme } from "@/components/ThemeProvider";
import { updateUserSettings } from "@/lib/settings-api";
import type { AuthProfileController } from "@/lib/use-auth-profile";

export type UserSettingsModalProps = {
  open: boolean;
  auth: AuthProfileController;
  onClose: () => void;
  returnFocusRef?: RefObject<HTMLElement | null>;
  restoreFocusOnClose?: boolean;
};

function focusableElements(root: HTMLElement | null): HTMLElement[] {
  if (!root) return [];
  return Array.from(root.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'));
}

export default function UserSettingsModal({ open, auth, onClose, returnFocusRef, restoreFocusOnClose = true }: UserSettingsModalProps) {
  const t = useT();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { lang, setLang } = useLanguage();
  const { currency, setCurrency } = useDisplayCurrency();
  const [currencyError, setCurrencyError] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      openerRef.current = returnFocusRef?.current ?? (document.activeElement as HTMLElement | null);
      setCurrencyError(null);
      closeRef.current?.focus();
    } else if (restoreFocusOnClose) openerRef.current?.focus();
  }, [open, restoreFocusOnClose, returnFocusRef]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); onClose(); return; }
      if (event.key !== "Tab") return;
      const items = focusableElements(dialogRef.current);
      if (!items.length) return;
      const first = items[0]; const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, open]);

  if (!open) return null;
  const signedIn = Boolean(auth.token && auth.profile);
  const accountLabel = auth.loading ? "…" : signedIn && auth.profile ? profileDisplayName(auth.profile) : t("settings.account.signedOut");
  const selectCurrency = (next: DisplayCurrency) => {
    const previous = currency;
    setCurrency(next);
    setCurrencyError(null);
    if (!signedIn || !auth.token) return;
    void updateUserSettings(auth.token, { preferredCurrency: next }).then((updated) => {
      auth.replaceProfile(updated);
      if (updated.preferredCurrency === "USD" || updated.preferredCurrency === "VND" || updated.preferredCurrency === "EUR") setCurrency(updated.preferredCurrency);
    }).catch((reason: unknown) => {
      setCurrency(previous);
      setCurrencyError(reason instanceof Error ? reason.message : t("settings.saveError"));
    });
  };
  const navigate = () => { onClose(); };

 return <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/60 p-4" onClick={onClose}><div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="user-settings-title" className="relative max-h-[min(90vh,720px)] w-full max-w-md overflow-y-auto rounded-xl border border-gray-600 bg-gray-800 shadow-2xl" onClick={(event) => event.stopPropagation()}><div className="flex items-center justify-between border-b border-gray-700 px-5 py-4"><h2 id="user-settings-title" className="text-lg font-semibold text-gray-100">{t("settings.title")}</h2><Button ref={closeRef} type="button" variant="ghost" size="icon" aria-label={t("common.close")} onClick={onClose}><X className="size-4" /></Button></div><div className="space-y-5 px-5 py-5"><section className="flex items-center justify-between gap-3 rounded-lg border border-gray-700 bg-gray-900/40 p-3"><div className="flex min-w-0 items-center gap-3"><UserAvatar profile={auth.profile} /><div className="min-w-0"><p className="truncate text-sm font-medium text-gray-100">{accountLabel}</p><p className="truncate text-xs text-gray-500">{signedIn ? auth.profile?.email : t("settings.account.guest")}</p></div></div>{signedIn ? <Button type="button" variant="outline" size="sm" onClick={auth.signOut}><LogOut className="size-4" /> {t("settings.signOut")}</Button> : auth.cognitoConfigured ? <Button type="button" variant="outline" size="sm" onClick={() => void auth.signIn(pathname ?? "/")}><LogIn className="size-4" /> {t("settings.signIn")}</Button> : null}</section><section><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">{t("settings.appearance")}</h3><div role="radiogroup" aria-label={t("settings.appearance")} className="grid grid-cols-2 gap-2">{([["light", t("settings.appearance.light"), Sun], ["dark", t("settings.appearance.dark"), Moon]] as const).map(([value, label, Icon]) => <button key={value} type="button" role="radio" aria-checked={theme === value} onClick={() => setTheme(value)} className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${theme === value ? "border-teal-400 bg-teal-400/10 text-gray-100" : "border-gray-700 text-gray-500"}`}><Icon className="size-4" /> {label}</button>)}</div></section><section><h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500"><Languages className="size-4" /> {t("settings.language")}</h3><div role="radiogroup" aria-label={t("settings.language")} className="grid grid-cols-2 gap-2">{(["en", "vi"] as const).map((value) => <button key={value} type="button" role="radio" aria-checked={lang === value} onClick={() => setLang(value)} className={`rounded-lg border px-3 py-2 text-left text-sm ${lang === value ? "border-teal-400 bg-teal-400/10 text-gray-100" : "border-gray-700 text-gray-500"}`}>{t(`settings.language.${value}`)}</button>)}</div></section><section><h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500"><Coins className="size-4" /> {t("settings.currency")}</h3><div role="radiogroup" aria-label={t("settings.currency")} className="grid grid-cols-3 gap-2">{DISPLAY_CURRENCIES.map((value) => <button key={value} type="button" role="radio" aria-checked={currency === value} onClick={() => selectCurrency(value)} className={`rounded-lg border px-3 py-2 text-sm ${currency === value ? "border-teal-400 bg-teal-400/10 text-gray-100" : "border-gray-700 text-gray-500"}`}>{value}</button>)}</div>{currencyError ? <p role="alert" className="mt-2 text-xs text-red-300">{currencyError}</p> : null}</section><nav aria-label={t("settings.more")} className="flex flex-wrap gap-3 border-t border-gray-700 pt-4 text-sm"><Link href="/settings" onClick={navigate} className="text-teal-300 underline">{t("settings.allSettings")}</Link><Link href="/settings?tab=fx" onClick={navigate} className="text-teal-300 underline">{t("settings.fxRates")}</Link></nav>{auth.error ? <p className="text-xs text-red-400">{auth.error}</p> : null}</div></div></div>;
}
