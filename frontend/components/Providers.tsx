"use client";

import { useEffect, type ReactNode } from "react";
import { CurrencyProvider } from "@/components/currency/CurrencyProvider";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import { LanguageProvider } from "@/components/LanguageProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import AuthProfileProvider from "@/components/auth/AuthProfileProvider";
import { useAuthProfile } from "@/lib/use-auth-profile";

function ProfileCurrencySynchronizer() {
  const auth = useAuthProfile();
  const { setCurrency } = useDisplayCurrency();
  useEffect(() => {
    const preferred = auth.profile?.preferredCurrency;
    if (preferred === "USD" || preferred === "VND" || preferred === "EUR") setCurrency(preferred);
  }, [auth.profile?.preferredCurrency, setCurrency]);
  return null;
}

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <CurrencyProvider>
          <AuthProfileProvider>
            <ProfileCurrencySynchronizer />
            {children}
          </AuthProfileProvider>
        </CurrencyProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}
