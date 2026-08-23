"use client";

import { useCallback, useContext, useEffect, useRef, useState } from "react";
import {
  AuthApiError,
  AUTH_CHANGE_EVENT,
  clearAuthToken,
  fetchAuthMe,
  isAuthTokenStorageKey,
  readAuthToken,
  type AuthProfile,
} from "@/lib/auth";
import { beginHostedUiLogin, isCognitoConfigured, logoutFromApp } from "@/lib/cognito";
import { AuthProfileContext, type AuthProfileController } from "@/lib/auth-profile-context";

export type { AuthProfileController } from "@/lib/auth-profile-context";

/** Shared provider hook with a standalone fallback for isolated consumers. */
function useStandaloneAuthProfile(disabled = false): AuthProfileController {
  const [hydrated, setHydrated] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestRef = useRef<AbortController | null>(null);
  const profileTokenRef = useRef<string | null>(null);

  const refresh = useCallback(() => setToken(readAuthToken()), []);
  const reloadProfile = useCallback(async () => {
    requestRef.current?.abort();
    const currentToken = token ?? readAuthToken();
    if (!currentToken) {
      profileTokenRef.current = null;
      setProfile(null);
      setLoading(false);
      return null;
    }
    if (profileTokenRef.current !== currentToken) {
      profileTokenRef.current = currentToken;
      setProfile(null);
    }
    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    try {
      const next = await fetchAuthMe({ token: currentToken, signal: controller.signal });
      if (controller.signal.aborted) return null;
      profileTokenRef.current = currentToken;
      setProfile(next);
      setError(null);
      return next;
    } catch (reason: unknown) {
      if (controller.signal.aborted) return null;
      if (reason instanceof AuthApiError && reason.authRequired) {
        clearAuthToken();
        setToken(null);
        profileTokenRef.current = null;
        setProfile(null);
        setError(null);
      } else {
        setProfile(null);
        setError(reason instanceof Error ? reason.message : "Unable to load account.");
      }
      return null;
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (disabled) return;
    refresh();
    setHydrated(true);
  }, [disabled, refresh]);
  useEffect(() => {
    if (disabled || !hydrated) return;
    if (!token) {
      setProfile(null);
      setLoading(false);
      return;
    }
    void reloadProfile();
    return () => requestRef.current?.abort();
  }, [disabled, hydrated, reloadProfile, token]);
  useEffect(() => {
    if (disabled || !hydrated) return;
    const sync = () => refresh();
    const storage = (event: StorageEvent) => {
      if (isAuthTokenStorageKey(event.key)) sync();
    };
    window.addEventListener(AUTH_CHANGE_EVENT, sync);
    window.addEventListener("storage", storage);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener(AUTH_CHANGE_EVENT, sync);
      window.removeEventListener("storage", storage);
      window.removeEventListener("focus", sync);
    };
  }, [disabled, hydrated, refresh]);

  const signIn = useCallback(async (next?: string) => {
    try {
      await beginHostedUiLogin({ next: next ?? "/" });
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to start sign-in.");
    }
  }, []);
  const signOut = useCallback(() => {
    const { cognitoLogoutUrl } = logoutFromApp();
    requestRef.current?.abort();
    setToken(null);
    setProfile(null);
    setError(null);
    if (cognitoLogoutUrl && typeof window !== "undefined") {
      try { window.location.assign(cognitoLogoutUrl); } catch { /* local logout completed */ }
    }
  }, []);
  const replaceProfile = useCallback((next: AuthProfile) => setProfile(next), []);
  return {
    hydrated,
    token,
    profile,
    loading,
    error,
    cognitoConfigured: isCognitoConfigured(),
    refresh,
    reloadProfile,
    replaceProfile,
    signIn,
    signOut,
  };
}

export function useAuthProfile(): AuthProfileController {
  const context = useContext(AuthProfileContext);
  const standalone = useStandaloneAuthProfile(Boolean(context));
  return context ?? standalone;
}
