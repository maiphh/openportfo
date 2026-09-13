"use client";

import { LogIn, LogOut, MoreHorizontal } from "lucide-react";
import { useT } from "@/components/LanguageProvider";
import UserAvatar from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  const label = auth.loading
    ? "…"
    : signedIn && auth.profile
      ? profileDisplayName(auth.profile)
      : t("settings.account.guest");
  const email = auth.profile?.email?.trim() || null;

  return (
    <div
      className={cn(
        "rounded-xl border border-gray-600/70 bg-gray-800/60 p-1.5 transition-colors hover:border-gray-500/80",
        collapsed && "flex flex-col items-center gap-1 border-0 bg-transparent p-0",
      )}
    >
      <div className={cn("flex items-center gap-1", collapsed && "flex-col")}>
        <Button
          type="button"
          variant="ghost"
          className={cn(
            "min-w-0 flex-1 justify-start gap-2.5 bg-transparent px-2 py-1.5 text-left hover:bg-gray-700/70",
            collapsed && "flex-none px-1.5",
          )}
          aria-label={t("settings.title")}
          title={collapsed ? label : undefined}
          onClick={onOpenSettings}
        >
          <UserAvatar profile={auth.profile} className="h-8 w-8" />
          <span className={cn("min-w-0", collapsed && "sr-only")}>
            <span className="block truncate text-sm font-medium text-gray-100">{label}</span>
            <span className="block truncate text-[11px] text-gray-500">
              {signedIn ? email || "Signed in" : t("settings.account.signedOut")}
            </span>
          </span>
        </Button>

        {!collapsed ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-8 shrink-0 text-gray-500 hover:bg-gray-700/70 hover:text-gray-200"
                aria-label="Account menu"
              >
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" side="top" className="w-56 border-gray-600 bg-gray-900 p-1.5">
              <DropdownMenuLabel className="px-2 py-2 font-normal">
                <div className="truncate text-sm text-gray-100">{label}</div>
                {email ? <div className="truncate text-xs text-gray-500">{email}</div> : null}
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-gray-700" />
              <DropdownMenuItem
                className="rounded-md focus:bg-gray-700 focus:text-gray-100"
                onSelect={() => onOpenSettings()}
              >
                {t("settings.title")}
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-gray-700" />
              <DropdownMenuItem
                className="rounded-md focus:bg-gray-700 focus:text-gray-100"
                onSelect={() => {
                  if (signedIn) auth.signOut();
                  else if (auth.cognitoConfigured) void auth.signIn();
                }}
              >
                {signedIn ? (
                  <>
                    <LogOut className="size-4" />
                    {t("settings.signOut")}
                  </>
                ) : (
                  <>
                    <LogIn className="size-4" />
                    {t("settings.signIn")}
                  </>
                )}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}

        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={cn(
            "size-8 shrink-0 text-gray-500 hover:bg-gray-700/70 hover:text-gray-200",
            !collapsed && "sr-only",
          )}
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
    </div>
  );
}
