import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type TestProfile = { userId: string; email: string; name: string; role: "user" | "admin" };

const mocks = vi.hoisted(() => ({
  fetchAdminUsers: vi.fn(),
  updateAdminUserRole: vi.fn(),
  auth: {
    hydrated: true,
    token: "admin-token" as string | null,
    profile: { userId: "admin", email: "admin@example.com", name: "Admin", role: "admin" } as TestProfile | null,
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

vi.mock("@/lib/admin-api", () => ({
  fetchAdminUsers: mocks.fetchAdminUsers,
  updateAdminUserRole: mocks.updateAdminUserRole,
}));
vi.mock("@/lib/use-auth-profile", () => ({ useAuthProfile: () => mocks.auth }));
vi.mock("@/components/LanguageProvider", () => ({ useT: () => (key: string) => ({
  "admin.title": "Users",
  "admin.subtitle": "Manage users",
  "admin.user": "User",
  "admin.role": "Role",
  "admin.created": "Created",
  "admin.actions": "Actions",
  "admin.edit": "Edit settings",
  "admin.loadMore": "Load more",
  "admin.loading": "Loading",
  "admin.forbidden": "Admin access required",
  "admin.roleError": "Unable to update role",
  "admin.whitelistError": "Managed by allowlist",
  "admin.lastAdminError": "The last admin cannot be removed",
  "admin.conflictError": "Role changed elsewhere",
  "admin.loadError": "Unable to load users",
  "admin.managedByEnv": "Managed by environment",
  "settings.signInPrompt": "Sign in to continue",
  "settings.signIn": "Sign in",
  "common.close": "Close",
}[key] ?? key) }));
vi.mock("@/components/admin/AdminUserEditor", () => ({
  default: ({ onClose }: { onClose: () => void }) => <button type="button" onClick={onClose}>Close editor</button>,
}));
vi.mock("@/components/admin/RssSourcesPanel", () => ({
  default: () => <div>RSS panel</div>,
}));
vi.mock("@/components/admin/JobControlsPanel", () => ({
  default: () => <div>Jobs panel</div>,
}));
vi.mock("@/components/admin/JobRunsPanel", () => ({
  default: () => <div>Runs panel</div>,
}));
vi.mock("next/link", () => ({ default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => <a href={href} {...props}>{children}</a> }));

import AdminPageClient from "@/components/admin/AdminPageClient";
import { AuthApiError } from "@/lib/auth";

const row = (userId: string, role: "user" | "admin" = "user") => ({
  userId,
  email: `${userId}@example.com`,
  name: userId,
  role,
  createdAt: "2026-08-01T00:00:00Z",
  updatedAt: null,
  roleManagedByEnv: false,
  isCurrentUser: userId === "admin",
});

describe("AdminPageClient", () => {
  beforeEach(() => {
    mocks.fetchAdminUsers.mockReset().mockResolvedValue({ items: [row("alice")], nextCursor: "next" });
    mocks.updateAdminUserRole.mockReset().mockResolvedValue(row("alice", "admin"));
    mocks.auth.hydrated = true;
    mocks.auth.token = "admin-token";
    mocks.auth.profile = { userId: "admin", email: "admin@example.com", name: "Admin", role: "admin" };
    mocks.auth.signIn.mockReset();
    mocks.auth.replaceProfile.mockReset();
  });

  afterEach(cleanup);

  it("does not request users for signed-out or non-admin viewers", async () => {
    mocks.auth.token = null;
    mocks.auth.profile = null;
    render(<AdminPageClient />);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(mocks.fetchAdminUsers).not.toHaveBeenCalled();

    cleanup();
    mocks.auth.token = "user-token";
    mocks.auth.profile = { userId: "user", email: "user@example.com", name: "User", role: "user" };
    render(<AdminPageClient />);
    expect(screen.getByRole("alert")).toHaveTextContent("Admin access required");
    expect(mocks.fetchAdminUsers).not.toHaveBeenCalled();
  });

  it("renders a paged semantic table, deduplicates load-more rows, and updates roles", async () => {
    render(<AdminPageClient />);
    await waitFor(() => expect(screen.getByRole("row", { name: /alice@example.com/ })).toBeInTheDocument());
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load more" })).toBeInTheDocument();

    mocks.fetchAdminUsers.mockResolvedValueOnce({ items: [row("alice"), row("bob")], nextCursor: null });
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    await waitFor(() => expect(screen.getByText("bob@example.com")).toBeInTheDocument());
    expect(screen.getAllByText("alice@example.com")).toHaveLength(1);

    fireEvent.change(screen.getByRole("combobox", { name: /alice@example.com/ }), { target: { value: "admin" } });
    await waitFor(() => expect(mocks.updateAdminUserRole).toHaveBeenCalledWith("admin-token", "alice", "admin"));
  });

  it("locks environment-managed rows and maps role conflict errors to safe copy", async () => {
    mocks.fetchAdminUsers.mockResolvedValue({ items: [{ ...row("managed"), roleManagedByEnv: true }], nextCursor: null });
    render(<AdminPageClient />);
    await waitFor(() => expect(screen.getByText("managed@example.com")).toBeInTheDocument());
    expect(screen.getByRole("combobox", { name: /managed@example.com/ })).toBeDisabled();

    mocks.fetchAdminUsers.mockResolvedValue({ items: [row("alice")], nextCursor: null });
    cleanup();
    mocks.updateAdminUserRole.mockRejectedValueOnce(new AuthApiError(409, "role_conflict"));
    render(<AdminPageClient />);
    await waitFor(() => expect(screen.getByText("alice@example.com")).toBeInTheDocument());
    fireEvent.change(screen.getByRole("combobox", { name: /alice@example.com/ }), { target: { value: "admin" } });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Role changed elsewhere"));
  });

  it("opens the in-flow editor and returns focus through its close callback", async () => {
    render(<AdminPageClient />);
    await waitFor(() => expect(screen.getByText("alice@example.com")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Edit settings" }));
    expect(screen.getByRole("button", { name: "Close editor" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close editor" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Close editor" })).not.toBeInTheDocument());
  });
});
