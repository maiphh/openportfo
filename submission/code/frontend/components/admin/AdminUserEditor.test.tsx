import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AdminUserEditor from "@/components/admin/AdminUserEditor";
import { LanguageProvider } from "@/components/LanguageProvider";
import { updateAdminUserSettings } from "@/lib/admin-api";
import type { AdminUserRow } from "@/lib/admin-api";
import type { AuthProfileController } from "@/lib/use-auth-profile";

vi.mock("@/lib/admin-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/admin-api")>("@/lib/admin-api");
  return { ...actual, updateAdminUserSettings: vi.fn() };
});

const updateMock = vi.mocked(updateAdminUserSettings);

const user: AdminUserRow = {
  userId: "u1",
  email: "u1@example.com",
  name: "User",
  role: "user",
  newsKeywords: ["BTC"],
  emailOptIn: false,
  preferredCurrency: "USD",
  avatarStyle: "notionists",
  avatarSeed: "seed",
  avatarColor: "14b8a6",
  createdAt: null,
  updatedAt: null,
  roleManagedByEnv: false,
  isCurrentUser: false,
};

function auth(): AuthProfileController {
  return {
    hydrated: true,
    token: "token",
    profile: user,
    loading: false,
    error: null,
    cognitoConfigured: false,
    refresh: vi.fn(),
    reloadProfile: vi.fn(async () => null),
    replaceProfile: vi.fn(),
    signIn: vi.fn(async () => undefined),
    signOut: vi.fn(),
  };
}

function renderEditor(controller = auth()) {
  return render(
    <LanguageProvider>
      <AdminUserEditor auth={controller} user={user} onClose={vi.fn()} onSaved={vi.fn()} />
    </LanguageProvider>,
  );
}

describe("AdminUserEditor", () => {
  beforeEach(() => updateMock.mockReset().mockResolvedValue(user));
  afterEach(cleanup);

  it("maps blank keywords to an explicit empty array", async () => {
    renderEditor();
    const keywords = screen.getByLabelText("News keywords");
    fireEvent.change(keywords, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(updateMock).toHaveBeenCalledWith("token", "u1", expect.objectContaining({ newsKeywords: [] })));
  });

  it("focuses the editor heading and marks invalid fields with their description", () => {
    renderEditor();
    expect(screen.getByRole("heading", { name: "User" })).toHaveFocus();
    fireEvent.change(screen.getByLabelText("Avatar seed"), { target: { value: "x".repeat(65) } });
    const field = screen.getByLabelText("Avatar seed");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAttribute("aria-describedby", "admin-user-settings-error");
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
