"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ComponentType } from "react";
import { Bitcoin, Briefcase, ChevronDown, LayoutDashboard, Search, Star, TrendingUp } from "lucide-react";
import { useT } from "@/components/LanguageProvider";
import { cn } from "@/lib/utils";

type Icon = ComponentType<{ className?: string }>;

export const NAV_ITEMS = [
  { href: "/portfolio", labelKey: "nav.portfolio", icon: Briefcase },
  { href: "/watchlist", labelKey: "nav.watchlist", icon: Star },
] as const;

export const MARKET_ACTIVE = new Set(["/", "/markets", "/markets/stock", "/markets/crypto"]);

function normalizePath(pathname: string) {
  if (!pathname || pathname === "/") return "/";
  return pathname.replace(/\/+$/, "") || "/";
}

export type SidebarNavProps = {
  collapsed: boolean;
  onSearch: () => void;
  onNavigate?: () => void;
};

function NavLink({
  href,
  label,
  icon: Icon,
  active,
  collapsed,
  onNavigate,
}: {
  href: string;
  label: string;
  icon: Icon;
  active: boolean;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  return (
    <Link
      href={href}
      title={collapsed ? label : undefined}
      aria-label={collapsed ? label : undefined}
      onClick={onNavigate}
      className={cn(
        "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
        collapsed ? "justify-center px-2" : "",
        active ? "bg-gray-700/60 text-gray-100" : "text-gray-500 hover:bg-gray-700/50 hover:text-gray-200",
        active && "before:absolute before:inset-y-1.5 before:left-0 before:w-0.5 before:rounded-full before:bg-teal-400",
      )}
    >
      <Icon className="size-5 shrink-0" aria-hidden="true" />
      <span className={cn("truncate", collapsed && "sr-only")}>{label}</span>
    </Link>
  );
}

export default function SidebarNav({ collapsed, onSearch, onNavigate }: SidebarNavProps) {
  const t = useT();
  const pathname = normalizePath(usePathname() ?? "/");
  const [marketOpen, setMarketOpen] = useState(true);
  const marketActive = MARKET_ACTIVE.has(pathname);

  return (
    <nav aria-label="Primary" className="flex flex-col gap-1">
      {!collapsed ? (
        <button
          type="button"
          aria-expanded={marketOpen}
          onClick={() => setMarketOpen((value) => !value)}
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
            marketActive ? "text-gray-100" : "text-gray-500 hover:bg-gray-700/50 hover:text-gray-200",
          )}
        >
          <LayoutDashboard className="size-5 shrink-0" aria-hidden="true" />
          <span className="flex-1 text-left">{t("nav.market")}</span>
          <ChevronDown className={cn("size-4 transition-transform", marketOpen && "rotate-180")} aria-hidden="true" />
        </button>
      ) : null}

      {collapsed || marketOpen ? (
        <div className={cn("flex flex-col gap-1", !collapsed && "ml-4 border-l border-gray-700 pl-2")}>
          <NavLink
            href="/markets/stock"
            label={t("nav.market.stock")}
            icon={TrendingUp}
            active={pathname === "/markets/stock" || (pathname === "/" && !collapsed)}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
          <NavLink
            href="/markets/crypto"
            label={t("nav.market.crypto")}
            icon={Bitcoin}
            active={pathname === "/markets/crypto"}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        </div>
      ) : null}

      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.href}
          href={item.href}
          label={t(item.labelKey)}
          icon={item.icon}
          active={pathname === normalizePath(item.href)}
          collapsed={collapsed}
          onNavigate={onNavigate}
        />
      ))}

      <button
        type="button"
        title={collapsed ? t("nav.search") : undefined}
        aria-label={t("nav.search")}
        onClick={onSearch}
        className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-500 transition-colors hover:bg-gray-700/50 hover:text-gray-200",
          collapsed && "justify-center px-2",
        )}
      >
        <Search className="size-5 shrink-0" aria-hidden="true" />
        <span className={cn(collapsed && "sr-only")}>{t("nav.search")}</span>
        {!collapsed ? <kbd className="ml-auto rounded border border-gray-600 px-1.5 py-0.5 text-[10px] text-gray-500">⌘K</kbd> : null}
      </button>
    </nav>
  );
}

