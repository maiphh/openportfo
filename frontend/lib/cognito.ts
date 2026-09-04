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
  // Prefer the live page origin so redirect_uri scheme/host always match the
  // tab the user is on (avoids Cognito redirect_mismatch when a stale
  // NEXT_PUBLIC_APP_URL bake disagrees with https:// EB).
  let appUrl = "";
  if (typeof window !== "undefined") {
    appUrl = normalizeAppUrl(window.location.origin);
  }
  if (!appUrl) {
    appUrl = normalizeAppUrl(env.NEXT_PUBLIC_APP_URL || "");
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

/**
 * Pure SHA-256 for PKCE S256 when SubtleCrypto is unavailable.
 * Browsers expose `crypto.subtle` only in secure contexts (HTTPS / localhost);
 * single-EB lab demos on plain `http://*.elasticbeanstalk.com` need this path.
 */
export function sha256Bytes(message: Uint8Array): Uint8Array {
  const K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);
  const bitLen = message.length * 8;
  const withPad = new Uint8Array(((message.length + 9 + 63) & ~63));
  withPad.set(message);
  withPad[message.length] = 0x80;
  const view = new DataView(withPad.buffer);
  view.setUint32(withPad.length - 4, bitLen >>> 0, false);
  // High 32 bits stay 0 for messages under 512MB (PKCE verifiers are tiny).

  let h0 = 0x6a09e667;
  let h1 = 0xbb67ae85;
  let h2 = 0x3c6ef372;
  let h3 = 0xa54ff53a;
  let h4 = 0x510e527f;
  let h5 = 0x9b05688c;
  let h6 = 0x1f83d9ab;
  let h7 = 0x5be0cd19;
  const w = new Uint32Array(64);

  for (let i = 0; i < withPad.length; i += 64) {
    for (let t = 0; t < 16; t += 1) w[t] = view.getUint32(i + t * 4, false);
    for (let t = 16; t < 64; t += 1) {
      const s0 = ((w[t - 15]! >>> 7) | (w[t - 15]! << 25)) ^ ((w[t - 15]! >>> 18) | (w[t - 15]! << 14)) ^ (w[t - 15]! >>> 3);
      const s1 = ((w[t - 2]! >>> 17) | (w[t - 2]! << 15)) ^ ((w[t - 2]! >>> 19) | (w[t - 2]! << 13)) ^ (w[t - 2]! >>> 10);
      w[t] = (w[t - 16]! + s0 + w[t - 7]! + s1) >>> 0;
    }
    let a = h0;
    let b = h1;
    let c = h2;
    let d = h3;
    let e = h4;
    let f = h5;
    let g = h6;
    let h = h7;
    for (let t = 0; t < 64; t += 1) {
      const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + S1 + ch + K[t]! + w[t]!) >>> 0;
      const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }
    h0 = (h0 + a) >>> 0;
    h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0;
    h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0;
    h5 = (h5 + f) >>> 0;
    h6 = (h6 + g) >>> 0;
    h7 = (h7 + h) >>> 0;
  }

  const out = new Uint8Array(32);
  const outView = new DataView(out.buffer);
  outView.setUint32(0, h0, false);
  outView.setUint32(4, h1, false);
  outView.setUint32(8, h2, false);
  outView.setUint32(12, h3, false);
  outView.setUint32(16, h4, false);
  outView.setUint32(20, h5, false);
  outView.setUint32(24, h6, false);
  outView.setUint32(28, h7, false);
  return out;
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
  subtle?: SubtleCrypto | null,
): Promise<string> {
  const bytes = new TextEncoder().encode(verifier);
  const subtleImpl = subtle === undefined ? globalThis.crypto?.subtle : subtle;
  if (subtleImpl && typeof subtleImpl.digest === "function") {
    const digest = await subtleImpl.digest("SHA-256", bytes);
    return base64UrlEncode(new Uint8Array(digest));
  }
  return base64UrlEncode(sha256Bytes(bytes));
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
  const challenge = await generateCodeChallenge(verifier, cryptoImpl?.subtle ?? null);
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
