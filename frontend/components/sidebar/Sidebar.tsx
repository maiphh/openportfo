"use client";

import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import BrandLogo, { BrandMark } from "@/components/BrandLogo";
import SidebarNav from "@/components/sidebar/SidebarNav";
import SidebarUserChip from "@/components/sidebar/SidebarUserChip";
import { Button } from "@/components/ui/button";
import { useT } from "@/components/LanguageProvider";
import type { AuthProfileController } from "@/lib/use-auth-profile";
import { cn } from "@/lib/utils";

export const SIDEBAR_COLLAPSED_STORAGE_KEY = "openportfo.sidebar.collapsed";

export type SidebarProps = {
  collapsed: boolean;
  auth: AuthProfileController;
  onToggleCollapsed: () => void;
  onSearch: () => void;
  onOpenSettings: () => void;
  onNavigate?: () => void;
};

export default function Sidebar({ collapsed, auth, onToggleCollapsed, onSearch, onOpenSettings, onNavigate }: SidebarProps) {
  const t = useT();
  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-40 hidden flex-col border-r border-gray-600 bg-gray-800 transition-[width] duration-200 sm:flex",
        collapsed ? "w-16" : "w-60",
      )}
      aria-label="Sidebar"
    >
      <div className={cn("flex h-16 items-center border-b border-gray-700", collapsed ? "justify-center px-2" : "justify-between px-3")}>
        {collapsed ? <BrandMark className="h-8 w-8" /> : <BrandLogo />}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-expanded={!collapsed}
          aria-label={collapsed ? t("nav.expand") : t("nav.collapse")}
          title={collapsed ? t("nav.expand") : t("nav.collapse")}
          onClick={onToggleCollapsed}
        >
          {collapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
        </Button>
      </div>
      <div className={cn("flex-1 overflow-y-auto py-4", collapsed ? "px-2" : "px-3")}>
        <SidebarNav
          collapsed={collapsed}
          onSearch={onSearch}
          onNavigate={onNavigate}
          isAdmin={auth.profile?.role === "admin"}
        />
      </div>
      <div className={cn("border-t border-gray-700 py-3", collapsed ? "px-2" : "px-3")}>
        <SidebarUserChip collapsed={collapsed} auth={auth} onOpenSettings={onOpenSettings} />
      </div>
    </aside>
  );
}
