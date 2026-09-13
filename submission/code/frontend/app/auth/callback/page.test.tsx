import { StrictMode } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AuthCallbackPage from "@/app/auth/callback/page";

vi.mock("@/lib/cognito", async () => {
  const actual = await vi.importActual<typeof import("@/lib/cognito")>("@/lib/cognito");
  return {
    ...actual,
    completeHostedUiCallback: vi.fn(),
    beginHostedUiLogin: vi.fn(),
    isCognitoConfigured: vi.fn(() => true),
  };
});

const { beginHostedUiLogin, completeHostedUiCallback, isCognitoConfigured } = await import("@/lib/cognito");
const beginLoginMock = vi.mocked(beginHostedUiLogin);
const completeMock = vi.mocked(completeHostedUiCallback);
const configuredMock = vi.mocked(isCognitoConfigured);

describe("AuthCallbackPage", () => {
  beforeEach(() => {
    completeMock.mockReset();
    beginLoginMock.mockReset();
    configuredMock.mockReturnValue(true);
    window.history.replaceState({}, "", "/auth/callback/?error=access_denied");
  });

  afterEach(() => {
    cleanup();
  });

  it("shows the callback error and a retry Sign in action", async () => {
    completeMock.mockResolvedValue({ ok: false, error: "User cancelled sign-in" });

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(screen.getByText("Sign-in failed")).toBeInTheDocument();
    });
    expect(screen.getByText("User cancelled sign-in")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry Sign in" })).toBeInTheDocument();
    expect(screen.queryByText("Signing you in…")).not.toBeInTheDocument();
  });

  it("exchanges the authorization code only once in React Strict Mode", async () => {
    completeMock.mockResolvedValue({ ok: false, error: "Test callback stopped" });

    render(
      <StrictMode>
        <AuthCallbackPage />
      </StrictMode>,
    );

    await waitFor(() => {
      expect(screen.getByText("Test callback stopped")).toBeInTheDocument();
    });
    expect(completeMock).toHaveBeenCalledTimes(1);
  });

  it("shows an unexpected callback failure instead of loading forever", async () => {
    completeMock.mockRejectedValue(new Error("Unexpected callback failure"));

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(screen.getByText("Unexpected callback failure")).toBeInTheDocument();
    });
  });

  it("shows an error when retry sign-in cannot start", async () => {
    completeMock.mockResolvedValue({ ok: false, error: "Original callback failure" });
    beginLoginMock.mockRejectedValue(new Error("Browser storage is disabled"));
    render(<AuthCallbackPage />);

    const retry = await screen.findByRole("button", { name: "Retry Sign in" });
    retry.click();

    expect(await screen.findByText("Browser storage is disabled")).toBeInTheDocument();
  });
});
