import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import {
  AUTH_TOKEN_STORAGE_KEY,
  AuthApiError,
  clearAuthToken,
  fetchAuthMe,
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
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("stores a trimmed ID token under artryx.accessToken", () => {
    writeAuthToken("  eyJid.token  ");
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe("eyJid.token");
    expect(readAuthToken()).toBe("eyJid.token");
  });

  it("strips a Bearer prefix before persisting", () => {
    writeAuthToken("Bearer abc.def");
    expect(readAuthToken()).toBe("abc.def");
  });

  it("does not persist an empty token", () => {
    writeAuthToken("   ");
    expect(readAuthToken()).toBeNull();
  });

  it("clears the stored token", () => {
    writeAuthToken("keep");
    clearAuthToken();
    expect(readAuthToken()).toBeNull();
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
