import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type TestProfile = { userId: string; email: string; name: string; role: "user" | "admin" };

const mocks = vi.hoisted(() => ({
  pathname: "/settings",
  query: "",
  push: vi.fn(),
  replace: vi.fn(),
  auth: {
    hydrated: true,
    token: "token" as string | null,
    profile: { userId: "u1", email: "u1@example.com", name: "User", role: "user" } as TestProfile | null,
    loading: false,
    error: null,
    cognitoConfigured: true,
    refresh: vi.fn(),
    reloadProfile: vi.fn(async () => null),
    replaceProfile: vi.fn(),
    signIn: vi.fn(async () => undefined),
    signOut: vi.fn(),
  },
}));

vi.mock("next/navigation", () => ({
  usePathname: () => mocks.pathname,
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
  useSearchParams: () => new URLSearchParams(mocks.query),
}));
vi.mock("@/components/LanguageProvider", () => ({ useT: () => (key: string) => ({
  "settings.title": "Settings",
  "settings.subtitle": "Account settings",
  "settings.tabs": "Settings tabs",
  "settings.general": "General",
  "settings.avatar": "Avatar",
  "settings.fx": "FX rates",
  "settings.chatbot": "Chatbot",
  "settings.signInPrompt": "Sign in to continue",
  "settings.signIn": "Sign in",
}[key] ?? key) }));
vi.mock("@/lib/use-auth-profile", () => ({ useAuthProfile: () => mocks.auth }));
vi.mock("@/components/settings/GeneralTab", () => ({ default: () => <div data-testid="general-panel" /> }));
vi.mock("@/components/settings/AvatarTab", () => ({ default: () => <div data-testid="avatar-panel" /> }));
vi.mock("@/components/settings/FxTab", () => ({ default: () => <div data-testid="fx-panel" /> }));
vi.mock("@/components/settings/ChatbotTab", () => ({ default: () => <div data-testid="chatbot-panel" /> }));

import SettingsPageClient from "@/components/settings/SettingsPageClient";

describe("SettingsPageClient", () => {
  beforeEach(() => {
    mocks.pathname = "/settings";
    mocks.query = "";
    mocks.push.mockReset();
    mocks.replace.mockReset();
    mocks.auth.hydrated = true;
    mocks.auth.token = "token";
    mocks.auth.profile = { userId: "u1", email: "u1@example.com", name: "User", role: "user" };
    mocks.auth.loading = false;
    mocks.auth.signIn.mockReset();
  });

  afterEach(cleanup);

  it("shows a stable hydration skeleton and avoids protected panels", () => {
    mocks.auth.hydrated = false;
    render(<SettingsPageClient />);
    expect(document.querySelector('[aria-busy="true"]')).toBeInTheDocument();
    expect(screen.queryByTestId("general-panel")).not.toBeInTheDocument();
  });

  it("shows signed-out prompt and preserves the same-origin query for sign-in", async () => {
    mocks.auth.token = null;
    mocks.auth.profile = null;
    mocks.query = "tab=avatar";
    render(<SettingsPageClient />);
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(mocks.auth.signIn).toHaveBeenCalledWith("/settings?tab=avatar"));
  });

  it("canonicalizes unauthorized chatbot deep links to General without requesting the admin panel", async () => {
    mocks.query = "tab=chatbot";
    render(<SettingsPageClient />);
    expect(screen.getByTestId("general-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("chatbot-panel")).not.toBeInTheDocument();
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/settings", { scroll: false }));
  });

  it("renders the admin chatbot tab and uses push for tab selection", async () => {
    mocks.auth.profile = { ...mocks.auth.profile!, role: "admin" };
    mocks.query = "tab=chatbot";
    render(<SettingsPageClient />);
    expect(screen.getByTestId("chatbot-panel")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "FX rates" }));
    expect(mocks.push).toHaveBeenCalledWith("/settings?tab=fx", { scroll: false });
  });

  it("canonicalizes the default query and supports keyboard tab navigation", async () => {
    mocks.query = "tab=general";
    render(<SettingsPageClient />);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/settings", { scroll: false }));
    const general = screen.getByRole("tab", { name: "General" });
    fireEvent.keyDown(general, { key: "ArrowRight" });
    expect(mocks.push).toHaveBeenCalledWith("/settings?tab=avatar", { scroll: false });
  });
});
