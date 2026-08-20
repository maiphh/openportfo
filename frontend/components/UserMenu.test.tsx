import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import UserMenu from "@/components/UserMenu";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

vi.mock("next/link", () => ({
  default({
    href,
    children,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  },
}));

vi.mock("@/lib/cognito", async () => {
  const actual = await vi.importActual<typeof import("@/lib/cognito")>("@/lib/cognito");
  return {
    ...actual,
    isCognitoConfigured: vi.fn(),
    beginHostedUiLogin: vi.fn(),
    logoutFromApp: vi.fn(() => ({ cognitoLogoutUrl: null })),
  };
});

const { beginHostedUiLogin, isCognitoConfigured } = await import("@/lib/cognito");
const beginHostedUiLoginMock = vi.mocked(beginHostedUiLogin);
const isCognitoConfiguredMock = vi.mocked(isCognitoConfigured);

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("UserMenu", () => {
  beforeEach(() => {
    window.localStorage.clear();
    beginHostedUiLoginMock.mockReset();
    isCognitoConfiguredMock.mockReturnValue(false);
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("does not render MOCK_USER while signed out", async () => {
    render(<UserMenu />);

    await waitFor(() => {
      expect(screen.getByTestId("user-menu-label")).toHaveTextContent("Guest");
    });
    expect(screen.queryByText("phu")).not.toBeInTheDocument();
    expect(screen.queryByText("phu@artryx.app")).not.toBeInTheDocument();
  });

  it("loads name and email from GET /api/auth/me", async () => {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "id.jwt");
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({ userId: "sub-1", email: "ada@example.com", name: "Ada Lovelace" }),
    );

    render(<UserMenu />);

    await waitFor(() => {
      expect(screen.getByTestId("user-menu-label")).toHaveTextContent("Ada Lovelace");
    });
    expect(screen.queryByText("phu@artryx.app")).not.toBeInTheDocument();
    expect(String(vi.mocked(global.fetch).mock.calls[0]?.[0])).toMatch(/\/api\/auth\/me$/);
  });

  it("clears a rejected token and does not keep a fake profile", async () => {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "stale.jwt");
    isCognitoConfiguredMock.mockReturnValue(true);
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ detail: "Unauthorized" }, 401));

    render(<UserMenu />);

    await waitFor(() => {
      expect(screen.getByTestId("user-menu-label")).toHaveTextContent("Sign in");
    });
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(screen.queryByText("phu")).not.toBeInTheDocument();
  });

  it("shows an error when header sign-in cannot start", async () => {
    isCognitoConfiguredMock.mockReturnValue(true);
    beginHostedUiLoginMock.mockRejectedValue(new Error("Browser storage is disabled"));
    render(<UserMenu />);

    await waitFor(() => {
      expect(screen.getByTestId("user-menu-label")).toHaveTextContent("Sign in");
    });
    fireEvent.pointerDown(screen.getByTestId("user-menu-label").closest("button")!, {
      button: 0,
      ctrlKey: false,
    });
    fireEvent.click(await screen.findByRole("menuitem", { name: "Sign in" }));

    expect(await screen.findByText("Browser storage is disabled")).toBeInTheDocument();
  });
});
