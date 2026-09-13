import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBase } from "@/lib/api";
import { AUTH_TOKEN_STORAGE_KEY, fetchAuthMe, readAuthToken } from "@/lib/auth";
import { fetchFxRates, refreshFxRates } from "@/lib/fx";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("fetchFxRates", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  });

  it("reads the optional auth token only from sessionStorage", () => {
    expect(readAuthToken()).toBeNull();
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, " fake:u1 ");
    expect(readAuthToken()).toBe("fake:u1");
    expect(window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe(" fake:u1 ");
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("marks authRequired on 401", async () => {
    vi.mocked(global.fetch).mockResolvedValue(jsonResponse({ detail: "Unauthorized" }, 401));
    const result = await fetchFxRates();
    expect(result.ok).toBe(false);
    expect(result.authRequired).toBe(true);
    expect(result.data.status).toBe("missing");
  });

  it("parses stored rates payload", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({
        base: "USD",
        rates: { USD_VND: "25000" },
        asOf: "2026-08-01T00:00:00Z",
        provider: "exchangerate",
        status: "fresh",
      }),
    );
    const result = await fetchFxRates({ token: "fake:u1" });
    expect(result.ok).toBe(true);
    expect(result.data.rates.USD_VND).toBe("25000");
    expect(result.data.status).toBe("fresh");
    expect(vi.mocked(global.fetch).mock.calls[0]?.[0]).toBe(`${apiBase()}/api/fx/rates`);
    const init = vi.mocked(global.fetch).mock.calls[0]?.[1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer fake:u1");
  });
});

describe("fetchAuthMe", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("returns role from GET /api/auth/me", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({ role: "admin", userId: "a1", email: "admin@example.com", name: "Admin" }),
    );
    const result = await fetchAuthMe({ token: "fake:admin1" });
    expect(result.role).toBe("admin");
    expect(vi.mocked(global.fetch).mock.calls[0]?.[0]).toBe(`${apiBase()}/api/auth/me`);
    const init = vi.mocked(global.fetch).mock.calls[0]?.[1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer fake:admin1");
  });
});

describe("refreshFxRates", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("POSTs /api/admin/fx/refresh with Bearer and parses success rates", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse({
        base: "USD",
        rates: { USD_VND: "26000" },
        asOf: "2026-08-19T00:00:00Z",
        provider: "exchangerate",
        status: "fresh",
        lastRefreshStatus: "success",
      }),
    );
    const result = await refreshFxRates({ token: "fake:admin1" });
    expect(result.ok).toBe(true);
    expect(result.data.rates.USD_VND).toBe("26000");
    expect(vi.mocked(global.fetch).mock.calls[0]?.[0]).toBe(`${apiBase()}/api/admin/fx/refresh`);
    const init = vi.mocked(global.fetch).mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer fake:admin1");
  });

  it("on 502 returns error and nested previous rates without throwing", async () => {
    vi.mocked(global.fetch).mockResolvedValue(
      jsonResponse(
        {
          detail: "boom",
          rates: {
            base: "USD",
            rates: { USD_VND: "24000" },
            asOf: "2026-01-01T00:00:00Z",
            status: "fresh",
            lastRefreshError: "boom",
          },
        },
        502,
      ),
    );
    const result = await refreshFxRates({ token: "fake:admin1" });
    expect(result.ok).toBe(false);
    expect(result.status).toBe(502);
    expect(result.error).toBe("boom");
    expect(result.data.rates.USD_VND).toBe("24000");
  });
});
