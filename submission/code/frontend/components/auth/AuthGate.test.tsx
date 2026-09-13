import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AuthGate from "@/components/auth/AuthGate";

vi.mock("@/lib/cognito", async () => {
  const actual = await vi.importActual<typeof import("@/lib/cognito")>("@/lib/cognito");
  return {
    ...actual,
    isCognitoConfigured: vi.fn(),
    beginHostedUiLogin: vi.fn(),
  };
});

const { beginHostedUiLogin, isCognitoConfigured } = await import("@/lib/cognito");
const isCognitoConfiguredMock = vi.mocked(isCognitoConfigured);
const beginHostedUiLoginMock = vi.mocked(beginHostedUiLogin);

afterEach(() => {
  cleanup();
  isCognitoConfiguredMock.mockReset();
  beginHostedUiLoginMock.mockReset();
});

describe("AuthGate", () => {
  it("keeps the paste fallback when Cognito env is missing", () => {
    isCognitoConfiguredMock.mockReturnValue(false);
    render(
      <AuthGate title="Portfolio" description="Paste a temporary token." onTokenSaved={() => undefined} />,
    );

    expect(screen.getByPlaceholderText(/fake:userId/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue with token" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("hides paste and offers Hosted UI Sign in when Cognito is configured", () => {
    isCognitoConfiguredMock.mockReturnValue(true);
    render(
      <AuthGate
        title="Portfolio"
        description="unused"
        nextPath="/portfolio/"
        onTokenSaved={() => undefined}
      />,
    );

    expect(screen.queryByPlaceholderText(/fake:userId/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows an error when Cognito sign-in cannot start", async () => {
    isCognitoConfiguredMock.mockReturnValue(true);
    beginHostedUiLoginMock.mockRejectedValue(new Error("Browser storage is disabled"));
    render(
      <AuthGate title="Portfolio" description="unused" onTokenSaved={() => undefined} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Browser storage is disabled")).toBeInTheDocument();
  });
});
