"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
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

export default function AuthProfileProvider({ children }: { children: ReactNode }) {
  const [hydrated, setHydrated] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestRef = useRef<AbortController | null>(null);
  const requestGeneration = useRef(0);
  const profileTokenRef = useRef<string | null>(null);

  const refresh = useCallback(() => {
    setToken(readAuthToken());
  }, []);

  const loadProfile = useCallback(async (nextToken: string | null, force: boolean) => {
    requestRef.current?.abort();
    const generation = ++requestGeneration.current;
    if (!nextToken) {
      profileTokenRef.current = null;
      setProfile(null);
      setLoading(false);
      setError(null);
      return null;
    }
    // A token transition must not temporarily expose the previous user's
    // profile while the replacement request is in flight. Forced reloads for
    // the same token intentionally retain the current profile until success.
    if (profileTokenRef.current !== nextToken) {
      profileTokenRef.current = nextToken;
      setProfile(null);
    }
    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      // `force` documents that reloadProfile intentionally requests even when
      // the bearer string has not changed; fetchAuthMe has no token cache.
      void force;
      const nextProfile = await fetchAuthMe({ token: nextToken, signal: controller.signal });
      if (controller.signal.aborted || generation !== requestGeneration.current) return null;
      profileTokenRef.current = nextToken;
      setProfile(nextProfile);
      return nextProfile;
    } catch (reason: unknown) {
      if (controller.signal.aborted || generation !== requestGeneration.current) return null;
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
      if (!controller.signal.aborted && generation === requestGeneration.current) setLoading(false);
      if (requestRef.current === controller) requestRef.current = null;
    }
  }, []);

  useEffect(() => {
    refresh();
    setHydrated(true);
  }, [refresh]);

  useEffect(() => {
    if (!hydrated) return;
    void loadProfile(token, false);
    return () => requestRef.current?.abort();
  }, [hydrated, loadProfile, token]);

  const reloadProfile = useCallback(async () => {
    const currentToken = token ?? readAuthToken();
    return loadProfile(currentToken, true);
  }, [loadProfile, token]);

  const replaceProfile = useCallback((nextProfile: AuthProfile) => {
    profileTokenRef.current = token;
    setProfile(nextProfile);
    setError(null);
  }, [token]);

  useEffect(() => {
    if (!hydrated) return;
    const sync = () => refresh();
    const onStorage = (event: StorageEvent) => {
      if (isAuthTokenStorageKey(event.key)) sync();
    };
    window.addEventListener(AUTH_CHANGE_EVENT, sync);
    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener(AUTH_CHANGE_EVENT, sync);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", sync);
    };
  }, [hydrated, refresh]);

  const signIn = useCallback(async (next?: string) => {
    setError(null);
    try {
      await beginHostedUiLogin({ next: next ?? (typeof window !== "undefined" ? window.location.pathname : "/") });
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to start sign-in.");
    }
  }, []);

  const signOut = useCallback(() => {
    const { cognitoLogoutUrl } = logoutFromApp();
    requestRef.current?.abort();
    requestGeneration.current += 1;
    profileTokenRef.current = null;
    setToken(null);
    setProfile(null);
    setError(null);
    if (cognitoLogoutUrl && typeof window !== "undefined") {
      try {
        window.location.assign(cognitoLogoutUrl);
      } catch {
        // Local logout remains complete when navigation is unavailable.
      }
    }
  }, []);

  const value = useMemo<AuthProfileController>(
    () => ({
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
    }),
    [error, hydrated, loading, profile, refresh, reloadProfile, replaceProfile, signIn, signOut, token],
  );

  return <AuthProfileContext.Provider value={value}>{children}</AuthProfileContext.Provider>;
}
