"use client";

import { createContext } from "react";
import type { AuthProfile } from "@/lib/auth";

export type AuthProfileController = {
  hydrated: boolean;
  token: string | null;
  profile: AuthProfile | null;
  loading: boolean;
  error: string | null;
  cognitoConfigured: boolean;
  refresh: () => void;
  reloadProfile: () => Promise<AuthProfile | null>;
  replaceProfile: (profile: AuthProfile) => void;
  signIn: (next?: string) => Promise<void>;
  signOut: () => void;
};

export const AuthProfileContext = createContext<AuthProfileController | null>(null);
