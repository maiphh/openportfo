"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ComponentType } from "react";
import {
  Bitcoin,
  Briefcase,
  ChevronDown,
  LayoutDashboard,
  Search,
  Settings,
  ShieldCheck,
  Star,
  TrendingUp,
} from "lucide-react";
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
  isAdmin?: boolean;
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
      data-active={active ? "true" : "false"}
      className={cn(
        "nav-pill",
        collapsed && "justify-center px-2",
        active ? "bg-gray-700/70 text-gray-100" : "",
      )}
    >
      <Icon className="size-[18px] shrink-0 opacity-90" aria-hidden="true" />
      <span className={cn("truncate", collapsed && "sr-only")}>{label}</span>
    </Link>
  );
}

function SectionLabel({ children, collapsed }: { children: string; collapsed: boolean }) {
  if (collapsed) return <div className="my-2 h-px bg-gray-700/80" aria-hidden />;
  return (
    <p className="mb-1 mt-4 px-3 text-[11px] font-medium uppercase tracking-[0.14em] text-gray-500 first:mt-0">
      {children}
    </p>
  );
}

export default function SidebarNav({ collapsed, onSearch, onNavigate, isAdmin = false }: SidebarNavProps) {
  const t = useT();
  const pathname = normalizePath(usePathname() ?? "/");
  const [marketOpen, setMarketOpen] = useState(true);
  const marketActive = MARKET_ACTIVE.has(pathname);

  return (
    <nav aria-label="Primary" className="flex flex-col gap-0.5">
      <button
        type="button"
        title={collapsed ? t("nav.search") : undefined}
        aria-label={t("nav.search")}
        onClick={onSearch}
        className={cn(
          "nav-pill mb-3 rounded-full border border-gray-600/70 bg-gray-800/50 text-gray-400 hover:border-gray-500 hover:bg-gray-700/50",
          collapsed && "justify-center px-2",
        )}
      >
        <Search className="size-[18px] shrink-0" aria-hidden="true" />
        <span className={cn("flex-1 text-left", collapsed && "sr-only")}>{t("nav.search")}</span>
        {!collapsed ? (
          <kbd className="rounded-full border border-gray-600 bg-gray-900/80 px-1.5 py-0.5 text-[10px] text-gray-500">
            ⌘K
          </kbd>
        ) : null}
      </button>

      <SectionLabel collapsed={collapsed}>Overview</SectionLabel>

      {!collapsed ? (
        <button
          type="button"
          aria-expanded={marketOpen}
          onClick={() => setMarketOpen((value) => !value)}
          className={cn("nav-pill", marketActive && "text-gray-100")}
        >
          <LayoutDashboard className="size-[18px] shrink-0" aria-hidden="true" />
          <span className="flex-1 text-left">{t("nav.market")}</span>
          <ChevronDown
            className={cn("size-3.5 text-gray-500 transition-transform duration-200", marketOpen && "rotate-180")}
            aria-hidden="true"
          />
        </button>
      ) : null}

      {collapsed || marketOpen ? (
        <div className={cn("flex flex-col gap-0.5", !collapsed && "ml-2 border-l border-gray-700/80 pl-2")}>
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

      <SectionLabel collapsed={collapsed}>Account</SectionLabel>

      <NavLink
        href="/settings"
        label={t("nav.settings")}
        icon={Settings}
        active={pathname === "/settings"}
        collapsed={collapsed}
        onNavigate={onNavigate}
      />
      {isAdmin ? (
        <NavLink
          href="/admin"
          label={t("nav.admin")}
          icon={ShieldCheck}
          active={pathname === "/admin"}
          collapsed={collapsed}
          onNavigate={onNavigate}
        />
      ) : null}
    </nav>
  );
}
