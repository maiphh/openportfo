/** Cognito/Bearer token helpers (BL-001 gate + BL-006 Hosted UI ID token). */

import { apiBase } from "@/lib/api";

export const AUTH_TOKEN_STORAGE_KEY = "artryx.accessToken";
export const AUTH_CHANGE_EVENT = "openportfo:auth-change";

/** Notify client widgets that the active bearer token may have changed. */
export function notifyAuthChanged(): void {
  if (typeof window === "undefined") return;
  try {
    window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
  } catch {
    // Browser event dispatch is best-effort; auth storage remains canonical.
  }
}

type AuthReadStorage = Pick<Storage, "getItem">;
type AuthWriteStorage = Pick<Storage, "setItem">;
type AuthClearStorage = Pick<Storage, "removeItem">;
type BrowserAuthStorage = AuthReadStorage & AuthWriteStorage & AuthClearStorage;

function browserStorage(kind: "sessionStorage" | "localStorage"): BrowserAuthStorage | null {
  if (typeof window === "undefined") return null;
  try {
    return window[kind];
  } catch {
    // Private browsing and restrictive storage policies can throw while the
    // storage property is being read, before getItem/setItem is called.
    return null;
  }
}

function cleanToken(raw: string | null): string | null {
  const token = raw?.trim() || "";
  return token || null;
}

function readStoredToken(storage: AuthReadStorage | null | undefined): string | null {
  if (!storage) return null;
  try {
    return cleanToken(storage.getItem(AUTH_TOKEN_STORAGE_KEY));
  } catch {
    return null;
  }
}

function writeStoredToken(storage: AuthWriteStorage | null | undefined, token: string): boolean {
  if (!storage) return false;
  try {
    storage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    return true;
  } catch {
    return false;
  }
}

function removeStoredToken(storage: AuthClearStorage | null | undefined): void {
  if (!storage) return;
  try {
    storage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage failures. Auth callers should fail closed without
    // turning browser privacy settings into an application error.
  }
}

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
  storage?: AuthReadStorage | null,
): string | null {
  // An explicitly supplied store is useful for deterministic callers/tests
  // and means "read this store". The browser default is sessionStorage.
  if (storage !== undefined) return readStoredToken(storage);

  const session = browserStorage("sessionStorage");
  const legacy = browserStorage("localStorage");
  const sessionToken = readStoredToken(session);
  const legacyToken = readStoredToken(legacy);

  if (sessionToken) {
    // Remove a stale copy left by an older release even when the current
    // session token already exists.
    if (legacyToken) removeStoredToken(legacy);
    return sessionToken;
  }

  if (!legacyToken) return null;

  // Migrate the old persistent token only after the tab-scoped write has
  // succeeded. If storage is unavailable, fail closed and remove the legacy
  // copy so a bearer token is not kept across browser sessions.
  if (writeStoredToken(session, legacyToken)) {
    removeStoredToken(legacy);
    return legacyToken;
  }

  removeStoredToken(legacy);
  return null;
}

export function writeAuthToken(
  token: string,
  storage?: AuthWriteStorage | null,
): boolean {
  const cleaned = token.trim();
  if (!cleaned) return false;
  const normalized = cleaned.startsWith("Bearer ") ? cleaned.slice(7).trim() : cleaned;
  if (!normalized) return false;
  if (storage !== undefined) {
    const stored = writeStoredToken(storage, normalized);
    if (stored) notifyAuthChanged();
    return stored;
  }
  const stored = writeStoredToken(browserStorage("sessionStorage"), normalized);
  if (stored) {
    removeStoredToken(browserStorage("localStorage"));
    notifyAuthChanged();
  }
  return stored;
}

export function clearAuthToken(
  storage?: AuthClearStorage | null,
): void {
  if (storage !== undefined) {
    removeStoredToken(storage);
    notifyAuthChanged();
    return;
  }
  removeStoredToken(browserStorage("sessionStorage"));
  removeStoredToken(browserStorage("localStorage"));
  notifyAuthChanged();
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
  timeoutMs?: number;
}): Promise<AuthProfile> {
  const token = options?.token ?? readAuthToken();
  const fetchImpl = options?.fetchImpl ?? fetch;
  const controller = new AbortController();
  const callerSignal = options?.signal;
  const abortFromCaller = () => controller.abort(callerSignal?.reason);
  if (callerSignal?.aborted) abortFromCaller();
  else callerSignal?.addEventListener("abort", abortFromCaller, { once: true });
  const timeout = globalThis.setTimeout(() => {
    controller.abort(new DOMException("Profile request timed out", "TimeoutError"));
  }, options?.timeoutMs ?? 10_000);

  try {
    const res = await fetchImpl(`${apiBase()}/api/auth/me`, {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...bearerHeader(token),
      },
      signal: controller.signal,
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
  } finally {
    globalThis.clearTimeout(timeout);
    callerSignal?.removeEventListener("abort", abortFromCaller);
  }
}

export function profileDisplayName(profile: AuthProfile): string {
  return profile.name?.trim() || profile.email.trim() || "Account";
}
