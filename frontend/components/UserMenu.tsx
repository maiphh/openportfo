"use client";

import { useEffect, useState } from "react";
import { LogIn, LogOut } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import NavItems from "@/components/NavItems";
import {
  AuthApiError,
  clearAuthToken,
  fetchAuthMe,
  profileDisplayName,
  readAuthToken,
  type AuthProfile,
} from "@/lib/auth";
import { beginHostedUiLogin, isCognitoConfigured, logoutFromApp } from "@/lib/cognito";

export default function UserMenu({ onSearch }: { onSearch?: () => void }) {
  const [hydrated, setHydrated] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  useEffect(() => {
    setToken(readAuthToken());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      setProfile(null);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    void fetchAuthMe({ token, signal: controller.signal })
      .then((me) => {
        if (!controller.signal.aborted) setProfile(me);
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (err instanceof AuthApiError && err.authRequired) {
          clearAuthToken();
          setToken(null);
          setProfile(null);
        } else {
          setProfile(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [hydrated, token]);

  const cognito = isCognitoConfigured();
  const signedIn = Boolean(token && profile);
  const displayName = profile ? profileDisplayName(profile) : "Guest";
  const initial = (signedIn ? displayName : "?").slice(0, 1).toUpperCase();

  const handleSignIn = () => {
    if (!cognito) return;
    setLoginError(null);
    void beginHostedUiLogin({
      next: typeof window !== "undefined" ? window.location.pathname : "/",
    }).catch((err: unknown) => {
      setLoginError(err instanceof Error ? err.message : "Unable to start sign-in.");
    });
  };

  const handleLogout = () => {
    const { cognitoLogoutUrl } = logoutFromApp();
    setToken(null);
    setProfile(null);
    if (cognitoLogoutUrl && typeof window !== "undefined") {
      window.location.assign(cognitoLogoutUrl);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="flex items-center gap-3 bg-transparent text-gray-400 hover:bg-gray-700">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-teal-500 text-sm font-bold text-teal-950">
              {hydrated ? initial : "?"}
            </AvatarFallback>
          </Avatar>
          <span data-testid="user-menu-label" className="hidden text-base font-medium md:inline">
            {!hydrated || loading ? "…" : signedIn ? displayName : cognito ? "Sign in" : "Guest"}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex items-center gap-3 py-1">
            <Avatar className="h-10 w-10">
              <AvatarFallback className="bg-teal-500 font-bold text-teal-950">{hydrated ? initial : "?"}</AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-gray-200">
                {!hydrated || loading ? "Loading…" : signedIn ? displayName : "Not signed in"}
              </span>
              <span className="text-xs text-gray-500">
                {signedIn ? profile?.email || "" : cognito ? "Use Cognito Hosted UI" : "Local token paste"}
              </span>
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {signedIn ? (
          <DropdownMenuItem onSelect={handleLogout}>
            <LogOut className="size-4" />
            Logout
          </DropdownMenuItem>
        ) : cognito ? (
          <DropdownMenuItem
            onSelect={(event) => {
              // Giữ menu mở để hiển thị lỗi nếu browser chặn PKCE storage.
              event.preventDefault();
              handleSignIn();
            }}
          >
            <LogIn className="size-4" />
            Sign in
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem disabled>Sign in unavailable</DropdownMenuItem>
        )}
        {loginError ? <p className="px-2 py-1.5 text-xs text-red-400">{loginError}</p> : null}
        <div className="sm:hidden">
          <DropdownMenuSeparator />
          <NavItems onSearch={onSearch} />
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
