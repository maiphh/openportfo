/** Cognito/Bearer token helpers (BL-001 gate + BL-006 Hosted UI ID token). */

import { apiBase } from "@/lib/api";

export const AUTH_TOKEN_STORAGE_KEY = "artryx.accessToken";

export type AuthProfile = {
  userId: string;
  email: string;
  name: string | null;
  role?: string;
};

export class AuthApiError extends Error {
  status: number;
  authRequired: boolean;

  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.name = "AuthApiError";
    this.status = status;
    this.authRequired = status === 401 || status === 403;
  }
}

export function readAuthToken(
  storage: Pick<Storage, "getItem"> | null | undefined = typeof window !== "undefined" ? window.localStorage : null,
): string | null {
  if (!storage) return null;
  try {
    const raw = storage.getItem(AUTH_TOKEN_STORAGE_KEY);
    return raw?.trim() || null;
  } catch {
    return null;
  }
}

export function writeAuthToken(
  token: string,
  storage: Pick<Storage, "setItem"> | null | undefined = typeof window !== "undefined" ? window.localStorage : null,
): void {
  if (!storage) return;
  const cleaned = token.trim();
  if (!cleaned) return;
  try {
    storage.setItem(
      AUTH_TOKEN_STORAGE_KEY,
      cleaned.startsWith("Bearer ") ? cleaned.slice(7).trim() : cleaned,
    );
  } catch {
    // Ignore quota / private mode.
  }
}

export function clearAuthToken(
  storage: Pick<Storage, "removeItem"> | null | undefined = typeof window !== "undefined" ? window.localStorage : null,
): void {
  if (!storage) return;
  try {
    storage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    // Ignore.
  }
}

export function bearerHeader(token: string | null | undefined): Record<string, string> {
  const raw = (token || "").trim();
  if (!raw) return {};
  return { Authorization: raw.startsWith("Bearer ") ? raw : `Bearer ${raw}` };
}

export async function fetchAuthMe(options?: {
  token?: string | null;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
}): Promise<AuthProfile> {
  const token = options?.token ?? readAuthToken();
  const fetchImpl = options?.fetchImpl ?? fetch;
  const res = await fetchImpl(`${apiBase()}/api/auth/me`, {
    method: "GET",
    headers: {
      Accept: "application/json",
      ...bearerHeader(token),
    },
    signal: options?.signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new AuthApiError(res.status, `Profile HTTP ${res.status}`);
  }
  const body = (await res.json()) as Partial<AuthProfile>;
  if (!body || typeof body.userId !== "string" || !body.userId.trim()) {
    throw new Error("Invalid profile payload");
  }
  return {
    userId: body.userId,
    email: typeof body.email === "string" ? body.email : "",
    name: typeof body.name === "string" && body.name.trim() ? body.name : null,
    role: typeof body.role === "string" ? body.role : undefined,
  };
}

export function profileDisplayName(profile: AuthProfile): string {
  return profile.name?.trim() || profile.email.trim() || "Account";
}
