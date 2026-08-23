import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  token: "token-a" as string | null,
  readAuthToken: vi.fn(),
  clearAuthToken: vi.fn(),
  fetchAuthMe: vi.fn(),
  beginHostedUiLogin: vi.fn(),
  logoutFromApp: vi.fn(),
  isCognitoConfigured: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  AUTH_CHANGE_EVENT: "openportfo:auth-change",
  AuthApiError: class AuthApiError extends Error {
    status: number;
    authRequired: boolean;
    constructor(status: number, message = "auth error") {
      super(message);
      this.status = status;
      this.authRequired = status === 401 || status === 403;
    }
  },
  clearAuthToken: mocks.clearAuthToken,
  fetchAuthMe: mocks.fetchAuthMe,
  isAuthTokenStorageKey: (key: string | null) => key === "openportfo.accessToken",
  readAuthToken: mocks.readAuthToken,
}));

vi.mock("@/lib/cognito", () => ({
  beginHostedUiLogin: mocks.beginHostedUiLogin,
  isCognitoConfigured: mocks.isCognitoConfigured,
  logoutFromApp: mocks.logoutFromApp,
}));

import { AuthApiError } from "@/lib/auth";
import { useAuthProfile } from "@/lib/use-auth-profile";

describe("useAuthProfile", () => {
  beforeEach(() => {
    mocks.token = "token-a";
    mocks.readAuthToken.mockReset().mockImplementation(() => mocks.token);
    mocks.clearAuthToken.mockReset();
    mocks.fetchAuthMe.mockReset().mockResolvedValue({ userId: "alice", email: "alice@example.com", name: "Alice" });
    mocks.beginHostedUiLogin.mockReset().mockResolvedValue(undefined);
    mocks.logoutFromApp.mockReset().mockReturnValue({ cognitoLogoutUrl: null });
    mocks.isCognitoConfigured.mockReset().mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("loads a profile and aborts the stale request on auth-change synchronization", async () => {
    let resolveFirst: ((value: unknown) => void) | undefined;
    const first = new Promise((resolve) => { resolveFirst = resolve; });
    mocks.fetchAuthMe.mockReturnValueOnce(first).mockResolvedValueOnce({ userId: "bob", email: "bob@example.com", name: "Bob" });
    const { result } = renderHook(() => useAuthProfile());
    await waitFor(() => expect(mocks.fetchAuthMe).toHaveBeenCalledTimes(1));
    const firstSignal = mocks.fetchAuthMe.mock.calls[0]?.[0]?.signal as AbortSignal;
    mocks.token = "token-b";
    act(() => window.dispatchEvent(new Event("openportfo:auth-change")));
    await waitFor(() => expect(firstSignal.aborted).toBe(true));
    await waitFor(() => expect(result.current.profile?.userId).toBe("bob"));
    resolveFirst?.({ userId: "alice", email: "alice@example.com", name: "Alice" });
  });

  it("clears invalid auth on 401/403 and exposes non-auth errors", async () => {
    mocks.fetchAuthMe.mockRejectedValueOnce(new AuthApiError(401, "unauthorized"));
    const { result } = renderHook(() => useAuthProfile());
    await waitFor(() => expect(mocks.clearAuthToken).toHaveBeenCalledTimes(1));
    expect(result.current.token).toBeNull();
    expect(result.current.profile).toBeNull();

    mocks.token = "token-c";
    mocks.fetchAuthMe.mockRejectedValueOnce(new Error("offline"));
    act(() => window.dispatchEvent(new Event("openportfo:auth-change")));
    await waitFor(() => expect(result.current.error).toBe("offline"));
  });

  it("synchronizes canonical storage events and focus without duplicating same tokens", async () => {
    const { result } = renderHook(() => useAuthProfile());
    await waitFor(() => expect(result.current.profile?.userId).toBe("alice"));
    const calls = mocks.fetchAuthMe.mock.calls.length;
    act(() => window.dispatchEvent(new StorageEvent("storage", { key: "openportfo.other" })));
    act(() => window.dispatchEvent(new Event("focus")));
    expect(mocks.fetchAuthMe).toHaveBeenCalledTimes(calls);
    mocks.token = "token-b";
    act(() => window.dispatchEvent(new StorageEvent("storage", { key: "openportfo.accessToken" })));
    await waitFor(() => expect(mocks.fetchAuthMe.mock.calls.length).toBeGreaterThan(calls));
  });

  it("owns sign-in errors and clears local state immediately on sign-out", async () => {
    const { result } = renderHook(() => useAuthProfile());
    await waitFor(() => expect(result.current.profile?.userId).toBe("alice"));
    mocks.beginHostedUiLogin.mockRejectedValueOnce(new Error("Cognito unavailable"));
    await act(async () => { await result.current.signIn("/portfolio"); });
    expect(result.current.error).toBe("Cognito unavailable");
    act(() => result.current.signOut());
    expect(mocks.logoutFromApp).toHaveBeenCalledTimes(1);
    expect(result.current.token).toBeNull();
    expect(result.current.profile).toBeNull();
  });
});
