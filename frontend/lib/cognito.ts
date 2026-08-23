/** Cognito Hosted UI + PKCE (BL-006). Browser talks to Cognito; no Next route handler. */

import {
  AuthApiError,
  clearAuthToken,
  fetchAuthMe,
  writeAuthToken,
  type AuthProfile,
} from "@/lib/auth";
export const PKCE_STORAGE_KEY = "openportfo.pkce";

const VERIFIER_BYTES = 32;
const STATE_BYTES = 16;

export type CognitoPublicConfig = {
  domain: string;
  clientId: string;
  region: string | null;
  appUrl: string;
};

export type PkceSession = {
  verifier: string;
  state: string;
  next: string;
};

type EnvLike = Record<string, string | undefined>;
type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function browserSessionStorage(): StorageLike | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function publicCognitoEnv(): EnvLike {
  return {
    NEXT_PUBLIC_COGNITO_DOMAIN: process.env.NEXT_PUBLIC_COGNITO_DOMAIN,
    NEXT_PUBLIC_COGNITO_CLIENT_ID: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID,
    NEXT_PUBLIC_COGNITO_REGION: process.env.NEXT_PUBLIC_COGNITO_REGION,
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
  };
}

export function normalizeCognitoDomain(raw: string): string {
  return raw.trim().replace(/^https?:\/\//i, "").replace(/\/+$/, "");
}

export function normalizeAppUrl(raw: string): string {
  return raw.trim().replace(/\/+$/, "");
}

export function callbackRedirectUri(appUrl: string): string {
  return `${normalizeAppUrl(appUrl)}/auth/callback/`;
}

export function postLogoutUri(appUrl: string): string {
  return `${normalizeAppUrl(appUrl)}/`;
}

export function safeNextPath(raw: string | null | undefined): string {
  const value = (raw || "").trim();
  if (!value.startsWith("/")) return "/";
  if (/[\\\u0000-\u001f\u007f]/.test(value)) return "/";
  try {
    const base = new URL("https://local.openportfo.invalid");
    const resolved = new URL(value, base);
    if (resolved.origin !== base.origin) return "/";
    return `${resolved.pathname}${resolved.search}${resolved.hash}`;
  } catch {
    return "/";
  }
}

export function readCognitoPublicParts(env: EnvLike = publicCognitoEnv()): {
  domain: string;
  clientId: string;
  region: string | null;
} | null {
  const domain = normalizeCognitoDomain(env.NEXT_PUBLIC_COGNITO_DOMAIN || "");
  const clientId = (env.NEXT_PUBLIC_COGNITO_CLIENT_ID || "").trim();
  if (!domain || !clientId) return null;
  const region = (env.NEXT_PUBLIC_COGNITO_REGION || "").trim() || null;
  return { domain, clientId, region };
}

export function isCognitoConfigured(env: EnvLike = publicCognitoEnv()): boolean {
  return readCognitoPublicParts(env) != null;
}

export function readCognitoConfig(env: EnvLike = publicCognitoEnv()): CognitoPublicConfig | null {
  const parts = readCognitoPublicParts(env);
  if (!parts) return null;
  let appUrl = normalizeAppUrl(env.NEXT_PUBLIC_APP_URL || "");
  if (!appUrl && typeof window !== "undefined") {
    appUrl = normalizeAppUrl(window.location.origin);
  }
  if (!appUrl) return null;
  return { ...parts, appUrl };
}

export function base64UrlEncode(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]!);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function randomBase64Url(size: number, cryptoImpl: Crypto = globalThis.crypto): string {
  const bytes = new Uint8Array(size);
  cryptoImpl.getRandomValues(bytes);
  return base64UrlEncode(bytes);
}

export function generateCodeVerifier(cryptoImpl: Crypto = globalThis.crypto): string {
  return randomBase64Url(VERIFIER_BYTES, cryptoImpl);
}

export function generateOAuthState(cryptoImpl: Crypto = globalThis.crypto): string {
  return randomBase64Url(STATE_BYTES, cryptoImpl);
}

export async function generateCodeChallenge(
  verifier: string,
  subtle: SubtleCrypto = globalThis.crypto.subtle,
): Promise<string> {
  const digest = await subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64UrlEncode(new Uint8Array(digest));
}

export function storePkceSession(
  session: PkceSession,
  storage?: StorageLike | null,
): boolean {
  const target = storage === undefined ? browserSessionStorage() : storage;
  if (!target) return false;
  try {
    target.setItem(PKCE_STORAGE_KEY, JSON.stringify(session));
    return true;
  } catch {
    return false;
  }
}

export function readPkceSession(
  storage?: StorageLike | null,
): PkceSession | null {
  const source = storage === undefined ? browserSessionStorage() : storage;
  if (!source) return null;
  try {
    const raw = source.getItem(PKCE_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PkceSession>;
    if (!parsed.verifier?.trim() || !parsed.state?.trim()) return null;
    return {
      verifier: parsed.verifier.trim(),
      state: parsed.state.trim(),
      next: safeNextPath(parsed.next),
    };
  } catch {
    return null;
  }
}

export function clearPkceSession(
  storage?: StorageLike | null,
): void {
  const target = storage === undefined ? browserSessionStorage() : storage;
  if (!target) return;
  try {
    target.removeItem(PKCE_STORAGE_KEY);
  } catch {
    // Ignore.
  }
}

export function buildAuthorizeUrl(
  config: CognitoPublicConfig,
  params: { challenge: string; state: string },
): string {
  const query = new URLSearchParams({
    client_id: config.clientId,
    response_type: "code",
    scope: "openid email profile",
    redirect_uri: callbackRedirectUri(config.appUrl),
    code_challenge: params.challenge,
    code_challenge_method: "S256",
    state: params.state,
  });
  return `https://${config.domain}/oauth2/authorize?${query.toString()}`;
}

export function buildLogoutUrl(config: CognitoPublicConfig): string {
  const query = new URLSearchParams({
    client_id: config.clientId,
    logout_uri: postLogoutUri(config.appUrl),
  });
  return `https://${config.domain}/logout?${query.toString()}`;
}

export async function prepareHostedUiLogin(options?: {
  next?: string;
  config?: CognitoPublicConfig | null;
  env?: EnvLike;
  sessionStorage?: StorageLike | null;
  crypto?: Crypto;
}): Promise<{ url: string; verifier: string; state: string; next: string }> {
  const config = options?.config ?? readCognitoConfig(options?.env ?? publicCognitoEnv());
  if (!config) {
    throw new Error("Cognito is not configured");
  }
  const cryptoImpl = options?.crypto ?? globalThis.crypto;
  const verifier = generateCodeVerifier(cryptoImpl);
  const challenge = await generateCodeChallenge(verifier, cryptoImpl.subtle);
  const state = generateOAuthState(cryptoImpl);
  const next = safeNextPath(options?.next);
  if (!storePkceSession({ verifier, state, next }, options?.sessionStorage)) {
    throw new Error("Unable to store the sign-in session. Check browser storage settings.");
  }
  const url = buildAuthorizeUrl(config, { challenge, state });
  return { url, verifier, state, next };
}

export async function beginHostedUiLogin(options?: { next?: string }): Promise<void> {
  const prepared = await prepareHostedUiLogin({ next: options?.next });
  if (typeof window !== "undefined") {
    window.location.assign(prepared.url);
  }
}

export function logoutFromApp(options?: {
  tokenStorage?: StorageLike | null;
  pkceStorage?: StorageLike | null;
  env?: EnvLike;
}): { cognitoLogoutUrl: string | null } {
  clearAuthToken(options?.tokenStorage);
  clearPkceSession(options?.pkceStorage);
  const config = readCognitoConfig(options?.env ?? publicCognitoEnv());
  return { cognitoLogoutUrl: config ? buildLogoutUrl(config) : null };
}

export function parseCallbackSearch(
  search: string | URLSearchParams,
): { ok: true; code: string; state: string | null } | { ok: false; error: string } {
  const params = typeof search === "string" ? new URLSearchParams(search.startsWith("?") ? search.slice(1) : search) : search;
  const denied = params.get("error")?.trim();
  if (denied) {
    return {
      ok: false,
      error: params.get("error_description")?.trim() || denied.replace(/_/g, " "),
    };
  }
  const code = params.get("code")?.trim();
  if (!code) {
    return { ok: false, error: "Missing authorization code. Try signing in again." };
  }
  return { ok: true, code, state: params.get("state")?.trim() || null };
}

export async function exchangeAuthorizationCode(options: {
  config: CognitoPublicConfig;
  code: string;
  verifier: string;
  fetchImpl?: typeof fetch;
}): Promise<{ idToken: string }> {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: options.config.clientId,
    code: options.code,
    redirect_uri: callbackRedirectUri(options.config.appUrl),
    code_verifier: options.verifier,
  });
  const fetchImpl = options.fetchImpl ?? fetch;
  const res = await fetchImpl(`https://${options.config.domain}/oauth2/token`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });
  const payload = (await res.json().catch(() => ({}))) as {
    id_token?: unknown;
    error?: unknown;
    error_description?: unknown;
  };
  if (!res.ok) {
    const detail =
      (typeof payload.error_description === "string" && payload.error_description) ||
      (typeof payload.error === "string" && payload.error) ||
      `Token exchange HTTP ${res.status}`;
    throw new Error(detail);
  }
  const idToken = typeof payload.id_token === "string" ? payload.id_token.trim() : "";
  if (!idToken) {
    throw new Error("Token response missing id_token");
  }
  return { idToken };
}

export async function completeHostedUiCallback(options: {
  search: string | URLSearchParams;
  config?: CognitoPublicConfig | null;
  env?: EnvLike;
  tokenStorage?: StorageLike | null;
  pkceStorage?: StorageLike | null;
  fetchImpl?: typeof fetch;
}): Promise<{ ok: true; next: string; profile: AuthProfile | null } | { ok: false; error: string }> {
  const pkceStorage =
    options.pkceStorage !== undefined ? options.pkceStorage : browserSessionStorage();
  // Leaving tokenStorage undefined delegates to the canonical auth helper,
  // which writes to tab-scoped sessionStorage. A supplied store remains
  // available for deterministic callers and tests.
  const tokenStorage = options.tokenStorage;
  const parsed = parseCallbackSearch(options.search);
  const session = readPkceSession(pkceStorage);
  const finishError = (error: string): { ok: false; error: string } => {
    clearPkceSession(pkceStorage);
    return { ok: false, error };
  };

  if (!session?.verifier) {
    return finishError("Sign-in session expired. Try signing in again.");
  }
  const callbackParams =
    typeof options.search === "string"
      ? new URLSearchParams(options.search.startsWith("?") ? options.search.slice(1) : options.search)
      : options.search;
  const callbackState = callbackParams.get("state")?.trim() || null;
  if (!callbackState || callbackState !== session.state) {
    // Callback không hợp lệ không được phép phá session đăng nhập đang diễn ra.
    return { ok: false, error: "Invalid sign-in state. Try signing in again." };
  }
  if (!parsed.ok) return finishError(parsed.error);

  // Claim PKCE atomically trước network call để cùng code không bị đổi token hai lần.
  clearPkceSession(pkceStorage);

  const config = options.config ?? readCognitoConfig(options.env ?? publicCognitoEnv());
  if (!config) {
    return finishError("Cognito is not configured.");
  }

  let idToken: string;
  try {
    ({ idToken } = await exchangeAuthorizationCode({
      config,
      code: parsed.code,
      verifier: session.verifier,
      fetchImpl: options.fetchImpl,
    }));
  } catch (err) {
    return finishError(err instanceof Error ? err.message : "Token exchange failed");
  }

  if (!writeAuthToken(idToken, tokenStorage)) {
    return { ok: false, error: "Unable to store the sign-in token. Check browser storage settings." };
  }

  try {
    const profile = await fetchAuthMe({
      token: idToken,
      fetchImpl: options.fetchImpl,
    });
    return { ok: true, next: session.next, profile };
  } catch (err) {
    if (err instanceof AuthApiError && err.authRequired) {
      clearAuthToken(tokenStorage);
      return { ok: false, error: "Signed in, but the API rejected the ID token." };
    }
    return { ok: true, next: session.next, profile: null };
  }
}
