import { apiBase } from "@/lib/api";
import { AuthApiError, bearerHeader, type AuthProfile } from "@/lib/auth";
import type { UserSettingsPatch } from "@/lib/settings-api";

export type AdminUserRow = AuthProfile & {
  createdAt: string | null;
  updatedAt: string | null;
  role: "user" | "admin";
  roleManagedByEnv: boolean;
  isCurrentUser: boolean;
};

export type AdminUsersPage = { items: AdminUserRow[]; nextCursor: string | null };
export type ChatOverride = {
  model: string | null;
  fallbackModels: string[] | null;
  temperature: number | null;
  topP: number | null;
  maxTokens: number | null;
  systemPromptExtra: string | null;
};
export type AdminSettings = {
  version: number;
  emailTime: string;
  timezone: string;
  emailEnabled: boolean;
  priceCacheTtlMinutes: number;
  jobs: Record<string, boolean>;
  defaultDisplayCurrency: string;
  chat: {
    overrides: ChatOverride;
    defaults: ChatOverride;
    effective: ChatOverride;
    availableModels: string[];
  };
};

async function apiError(response: Response): Promise<AuthApiError> {
  let detail = `HTTP ${response.status}`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (body.detail && typeof body.detail === "object" && "code" in body.detail) {
      detail = String((body.detail as { code?: unknown }).code || detail);
    } else if (typeof body.detail === "string") detail = body.detail;
  } catch {
    // status-only detail is safe
  }
  return new AuthApiError(response.status, detail);
}

async function request<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...bearerHeader(token),
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!response.ok) throw await apiError(response);
  return (await response.json()) as T;
}

export function fetchAdminUsers(token: string, options?: { limit?: number; cursor?: string | null; signal?: AbortSignal }): Promise<AdminUsersPage> {
  const params = new URLSearchParams({ limit: String(options?.limit ?? 25) });
  if (options?.cursor) params.set("cursor", options.cursor);
  return request<AdminUsersPage>(token, `/api/admin/users?${params.toString()}`, { signal: options?.signal });
}

export function updateAdminUserRole(token: string, userId: string, role: "user" | "admin"): Promise<AdminUserRow> {
  return request<AdminUserRow>(token, `/api/admin/users/${encodeURIComponent(userId)}/role`, {
    method: "PUT",
    body: JSON.stringify({ role }),
  });
}

export function updateAdminUserSettings(token: string, userId: string, patch: UserSettingsPatch): Promise<AdminUserRow> {
  return request<AdminUserRow>(token, `/api/admin/users/${encodeURIComponent(userId)}/settings`, {
    method: "PUT",
    body: JSON.stringify(patch),
  });
}

export function fetchAdminSettings(token: string, options?: { signal?: AbortSignal }): Promise<AdminSettings> {
  return request<AdminSettings>(token, "/api/admin/settings", { signal: options?.signal });
}

export function updateAdminSettings(
  token: string,
  version: number,
  patch: Record<string, unknown>,
): Promise<AdminSettings> {
  return request<AdminSettings>(token, "/api/admin/settings", {
    method: "PUT",
    body: JSON.stringify({ version, ...patch }),
  });
}

