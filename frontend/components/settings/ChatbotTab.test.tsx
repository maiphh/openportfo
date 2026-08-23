import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  fetchAdminSettings: vi.fn(),
  updateAdminSettings: vi.fn(),
}));

vi.mock("@/lib/admin-api", () => ({
  fetchAdminSettings: mocks.fetchAdminSettings,
  updateAdminSettings: mocks.updateAdminSettings,
}));

import ChatbotTab from "@/components/settings/ChatbotTab";
import { LanguageProvider } from "@/components/LanguageProvider";
import { AuthApiError } from "@/lib/auth";
import type { AdminSettings } from "@/lib/admin-api";
import type { AuthProfileController } from "@/lib/use-auth-profile";

const settings: AdminSettings = {
  version: 4,
  emailTime: "08:00",
  timezone: "UTC",
  emailEnabled: false,
  priceCacheTtlMinutes: 15,
  jobs: {},
  defaultDisplayCurrency: "USD",
  chat: {
    overrides: { model: null, fallbackModels: null, temperature: null, topP: null, maxTokens: null, systemPromptExtra: null },
    defaults: { model: "free-model", fallbackModels: ["free-fallback"], temperature: 0.7, topP: 0.9, maxTokens: 1000, systemPromptExtra: null },
    effective: { model: "free-model", fallbackModels: ["free-fallback"], temperature: 0.7, topP: 0.9, maxTokens: 1000, systemPromptExtra: null },
    availableModels: ["free-model", "free-fallback"],
  },
};

function auth(role: "user" | "admin"): AuthProfileController {
  return {
    hydrated: true,
    token: "token",
    profile: { userId: role, email: `${role}@example.com`, name: role, role },
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

function renderTab(controller: AuthProfileController) {
  return render(<LanguageProvider><ChatbotTab auth={controller} /></LanguageProvider>);
}

describe("ChatbotTab", () => {
  beforeEach(() => {
    mocks.fetchAdminSettings.mockReset().mockResolvedValue(settings);
    mocks.updateAdminSettings.mockReset().mockResolvedValue(settings);
  });

  afterEach(cleanup);

  it("does not fetch admin settings for a normal user", () => {
    renderTab(auth("user"));
    expect(mocks.fetchAdminSettings).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("administrators only");
  });

  it("keeps null environment fallbacks distinct from an explicit empty list", async () => {
    renderTab(auth("admin"));
    await waitFor(() => expect(screen.getByRole("button", { name: "No fallbacks" })).toBeEnabled());
    expect(screen.getByRole("button", { name: "Use environment fallbacks" })).toHaveClass("border-teal-400");
    fireEvent.click(screen.getByRole("button", { name: "No fallbacks" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(mocks.updateAdminSettings).toHaveBeenCalledWith("token", 4, expect.objectContaining({
      chat: expect.objectContaining({ fallbackModels: [] }),
    })));
  });

  it("preserves edits on a version conflict and offers a reload", async () => {
    mocks.updateAdminSettings.mockRejectedValueOnce(new AuthApiError(409, "settings_conflict"));
    renderTab(auth("admin"));
    await waitFor(() => expect(screen.getByLabelText("Primary model")).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Primary model"), { target: { value: "free-fallback" } });
    await waitFor(() => expect(screen.getByLabelText("Primary model")).toHaveValue("free-fallback"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Reload before saving");
    expect(screen.getByLabelText("Primary model")).toHaveValue("free-fallback");
    mocks.fetchAdminSettings.mockResolvedValueOnce({ ...settings, version: 5 });
    fireEvent.click(screen.getByRole("button", { name: "Reload settings" }));
    await waitFor(() => expect(mocks.fetchAdminSettings).toHaveBeenCalledTimes(2));
    expect(screen.getByLabelText("Primary model")).toHaveValue("");
  });

  it("renders all six raw/default/effective fields and prevents duplicate saves", async () => {
    renderTab(auth("admin"));
    await waitFor(() => expect(screen.getByText("Raw overrides")).toBeInTheDocument());
    for (const label of ["Primary model", "Fallback models", "Temperature", "Top-p", "Max tokens", "System prompt suffix"]) {
      expect(screen.getAllByText(new RegExp(`^${label}`)).length).toBeGreaterThanOrEqual(4);
    }
    expect(screen.getByText(/Model\/provider support varies/)).toBeInTheDocument();

    let resolveSave: ((value: AdminSettings) => void) | undefined;
    mocks.updateAdminSettings.mockReturnValueOnce(new Promise((resolve) => { resolveSave = resolve; }));
    fireEvent.change(screen.getByLabelText("Temperature"), { target: { value: "1.2" } });
    await waitFor(() => expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled());
    const saveButton = screen.getByRole("button", { name: "Save changes" });
    fireEvent.click(saveButton);
    fireEvent.click(saveButton);
    expect(mocks.updateAdminSettings).toHaveBeenCalledTimes(1);
    resolveSave?.(settings);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Saved"));
  });

  it("blocks out-of-range, non-integer, and control-character values before saving", async () => {
    renderTab(auth("admin"));
    await waitFor(() => expect(screen.getByLabelText("Temperature")).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Temperature"), { target: { value: "2.1" } });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Temperature must be between"));
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Temperature"), { target: { value: "0.7" } });
    fireEvent.change(screen.getByLabelText("Max tokens"), { target: { value: "1.5" } });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Max tokens must be an integer"));
    fireEvent.change(screen.getByLabelText("Max tokens"), { target: { value: "1000" } });
    fireEvent.change(screen.getByLabelText("System prompt suffix"), { target: { value: "bad\u0000suffix" } });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Prompt suffix must be"));
    expect(mocks.updateAdminSettings).not.toHaveBeenCalled();
  });
});
