"use client";

import { LogIn, LogOut } from "lucide-react";
import { useT } from "@/components/LanguageProvider";
import UserAvatar from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import { profileDisplayName } from "@/lib/auth";
import type { AuthProfileController } from "@/lib/use-auth-profile";
import { cn } from "@/lib/utils";

export type SidebarUserChipProps = {
  collapsed: boolean;
  auth: AuthProfileController;
  onOpenSettings: () => void;
};

export default function SidebarUserChip({ collapsed, auth, onOpenSettings }: SidebarUserChipProps) {
  const t = useT();
  const signedIn = Boolean(auth.token && auth.profile);
  const label = auth.loading ? "…" : signedIn && auth.profile ? profileDisplayName(auth.profile) : t("settings.account.guest");
  return (
    <div className={cn("flex items-center gap-2", collapsed ? "flex-col" : "")}> 
      <Button
        type="button"
        variant="ghost"
        className={cn("min-w-0 flex-1 justify-start bg-transparent p-1 text-left hover:bg-gray-700", collapsed && "flex-none")}
        aria-label={t("settings.title")}
        title={collapsed ? label : undefined}
        onClick={onOpenSettings}
      >
        <UserAvatar profile={auth.profile} className="h-9 w-9" />
        <span className={cn("min-w-0 truncate text-sm text-gray-400", collapsed && "sr-only")}>{label}</span>
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={signedIn ? t("settings.signOut") : t("settings.signIn")}
        title={signedIn ? t("settings.signOut") : t("settings.signIn")}
        onClick={() => {
          if (signedIn) auth.signOut();
          else if (auth.cognitoConfigured) void auth.signIn();
        }}
      >
        {signedIn ? <LogOut className="size-4" /> : <LogIn className="size-4" />}
      </Button>
    </div>
  );
}

