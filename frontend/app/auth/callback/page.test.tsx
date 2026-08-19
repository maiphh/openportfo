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

const { completeHostedUiCallback, isCognitoConfigured } = await import("@/lib/cognito");
const completeMock = vi.mocked(completeHostedUiCallback);
const configuredMock = vi.mocked(isCognitoConfigured);

describe("AuthCallbackPage", () => {
  beforeEach(() => {
    completeMock.mockReset();
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
});
