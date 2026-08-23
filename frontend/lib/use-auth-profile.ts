"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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

export type AuthProfileController = {
  hydrated: boolean;
  token: string | null;
  profile: AuthProfile | null;
  loading: boolean;
  error: string | null;
  cognitoConfigured: boolean;
  refresh: () => void;
  signIn: (next?: string) => Promise<void>;
  signOut: () => void;
};

export function useAuthProfile(): AuthProfileController {
  const [hydrated, setHydrated] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestRef = useRef<AbortController | null>(null);

  const refresh = useCallback(() => {
    setToken(readAuthToken());
  }, []);

  useEffect(() => {
    refresh();
    setHydrated(true);
  }, [refresh]);

  useEffect(() => {
    if (!hydrated) return;
    requestRef.current?.abort();
    if (!token) {
      setProfile(null);
      setLoading(false);
      setError(null);
      return;
    }

    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    setError(null);
    void fetchAuthMe({ token, signal: controller.signal })
      .then((nextProfile) => {
        if (controller.signal.aborted) return;
        setProfile(nextProfile);
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        if (reason instanceof AuthApiError && reason.authRequired) {
          clearAuthToken();
          setToken(null);
          setProfile(null);
          setError(null);
        } else {
          setProfile(null);
          setError(reason instanceof Error ? reason.message : "Unable to load account.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => {
      controller.abort();
      if (requestRef.current === controller) requestRef.current = null;
    };
  }, [hydrated, token]);

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
    setToken(null);
    setProfile(null);
    setError(null);
    if (cognitoLogoutUrl && typeof window !== "undefined") {
      try {
        window.location.assign(cognitoLogoutUrl);
      } catch {
        // jsdom and locked-down browsers may reject navigation; local logout
        // has already completed and remains the source of truth.
      }
    }
  }, []);

  return {
    hydrated,
    token,
    profile,
    loading,
    error,
    cognitoConfigured: isCognitoConfigured(),
    refresh,
    signIn,
    signOut,
  };
}

