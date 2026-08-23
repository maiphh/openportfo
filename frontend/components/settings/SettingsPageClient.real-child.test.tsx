import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  fetchAdminSettings: vi.fn(),
  updateAdminSettings: vi.fn(),
  replace: vi.fn(),
  push: vi.fn(),
  query: "tab=chatbot",
  auth: {
    hydrated: true,
    token: "token" as string | null,
    profile: { userId: "u1", email: "u1@example.com", name: "User", role: "user" as const },
    loading: false,
    error: null,
    cognitoConfigured: false,
    refresh: vi.fn(),
    reloadProfile: vi.fn(async () => null),
    replaceProfile: vi.fn(),
    signIn: vi.fn(async () => undefined),
    signOut: vi.fn(),
  },
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings",
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
  "settings.adminOnly": "Administrators only",
}[key] ?? key) }));
vi.mock("@/lib/use-auth-profile", () => ({ useAuthProfile: () => mocks.auth }));
vi.mock("@/lib/admin-api", () => ({ fetchAdminSettings: mocks.fetchAdminSettings, updateAdminSettings: mocks.updateAdminSettings }));
vi.mock("@/components/settings/GeneralTab", () => ({ default: () => <div data-testid="general-panel" /> }));
vi.mock("@/components/settings/AvatarTab", () => ({ default: () => <div data-testid="avatar-panel" /> }));
vi.mock("@/components/settings/FxTab", () => ({ default: () => <div data-testid="fx-panel" /> }));

import SettingsPageClient from "@/components/settings/SettingsPageClient";
import ChatbotTab from "@/components/settings/ChatbotTab";

describe("settings authorization boundary", () => {
  afterEach(cleanup);

  it("clamps the route before mounting the real chatbot child, which makes no admin request", () => {
    render(<SettingsPageClient />);
    expect(screen.getByTestId("general-panel")).toBeInTheDocument();
    expect(screen.queryByText("Administrators only")).not.toBeInTheDocument();
    render(<ChatbotTab auth={mocks.auth} />);
    expect(screen.getByText("Administrators only")).toBeInTheDocument();
    expect(mocks.fetchAdminSettings).not.toHaveBeenCalled();
  });
});
