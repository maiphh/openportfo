"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useT } from "@/components/LanguageProvider";
import { useAuthProfile } from "@/lib/use-auth-profile";
import GeneralTab from "@/components/settings/GeneralTab";
import AvatarTab from "@/components/settings/AvatarTab";
import FxTab from "@/components/settings/FxTab";
import ChatbotTab from "@/components/settings/ChatbotTab";

const TAB_IDS = ["general", "avatar", "fx", "chatbot"] as const;
type TabId = (typeof TAB_IDS)[number];

function validTab(value: string | null): TabId {
  return TAB_IDS.includes(value as TabId) ? (value as TabId) : "general";
}

export default function SettingsPageClient() {
  const t = useT();
  const auth = useAuthProfile();
  const router = useRouter();
  const pathname = usePathname() || "/settings";
  const search = useSearchParams();
  const requested = search.get("tab");
  const isAdmin = auth.profile?.role === "admin";
  const [selected, setSelected] = useState<TabId>(() => {
    const initial = validTab(requested);
    return initial === "chatbot" && !isAdmin ? "general" : initial;
  });
  const tabsRef = useRef<Array<HTMLButtonElement | null>>([]);

  const tab = useMemo(() => {
    const candidate = validTab(requested);
    return candidate === "chatbot" && !isAdmin ? "general" : candidate;
  }, [isAdmin, requested]);
  const visibleSelected = selected === "chatbot" && !isAdmin ? "general" : selected;

  useEffect(() => {
    setSelected(tab);
    if (requested !== null && (requested !== tab || requested === "general")) router.replace("/settings", { scroll: false });
    else if (requested === null && tab !== "general") router.replace(`/settings?tab=${tab}`, { scroll: false });
  }, [requested, router, tab]);

  const choose = (next: TabId) => {
    if (next === "chatbot" && !isAdmin) return;
    setSelected(next);
    router.push(next === "general" ? "/settings" : `/settings?tab=${next}`, { scroll: false });
  };

  if (!auth.hydrated || (auth.loading && !auth.profile)) return <div aria-busy="true" className="mx-auto max-w-5xl animate-pulse px-4"><div className="h-8 w-48 rounded bg-gray-700" /><div className="mt-6 h-72 rounded-xl bg-gray-800" /></div>;
  if (!auth.token || !auth.profile) {
    const next = `${pathname}${search.toString() ? `?${search.toString()}` : ""}`;
    return <section className="mx-auto max-w-xl rounded-xl border border-gray-700 bg-gray-800 p-8 text-center"><h1 className="text-2xl font-semibold text-gray-100">{t("settings.title")}</h1><p className="mt-3 text-sm text-gray-400">{t("settings.signInPrompt")}</p>{auth.cognitoConfigured ? <button type="button" onClick={() => void auth.signIn(next)} className="mt-6 rounded-md bg-teal-400 px-4 py-2 font-medium text-teal-950">{t("settings.signIn")}</button> : null}</section>;
  }

  const tabLabels: Record<TabId, string> = { general: t("settings.general"), avatar: t("settings.avatar"), fx: t("settings.fx"), chatbot: t("settings.chatbot") };
  const moveTab = (offset: number) => {
    const available = TAB_IDS.filter((item) => item !== "chatbot" || isAdmin);
    const currentIndex = Math.max(0, available.indexOf(visibleSelected));
    const next = available[(currentIndex + offset + available.length) % available.length] ?? "general";
    choose(next);
    requestAnimationFrame(() => tabsRef.current[TAB_IDS.indexOf(next)]?.focus());
  };
  return (
    <section className="mx-auto max-w-5xl space-y-6 px-4">
      <div><h1 className="text-3xl font-semibold text-gray-100">{t("settings.title")}</h1><p className="mt-1 text-sm text-gray-500">{t("settings.subtitle")}</p></div>
      <div className="grid gap-6 sm:grid-cols-[minmax(9rem,14rem)_1fr]">
        <div role="tablist" aria-label={t("settings.tabs")} className="flex gap-2 overflow-x-auto sm:flex-col sm:overflow-visible">
          {TAB_IDS.map((item, index) => {
            if (item === "chatbot" && !isAdmin) return null;
            return <button key={item} id={`settings-tab-${item}`} ref={(node) => { tabsRef.current[index] = node; }} type="button" role="tab" aria-selected={visibleSelected === item} aria-controls={`settings-panel-${item}`} tabIndex={visibleSelected === item ? 0 : -1} onClick={() => choose(item)} onKeyDown={(event) => { if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); moveTab(1); } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); moveTab(-1); } else if (event.key === "Home") { event.preventDefault(); choose("general"); tabsRef.current[0]?.focus(); } else if (event.key === "End") { event.preventDefault(); const last = isAdmin ? "chatbot" : "fx"; choose(last); tabsRef.current[TAB_IDS.indexOf(last)]?.focus(); } }} className={`whitespace-nowrap rounded-md px-3 py-2 text-left text-sm ${visibleSelected === item ? "bg-teal-400/15 text-teal-200" : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"}`}>{tabLabels[item]}</button>;
          })}
        </div>
        <div id={`settings-panel-${visibleSelected}`} role="tabpanel" aria-labelledby={`settings-tab-${visibleSelected}`} className="min-w-0 rounded-xl border border-gray-700 bg-gray-800 p-5 shadow-xl">{visibleSelected === "general" ? <GeneralTab auth={auth} /> : visibleSelected === "avatar" ? <AvatarTab auth={auth} /> : visibleSelected === "fx" ? <FxTab auth={auth} /> : <ChatbotTab auth={auth} />}</div>
      </div>
    </section>
  );
}
