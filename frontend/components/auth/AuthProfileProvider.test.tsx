import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { useContext } from "react";
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

import AuthProfileProvider from "@/components/auth/AuthProfileProvider";
import { AuthProfileContext } from "@/lib/auth-profile-context";
import { AuthApiError } from "@/lib/auth";

const alice = { userId: "alice", email: "alice@example.com", name: "Alice", role: "user" as const };
const bob = { userId: "bob", email: "bob@example.com", name: "Bob", role: "admin" as const };

describe("AuthProfileProvider", () => {
  beforeEach(() => {
    mocks.token = "token-a";
    mocks.readAuthToken.mockReset().mockImplementation(() => mocks.token);
    mocks.clearAuthToken.mockReset();
    mocks.fetchAuthMe.mockReset().mockResolvedValue(alice);
    mocks.beginHostedUiLogin.mockReset().mockResolvedValue(undefined);
    mocks.logoutFromApp.mockReset().mockReturnValue({ cognitoLogoutUrl: null });
    mocks.isCognitoConfigured.mockReset().mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shares one profile request and supports a forced same-token reload/replace", async () => {
    const { result } = renderHook(() => useContextValue(), { wrapper: AuthProfileProvider });
    await waitFor(() => expect(result.current?.profile?.userId).toBe("alice"));
    expect(mocks.fetchAuthMe).toHaveBeenCalledTimes(1);

    mocks.fetchAuthMe.mockResolvedValueOnce(bob);
    await act(async () => { await result.current?.reloadProfile?.(); });
    expect(mocks.fetchAuthMe).toHaveBeenCalledTimes(2);
    expect(result.current?.profile?.userId).toBe("bob");

    act(() => result.current?.replaceProfile?.({ ...alice, name: "Alice Updated" }));
    expect(result.current?.profile?.name).toBe("Alice Updated");
  });

  it("supersedes stale requests when the bearer token changes", async () => {
    let resolveFirst: ((value: typeof alice) => void) | undefined;
    const first = new Promise<typeof alice>((resolve) => { resolveFirst = resolve; });
    mocks.fetchAuthMe.mockReturnValueOnce(first).mockResolvedValueOnce(bob);
    const { result } = renderHook(() => useContextValue(), { wrapper: AuthProfileProvider });
    await waitFor(() => expect(mocks.fetchAuthMe).toHaveBeenCalledTimes(1));
    const firstSignal = mocks.fetchAuthMe.mock.calls[0]?.[0]?.signal as AbortSignal;
    mocks.token = "token-b";
    act(() => window.dispatchEvent(new Event("openportfo:auth-change")));
    await waitFor(() => expect(firstSignal.aborted).toBe(true));
    await waitFor(() => expect(result.current?.profile?.userId).toBe("bob"));
    resolveFirst?.(alice);
  });

  it("clears the shared profile and token on an auth-required response", async () => {
    mocks.fetchAuthMe.mockRejectedValueOnce(new AuthApiError(401, "unauthorized"));
    const { result } = renderHook(() => useContextValue(), { wrapper: AuthProfileProvider });
    await waitFor(() => expect(mocks.clearAuthToken).toHaveBeenCalledTimes(1));
    expect(result.current?.token).toBeNull();
    expect(result.current?.profile).toBeNull();
    expect(result.current?.error).toBeNull();
  });
});

function useContextValue() {
  // Kept in a helper so every test exercises the actual provider context.
  return useContext(AuthProfileContext);
}
