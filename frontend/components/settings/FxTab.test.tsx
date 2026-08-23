import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import FxTab from "@/components/settings/FxTab";
import { CurrencyProvider } from "@/components/currency/CurrencyProvider";
import { LanguageProvider } from "@/components/LanguageProvider";
import { fetchFxRates, refreshFxRates } from "@/lib/fx";
import type { AuthProfileController } from "@/lib/use-auth-profile";

vi.mock("@/lib/fx", async () => {
  const actual = await vi.importActual<typeof import("@/lib/fx")>("@/lib/fx");
  return { ...actual, fetchFxRates: vi.fn(), refreshFxRates: vi.fn() };
});

const fetchFxRatesMock = vi.mocked(fetchFxRates);
const refreshFxRatesMock = vi.mocked(refreshFxRates);

const prior = {
  base: "USD",
  rates: { USD_VND: "24000" },
  asOf: "2026-01-01T00:00:00Z",
  provider: "test",
  status: "fresh",
} as const;

function auth(role: "user" | "admin" | undefined): AuthProfileController {
  return {
    hydrated: true,
    token: role ? "token" : null,
    profile: role ? { userId: role, email: `${role}@example.com`, name: role, role } : null,
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
  return render(
    <LanguageProvider>
      <CurrencyProvider>
        <FxTab auth={controller} />
      </CurrencyProvider>
    </LanguageProvider>,
  );
}

describe("FxTab", () => {
  beforeEach(() => {
    fetchFxRatesMock.mockReset().mockResolvedValue({ data: prior, ok: true, status: 200, authRequired: false });
    refreshFxRatesMock.mockReset();
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it("renders rates for a user without exposing the admin refresh action", async () => {
    renderTab(auth("user"));
    await waitFor(() => expect(screen.getByText("USD_VND")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Refresh rates" })).not.toBeInTheDocument();
  });

  it("refreshes and replaces shared rates for an admin", async () => {
    refreshFxRatesMock.mockResolvedValue({
      data: { ...prior, rates: { USD_VND: "26000" }, asOf: "2026-08-19T12:00:00Z", provider: "exchangerate" },
      ok: true,
      status: 200,
      error: null,
      authRequired: false,
    });
    renderTab(auth("admin"));
    const button = await screen.findByRole("button", { name: "Refresh rates" });
    await act(async () => { fireEvent.click(button); });
    await waitFor(() => expect(screen.getByText("26000")).toBeInTheDocument());
    expect(refreshFxRatesMock).toHaveBeenCalledWith(expect.objectContaining({ token: "token" }));
  });

  it("retains the previous table and reports a refresh failure", async () => {
    refreshFxRatesMock.mockResolvedValue({
      data: { ...prior, lastRefreshError: "provider unavailable" },
      ok: false,
      status: 502,
      error: "provider unavailable",
      authRequired: false,
    });
    renderTab(auth("admin"));
    await screen.findByRole("button", { name: "Refresh rates" });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Refresh rates" })); });
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not refresh FX rates.");
    expect(screen.getByText("24000")).toBeInTheDocument();
  });

  it("uses the provider's initial fetch without mounting a duplicate tab fetch", async () => {
    renderTab(auth("user"));
    await waitFor(() => expect(screen.getByText("USD_VND")).toBeInTheDocument());
    expect(fetchFxRatesMock).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["fresh", "Fresh"],
    ["stale", "Stale"],
    ["missing", "Missing"],
  ] as const)("localizes the %s rates state", async (status, label) => {
    fetchFxRatesMock.mockResolvedValueOnce({
      data: { ...prior, status, rates: status === "missing" ? {} : prior.rates },
      ok: true,
      status: 200,
      authRequired: false,
    });
    renderTab(auth("user"));
    expect(await screen.findByRole("status", { name: "FX data status" })).toHaveTextContent(label);
  });

  it("clears busy state after a thrown refresh and reloads auth only for an auth response", async () => {
    const controller = auth("admin");
    refreshFxRatesMock.mockRejectedValueOnce(new Error("network down"));
    renderTab(controller);
    const button = await screen.findByRole("button", { name: "Refresh rates" });
    await act(async () => { fireEvent.click(button); });
    await waitFor(() => expect(button).toBeEnabled());
    expect(controller.reloadProfile).not.toHaveBeenCalled();

    refreshFxRatesMock.mockResolvedValueOnce({
      data: prior,
      ok: false,
      status: 401,
      error: "unauthorized",
      authRequired: true,
    });
    await act(async () => { fireEvent.click(button); });
    await waitFor(() => expect(controller.reloadProfile).toHaveBeenCalledTimes(1));
  });
});
