import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import {
  AUTH_TOKEN_STORAGE_KEY,
  AUTH_CHANGE_EVENT,
  AuthApiError,
  clearAuthToken,
  fetchAuthMe,
  isAuthTokenStorageKey,
  profileDisplayName,
  readAuthToken,
  writeAuthToken,
} from "@/lib/auth";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("auth token storage", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  afterEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it("stores a trimmed ID token in sessionStorage", () => {
    expect(writeAuthToken("  eyJid.token  ")).toBe(true);
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe("eyJid.token");
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(readAuthToken()).toBe("eyJid.token");
  });

  it("strips a Bearer prefix before persisting", () => {
    writeAuthToken("Bearer abc.def");
    expect(readAuthToken()).toBe("abc.def");
  });

  it("does not persist an empty token", () => {
    expect(writeAuthToken("   ")).toBe(false);
    expect(readAuthToken()).toBeNull();
  });

  it("rejects and removes a token persisted outside sessionStorage", () => {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, " persistent.jwt ");

    expect(readAuthToken()).toBeNull();
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("reads an explicitly supplied canonical store without inferring another store", () => {
    const supplied = {
      getItem: (key: string) => key === AUTH_TOKEN_STORAGE_KEY ? "supplied-only" : null,
    };
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "browser-session");
    expect(readAuthToken(supplied)).toBe("supplied-only");
  });

  it("prefers the session token and removes a persistent local copy", () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "session.jwt");
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "persistent.jwt");

    expect(readAuthToken()).toBe("session.jwt");
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("clears the stored token from both browser stores", () => {
    writeAuthToken("session.jwt");
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "persistent.jwt");
    clearAuthToken();
    expect(readAuthToken()).toBeNull();
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("clears canonical auth storage and emits the same-document auth event", () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "new-session");
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "new-local");
    const listener = vi.fn();
    window.addEventListener(AUTH_CHANGE_EVENT, listener);
    clearAuthToken();
    window.removeEventListener(AUTH_CHANGE_EVENT, listener);
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("recognizes only the canonical auth storage event", () => {
    expect(isAuthTokenStorageKey(AUTH_TOKEN_STORAGE_KEY)).toBe(true);
    expect(isAuthTokenStorageKey("legacy.accessToken")).toBe(false);
    expect(isAuthTokenStorageKey("openportfo.other")).toBe(false);
    expect(isAuthTokenStorageKey(null)).toBe(false);
  });

  it("fails safely when a supplied storage is unavailable", () => {
    const unavailable = {
      setItem: () => {
        throw new Error("Storage disabled");
      },
      removeItem: () => {
        throw new Error("Storage disabled");
      },
      getItem: () => {
        throw new Error("Storage disabled");
      },
    };

    expect(writeAuthToken("id.jwt", unavailable)).toBe(false);
    expect(readAuthToken(unavailable)).toBeNull();
    expect(() => clearAuthToken(unavailable)).not.toThrow();
  });
});

describe("fetchAuthMe", () => {
  const fetchImpl = vi.fn();

  beforeEach(() => {
    fetchImpl.mockReset();
  });

  it("returns name and email from GET /api/auth/me", async () => {
    fetchImpl.mockResolvedValue(
      jsonResponse({ userId: "sub-1", email: "ada@example.com", name: "Ada", role: "user" }),
    );

    const profile = await fetchAuthMe({ token: "id.token", fetchImpl: fetchImpl as unknown as typeof fetch });

    expect(profile).toEqual({
      userId: "sub-1",
      email: "ada@example.com",
      name: "Ada",
      role: "user",
    });
    expect(fetchImpl).toHaveBeenCalledWith(
      `${apiBase()}/api/auth/me`,
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({ Authorization: "Bearer id.token" }),
      }),
    );
  });

  it("marks 401 as authRequired", async () => {
    fetchImpl.mockResolvedValue(jsonResponse({ detail: "Unauthorized" }, 401));

    await expect(
      fetchAuthMe({ token: "bad", fetchImpl: fetchImpl as unknown as typeof fetch }),
    ).rejects.toMatchObject({ name: "AuthApiError", status: 401, authRequired: true });
    expect(AuthApiError).toBeTypeOf("function");
  });

  it("aborts a profile request that exceeds the timeout", async () => {
    fetchImpl.mockImplementation((_url: string, init?: RequestInit) =>
      new Promise((_resolve, reject) => {
        init?.signal?.addEventListener(
          "abort",
          () => reject(init.signal?.reason ?? new DOMException("Aborted", "AbortError")),
          { once: true },
        );
      }),
    );

    await expect(
      fetchAuthMe({
        token: "id.token",
        fetchImpl: fetchImpl as unknown as typeof fetch,
        timeoutMs: 1,
      }),
    ).rejects.toMatchObject({ name: "TimeoutError" });
  });
});

describe("profileDisplayName", () => {
  it("prefers name, then email", () => {
    expect(profileDisplayName({ userId: "1", email: "a@b.c", name: "Ada" })).toBe("Ada");
    expect(profileDisplayName({ userId: "1", email: "a@b.c", name: null })).toBe("a@b.c");
  });
});
