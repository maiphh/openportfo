import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  updateUserSettings: vi.fn(),
  setCurrency: vi.fn(),
}));

vi.mock("@/lib/settings-api", () => ({ updateUserSettings: mocks.updateUserSettings }));
vi.mock("@/components/currency/CurrencyProvider", () => ({
  useDisplayCurrency: () => ({ currency: "USD", setCurrency: mocks.setCurrency }),
}));

import GeneralTab from "@/components/settings/GeneralTab";
import AvatarTab from "@/components/settings/AvatarTab";
import type { AuthProfileController } from "@/lib/use-auth-profile";

const profile = {
  userId: "alice",
  email: "alice@example.com",
  name: "Alice",
  role: "user" as const,
  preferredCurrency: "USD" as const,
  emailOptIn: false,
  newsKeywords: ["BTC"],
  avatarStyle: "notionists" as const,
  avatarSeed: "alice-seed",
  avatarColor: "14b8a6",
};

function auth(): AuthProfileController {
  return {
    hydrated: true,
    token: "token",
    profile,
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

describe("settings tabs", () => {
  beforeEach(() => {
    mocks.updateUserSettings.mockReset().mockResolvedValue(profile);
    mocks.setCurrency.mockReset();
  });

  afterEach(cleanup);

  it("keeps General clean initially, saves an explicit patch, and resets edits", async () => {
    const controller = auth();
    render(<GeneralTab auth={controller} />);
    const save = screen.getByRole("button", { name: "Save changes" });
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByLabelText("News keywords"), { target: { value: "VND" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(save).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(mocks.updateUserSettings).toHaveBeenCalledWith("token", {
      newsKeywords: ["BTC", "VND"],
      emailOptIn: false,
      preferredCurrency: "USD",
    }));
    expect(controller.replaceProfile).toHaveBeenCalledWith(profile);

    fireEvent.change(screen.getByLabelText("News keywords"), { target: { value: "EUR" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(screen.queryByRole("button", { name: /EUR/ })).not.toBeInTheDocument();
  });

  it("keeps avatar edits local until save and sends canonical reset/style fields", async () => {
    const controller = auth();
    render(<AvatarTab auth={controller} />);
    fireEvent.click(screen.getByRole("radio", { name: "shapes" }));
    fireEvent.change(screen.getByLabelText("Avatar seed"), { target: { value: "new-seed" } });
    fireEvent.change(screen.getByLabelText("Background color"), { target: { value: "#abcdef" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(mocks.updateUserSettings).toHaveBeenCalledWith("token", {
      avatarStyle: "shapes",
      avatarSeed: "new-seed",
      avatarColor: "abcdef",
    }));
    expect(controller.replaceProfile).toHaveBeenCalledWith(profile);

    fireEvent.click(screen.getByRole("button", { name: "Use default" }));
    expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(mocks.updateUserSettings).toHaveBeenLastCalledWith("token", {
      avatarStyle: null,
      avatarSeed: null,
      avatarColor: null,
    }));
    fireEvent.click(screen.getByRole("button", { name: "Revert edits" }));
    expect(screen.getByLabelText("Avatar seed")).toHaveValue("alice-seed");
  });

  it("disables avatar save for invalid input and surfaces the validation message", () => {
    const controller = auth();
    render(<AvatarTab auth={controller} />);
    fireEvent.change(screen.getByLabelText("Avatar seed"), { target: { value: "x".repeat(65) } });
    expect(screen.getByRole("alert")).toHaveTextContent("avatar");
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
    expect(mocks.updateUserSettings).not.toHaveBeenCalled();
  });
});
