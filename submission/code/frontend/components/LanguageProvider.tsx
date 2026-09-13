"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { DEFAULT_LANG, readStoredLang, translate, writeStoredLang, type Lang } from "@/lib/i18n";

type LanguageContextValue = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
  mounted: boolean;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(DEFAULT_LANG);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const next = readStoredLang();
    setLangState(next);
    document.documentElement.lang = next;
    setMounted(true);
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    document.documentElement.lang = next;
    writeStoredLang(next);
  }, []);
  const t = useCallback((key: string) => translate(lang, key), [lang]);
  const value = useMemo(() => ({ lang, setLang, t, mounted }), [lang, mounted, setLang, t]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useLanguage must be used within LanguageProvider");
  return context;
}

export function useT(): (key: string) => string {
  const context = useContext(LanguageContext);
  return context?.t ?? ((key: string) => translate(DEFAULT_LANG, key));
}
