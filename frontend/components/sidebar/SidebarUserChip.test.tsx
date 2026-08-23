import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SidebarUserChip from "@/components/sidebar/SidebarUserChip";
import type { AuthProfileController } from "@/lib/use-auth-profile";

function auth(overrides: Partial<AuthProfileController> = {}): AuthProfileController {
  return {
    hydrated: true,
    token: null,
    profile: null,
    loading: false,
    error: null,
    cognitoConfigured: true,
    refresh: vi.fn(),
    signIn: vi.fn(async () => undefined),
    signOut: vi.fn(),
    ...overrides,
  };
}

describe("SidebarUserChip", () => {
  afterEach(cleanup);

  it("opens settings from the account avatar and signs in a configured guest", () => {
    const onSettings = vi.fn();
    const controller = auth();
    render(<SidebarUserChip collapsed={false} auth={controller} onOpenSettings={onSettings} />);
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(onSettings).toHaveBeenCalledTimes(1);
    expect(controller.signIn).toHaveBeenCalledTimes(1);
  });

  it("signs out a signed-in account and retains the profile name", () => {
    const controller = auth({
      token: "token",
      profile: { userId: "sub-1", email: "ada@example.com", name: "Ada" },
    });
    render(<SidebarUserChip collapsed={false} auth={controller} onOpenSettings={vi.fn()} />);
    expect(screen.getByText("Ada")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(controller.signOut).toHaveBeenCalledTimes(1);
  });
});
