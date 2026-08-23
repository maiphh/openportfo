"use client";

import { Menu } from "lucide-react";
import type { Ref } from "react";
import BrandLogo from "@/components/BrandLogo";
import UserAvatar from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import { useT } from "@/components/LanguageProvider";
import type { AuthProfile } from "@/lib/auth";

export type MobileTopbarProps = {
  menuOpen: boolean;
  menuButtonRef?: Ref<HTMLButtonElement>;
  profile: AuthProfile | null;
  onMenu: () => void;
  onOpenSettings: () => void;
};

export default function MobileTopbar({ menuOpen, menuButtonRef, profile, onMenu, onOpenSettings }: MobileTopbarProps) {
  const t = useT();
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-gray-600 bg-gray-800 px-3 sm:hidden">
      <Button
        ref={menuButtonRef}
        type="button"
        variant="ghost"
        size="icon"
        aria-expanded={menuOpen}
        aria-controls="mobile-sidebar-drawer"
        aria-label={t("nav.openMenu")}
        onClick={onMenu}
      >
        <Menu className="size-5" />
      </Button>
      <BrandLogo />
      <Button type="button" variant="ghost" size="icon" aria-label={t("settings.title")} onClick={onOpenSettings}>
        <UserAvatar profile={profile} className="h-8 w-8" />
      </Button>
    </header>
  );
}

