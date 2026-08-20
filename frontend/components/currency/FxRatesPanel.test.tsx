import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CurrencyProvider } from "@/components/currency/CurrencyProvider";
import FxRatesPanel from "@/components/currency/FxRatesPanel";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth";
import { fetchFxRates } from "@/lib/fx";
import { formatPrice } from "@/lib/utils";

vi.mock("@/lib/fx", async () => {
  const actual = await vi.importActual<typeof import("@/lib/fx")>("@/lib/fx");
  return {
    ...actual,
    fetchFxRates: vi.fn(),
  };
});

const fetchFxRatesMock = vi.mocked(fetchFxRates);

const priorPayload = {
  data: {
    base: "USD",
    rates: { USD_VND: "24000" },
    asOf: "2026-01-01T00:00:00Z",
    provider: "test",
    status: "fresh",
  },
  ok: true as const,
  status: 200,
  authRequired: false,
};

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

function renderPanel() {
  return render(
    <CurrencyProvider>
      <FxRatesPanel open onClose={() => undefined} />
    </CurrencyProvider>,
  );
}

function fetchCallsTo(path: string) {
  return vi.mocked(global.fetch).mock.calls.filter(([url]) => String(url).includes(path));
}

describe("FxRatesPanel admin refresh", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
    fetchFxRatesMock.mockReset();
    fetchFxRatesMock.mockResolvedValue(priorPayload);
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    window.sessionStorage.clear();
    window.localStorage.clear();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows Refresh rates only when GET /api/auth/me role is admin", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:user1");
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ role: "user", userId: "user-1" }));

    const { unmount } = renderPanel();

    await waitFor(() => {
      expect(screen.getByText("USD_VND")).toBeInTheDocument();
    });
    expect(fetchCallsTo("/api/auth/me").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Refresh rates" })).not.toBeInTheDocument();

    unmount();

    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:admin1");
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ role: "admin", userId: "admin-1" }));
    renderPanel();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Refresh rates" })).toBeInTheDocument();
    });
  });

  it("does not show Refresh rates when unauthenticated", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ role: "admin" }));
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("USD_VND")).toBeInTheDocument();
    });
    expect(fetchCallsTo("/api/auth/me")).toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Refresh rates" })).not.toBeInTheDocument();
  });

  it("POSTs /api/admin/fx/refresh and replaces panel rates on success", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:admin1");
    vi.mocked(global.fetch).mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/auth/me")) return jsonResponse({ role: "admin", userId: "admin-1" });
      if (url.includes("/api/admin/fx/refresh")) {
        return jsonResponse({
          base: "USD",
          rates: { USD_VND: "26000" },
          asOf: "2026-08-19T12:00:00Z",
          provider: "exchangerate",
          status: "fresh",
          lastRefreshStatus: "success",
        });
      }
      return jsonResponse({}, 404);
    });

    renderPanel();

    const button = await screen.findByRole("button", { name: "Refresh rates" });
    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByText(formatPrice(26000))).toBeInTheDocument();
    });
    expect(screen.queryByText(formatPrice(24000))).not.toBeInTheDocument();

    const refreshCalls = fetchCallsTo("/api/admin/fx/refresh");
    expect(refreshCalls).toHaveLength(1);
    const init = refreshCalls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer fake:admin1");
  });

  it("keeps prior rates and shows detail on 502", async () => {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "fake:admin1");
    vi.mocked(global.fetch).mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/auth/me")) return jsonResponse({ role: "admin", userId: "admin-1" });
      if (url.includes("/api/admin/fx/refresh")) {
        return jsonResponse(
          {
            detail: "boom",
            rates: {
              base: "USD",
              rates: { USD_VND: "24000" },
              status: "fresh",
              lastRefreshError: "boom",
            },
          },
          502,
        );
      }
      return jsonResponse({}, 404);
    });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(formatPrice(24000))).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Refresh rates" }));
    });

    await waitFor(() => {
      expect(screen.getByText("boom")).toBeInTheDocument();
    });
    expect(screen.getByText(formatPrice(24000))).toBeInTheDocument();
    expect(screen.queryByText(formatPrice(26000))).not.toBeInTheDocument();
  });
});
