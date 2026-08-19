import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import {
  PKCE_STORAGE_KEY,
  buildAuthorizeUrl,
  buildLogoutUrl,
  callbackRedirectUri,
  completeHostedUiCallback,
  generateCodeChallenge,
  generateCodeVerifier,
  isCognitoConfigured,
  parseCallbackSearch,
  prepareHostedUiLogin,
  readCognitoConfig,
  safeNextPath,
  storePkceSession,
} from "@/lib/cognito";

const CONFIG = {
  domain: "openportfo.auth.us-east-1.amazoncognito.com",
  clientId: "client-123",
  region: "us-east-1",
  appUrl: "http://localhost:3000",
};

function memoryStorage(initial: Record<string, string> = {}): Storage {
  const map = new Map(Object.entries(initial));
  return {
    get length() {
      return map.size;
    },
    clear: () => map.clear(),
    getItem: (key: string) => map.get(key) ?? null,
    key: (index: number) => [...map.keys()][index] ?? null,
    removeItem: (key: string) => {
      map.delete(key);
    },
    setItem: (key: string, value: string) => {
      map.set(key, value);
    },
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("Cognito public config", () => {
  it("is unconfigured when domain or client id is missing", () => {
    expect(isCognitoConfigured({})).toBe(false);
    expect(isCognitoConfigured({ NEXT_PUBLIC_COGNITO_DOMAIN: CONFIG.domain })).toBe(false);
    expect(isCognitoConfigured({ NEXT_PUBLIC_COGNITO_CLIENT_ID: CONFIG.clientId })).toBe(false);
  });

  it("reads Hosted UI env and callback origin", () => {
    expect(
      isCognitoConfigured({
        NEXT_PUBLIC_COGNITO_DOMAIN: `https://${CONFIG.domain}/`,
        NEXT_PUBLIC_COGNITO_CLIENT_ID: CONFIG.clientId,
      }),
    ).toBe(true);

    expect(
      readCognitoConfig({
        NEXT_PUBLIC_COGNITO_DOMAIN: CONFIG.domain,
        NEXT_PUBLIC_COGNITO_CLIENT_ID: CONFIG.clientId,
        NEXT_PUBLIC_COGNITO_REGION: "us-east-1",
        NEXT_PUBLIC_APP_URL: "http://localhost:3000/",
      }),
    ).toEqual(CONFIG);
  });

  it("builds trailing-slash callback and logout URIs", () => {
    expect(callbackRedirectUri(CONFIG.appUrl)).toBe("http://localhost:3000/auth/callback/");
    expect(buildLogoutUrl(CONFIG)).toBe(
      "https://openportfo.auth.us-east-1.amazoncognito.com/logout?client_id=client-123&logout_uri=http%3A%2F%2Flocalhost%3A3000%2F",
    );
  });
});

describe("PKCE helper", () => {
  it("generates an unreserved verifier of RFC 7636 length", () => {
    const verifier = generateCodeVerifier();
    expect(verifier.length).toBeGreaterThanOrEqual(43);
    expect(verifier.length).toBeLessThanOrEqual(128);
    expect(verifier).toMatch(/^[A-Za-z0-9\-._~]+$/);
  });

  it("matches the RFC 7636 S256 challenge test vector", async () => {
    const verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
    await expect(generateCodeChallenge(verifier)).resolves.toBe("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
  });

  it("never puts the verifier in the authorize URL", async () => {
    const session = memoryStorage();
    const prepared = await prepareHostedUiLogin({
      config: CONFIG,
      next: "/portfolio/",
      sessionStorage: session,
    });

    expect(prepared.url).toContain("/oauth2/authorize?");
    expect(prepared.url).toContain("response_type=code");
    expect(prepared.url).toContain("code_challenge_method=S256");
    expect(prepared.url).toContain("scope=openid+email+profile");
    expect(prepared.url).toContain(encodeURIComponent("http://localhost:3000/auth/callback/"));
    expect(prepared.url).not.toContain("code_verifier");
    expect(prepared.url).not.toContain(prepared.verifier);
    expect(session.getItem(PKCE_STORAGE_KEY)).toContain(prepared.verifier);
    expect(JSON.parse(session.getItem(PKCE_STORAGE_KEY) || "{}").next).toBe("/portfolio/");
  });

  it("buildAuthorizeUrl stays PKCE-only", () => {
    const url = buildAuthorizeUrl(CONFIG, { challenge: "abc", state: "st" });
    expect(url).not.toMatch(/code_verifier/);
  });
});

describe("callback parsing", () => {
  it("surfaces Hosted UI denial", () => {
    expect(parseCallbackSearch("error=access_denied&error_description=User+denied")).toEqual({
      ok: false,
      error: "User denied",
    });
  });

  it("requires a code", () => {
    expect(parseCallbackSearch("")).toMatchObject({ ok: false, error: expect.stringMatching(/code/i) });
  });

  it("rejects open redirects in next", () => {
    expect(safeNextPath("https://evil.test")).toBe("/");
    expect(safeNextPath("//evil.test")).toBe("/");
    expect(safeNextPath("/portfolio/")).toBe("/portfolio/");
  });
});

describe("completeHostedUiCallback", () => {
  const tokenStorage = memoryStorage();
  const pkceStorage = memoryStorage();
  const fetchImpl = vi.fn();

  beforeEach(() => {
    tokenStorage.clear();
    pkceStorage.clear();
    fetchImpl.mockReset();
    storePkceSession({ verifier: "session-verifier", state: "abc", next: "/portfolio/" }, pkceStorage);
  });

  afterEach(() => {
    tokenStorage.clear();
    pkceStorage.clear();
  });

  it("does not store a token when Cognito returns an error", async () => {
    const result = await completeHostedUiCallback({
      search: "error=access_denied&error_description=Nope",
      config: CONFIG,
      tokenStorage,
      pkceStorage,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    expect(result).toEqual({ ok: false, error: "Nope" });
    expect(tokenStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(pkceStorage.getItem(PKCE_STORAGE_KEY)).toBeNull();
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("ignores a verifier in the query and fails if session PKCE is missing", async () => {
    pkceStorage.clear();
    const result = await completeHostedUiCallback({
      search: "code=auth-code&code_verifier=attacker-verifier",
      config: CONFIG,
      tokenStorage,
      pkceStorage,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    expect(result.ok).toBe(false);
    expect(tokenStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("does not store a token when the token endpoint fails", async () => {
    fetchImpl.mockResolvedValue(jsonResponse({ error: "invalid_grant", error_description: "Bad code" }, 400));

    const result = await completeHostedUiCallback({
      search: "code=auth-code&state=abc",
      config: CONFIG,
      tokenStorage,
      pkceStorage,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    expect(result).toEqual({ ok: false, error: "Bad code" });
    expect(tokenStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    const [url, init] = fetchImpl.mock.calls[0] ?? [];
    expect(url).toBe("https://openportfo.auth.us-east-1.amazoncognito.com/oauth2/token");
    expect(String((init as RequestInit).body)).toContain("code_verifier=session-verifier");
    expect(String((init as RequestInit).body)).not.toContain("attacker");
  });

  it("does not store access_token when id_token is missing", async () => {
    fetchImpl.mockResolvedValue(jsonResponse({ access_token: "not-an-id-token" }));

    const result = await completeHostedUiCallback({
      search: "code=auth-code&state=abc",
      config: CONFIG,
      tokenStorage,
      pkceStorage,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    expect(result.ok).toBe(false);
    expect(tokenStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("stores the ID token then loads /api/auth/me", async () => {
    fetchImpl
      .mockResolvedValueOnce(jsonResponse({ id_token: "  id.jwt  ", access_token: "access.jwt" }))
      .mockResolvedValueOnce(jsonResponse({ userId: "sub-1", email: "ada@example.com", name: "Ada" }));

    const result = await completeHostedUiCallback({
      search: "code=auth-code&state=abc",
      config: CONFIG,
      tokenStorage,
      pkceStorage,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    expect(result).toMatchObject({ ok: true, next: "/portfolio/" });
    expect(tokenStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe("id.jwt");
    expect(pkceStorage.getItem(PKCE_STORAGE_KEY)).toBeNull();
    expect(String(fetchImpl.mock.calls[1]?.[0])).toMatch(/\/api\/auth\/me$/);
  });

  it("clears the ID token when /api/auth/me returns 401", async () => {
    fetchImpl
      .mockResolvedValueOnce(jsonResponse({ id_token: "id.jwt" }))
      .mockResolvedValueOnce(jsonResponse({ detail: "Unauthorized" }, 401));

    const result = await completeHostedUiCallback({
      search: "code=auth-code&state=abc",
      config: CONFIG,
      tokenStorage,
      pkceStorage,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    expect(result.ok).toBe(false);
    expect(tokenStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
  });
});
