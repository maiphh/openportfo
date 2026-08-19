/** Cognito/Bearer token helpers (BL-001 pragmatic auth gate). */

export const AUTH_TOKEN_STORAGE_KEY = "artryx.accessToken";

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
