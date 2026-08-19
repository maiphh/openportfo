import { apiBase } from "@/lib/api";
import { AUTH_TOKEN_STORAGE_KEY, readAuthToken } from "@/lib/auth";
import { emptyFxRates, type FxRatesPayload } from "@/lib/currency";

export { AUTH_TOKEN_STORAGE_KEY, readAuthToken };

export type FetchFxRatesResult = {
  data: FxRatesPayload;
  ok: boolean;
  status: number;
  /** True when API rejected for missing/invalid auth. */
  authRequired: boolean;
};

export async function fetchFxRates(options?: {
  token?: string | null;
  signal?: AbortSignal;
}): Promise<FetchFxRatesResult> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = options?.token?.trim();
  if (token) {
    headers.Authorization = token.startsWith("Bearer ") ? token : `Bearer ${token}`;
  }

  const res = await fetch(`${apiBase()}/api/fx/rates`, {
    method: "GET",
    headers,
    signal: options?.signal,
    cache: "no-store",
  });

  if (res.status === 401 || res.status === 403) {
    return {
      data: emptyFxRates("missing"),
      ok: false,
      status: res.status,
      authRequired: true,
    };
  }

  if (!res.ok) {
    return {
      data: emptyFxRates("missing"),
      ok: false,
      status: res.status,
      authRequired: false,
    };
  }

  const body = (await res.json()) as Partial<FxRatesPayload>;
  return {
    data: {
      base: body.base ?? null,
      rates: body.rates && typeof body.rates === "object" ? body.rates : {},
      asOf: body.asOf ?? null,
      provider: body.provider ?? null,
      status: typeof body.status === "string" ? body.status : "missing",
      lastRefreshStatus: body.lastRefreshStatus ?? null,
      lastRefreshError: body.lastRefreshError ?? null,
      updatedBy: body.updatedBy ?? null,
    },
    ok: true,
    status: res.status,
    authRequired: false,
  };
}
