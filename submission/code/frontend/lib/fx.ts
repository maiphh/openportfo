import { apiBase } from "@/lib/api";
import { bearerHeader } from "@/lib/auth";
import { emptyFxRates, type FxRatesPayload } from "@/lib/currency";

export type FetchFxRatesResult = {
  data: FxRatesPayload;
  ok: boolean;
  status: number;
  /** True when API rejected for missing/invalid auth. */
  authRequired: boolean;
};

export type RefreshFxRatesResult = {
  data: FxRatesPayload;
  ok: boolean;
  status: number;
  /** Provider/API error (`detail` or `lastRefreshError`). */
  error: string | null;
  authRequired: boolean;
};

function authHeaders(token?: string | null): Record<string, string> {
  return { Accept: "application/json", ...bearerHeader(token) };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value != null && typeof value === "object" && !Array.isArray(value);
}

export function parseFxRatesPayload(body: unknown): FxRatesPayload {
  if (!isRecord(body)) return emptyFxRates("missing");
  const ratesRaw = body.rates;
  return {
    base: typeof body.base === "string" ? body.base : null,
    rates: isRecord(ratesRaw)
      ? Object.fromEntries(Object.entries(ratesRaw).map(([k, v]) => [k, String(v)]))
      : {},
    asOf: typeof body.asOf === "string" ? body.asOf : null,
    provider: typeof body.provider === "string" ? body.provider : null,
    status: typeof body.status === "string" ? body.status : "missing",
    lastRefreshStatus: typeof body.lastRefreshStatus === "string" ? body.lastRefreshStatus : null,
    lastRefreshError: typeof body.lastRefreshError === "string" ? body.lastRefreshError : null,
    updatedBy: typeof body.updatedBy === "string" ? body.updatedBy : null,
  };
}

function readErrorDetail(body: unknown): string | null {
  if (!isRecord(body)) return null;
  if (typeof body.detail === "string" && body.detail.trim()) return body.detail;
  if (typeof body.lastRefreshError === "string" && body.lastRefreshError.trim()) {
    return body.lastRefreshError;
  }
  const nested = body.rates;
  if (isRecord(nested) && typeof nested.lastRefreshError === "string" && nested.lastRefreshError.trim()) {
    return nested.lastRefreshError;
  }
  return null;
}

async function readJson(res: Response): Promise<unknown> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchFxRates(options?: {
  token?: string | null;
  signal?: AbortSignal;
}): Promise<FetchFxRatesResult> {
  const res = await fetch(`${apiBase()}/api/fx/rates`, {
    method: "GET",
    headers: authHeaders(options?.token),
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

  return {
    data: parseFxRatesPayload(await readJson(res)),
    ok: true,
    status: res.status,
    authRequired: false,
  };
}

export async function refreshFxRates(options?: {
  token?: string | null;
  signal?: AbortSignal;
}): Promise<RefreshFxRatesResult> {
  const res = await fetch(`${apiBase()}/api/admin/fx/refresh`, {
    method: "POST",
    headers: authHeaders(options?.token),
    signal: options?.signal,
    cache: "no-store",
  });

  const body = await readJson(res);
  const authRequired = res.status === 401 || res.status === 403;

  if (res.ok) {
    return {
      data: parseFxRatesPayload(body),
      ok: true,
      status: res.status,
      error: null,
      authRequired: false,
    };
  }

  const nested = isRecord(body) ? body.rates : null;
  const previous = isRecord(nested) ? parseFxRatesPayload(nested) : emptyFxRates("missing");

  return {
    data: previous,
    ok: false,
    status: res.status,
    error: readErrorDetail(body) || `HTTP ${res.status}`,
    authRequired,
  };
}
