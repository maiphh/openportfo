import { apiBase } from "@/lib/api";
import { AuthApiError, bearerHeader, type AuthProfile } from "@/lib/auth";

export type UserSettingsPatch = {
  newsKeywords?: string[] | null;
  emailOptIn?: boolean | null;
  preferredCurrency?: "USD" | "VND" | "EUR" | null;
  avatarStyle?: string | null;
  avatarSeed?: string | null;
  avatarColor?: string | null;
};

export type UserSettings = {
  newsKeywords: string[];
  emailOptIn: boolean;
  preferredCurrency: string | null;
  avatarStyle: string | null;
  avatarSeed: string | null;
  avatarColor: string | null;
};

async function parseError(response: Response): Promise<AuthApiError> {
  let detail = `HTTP ${response.status}`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") detail = body.detail;
    else if (body.detail && typeof body.detail === "object" && "code" in body.detail) {
      detail = String((body.detail as { code?: unknown }).code || detail);
    }
  } catch {
    // Keep the bounded status-only detail.
  }
  return new AuthApiError(response.status, detail);
}

function profileFromPayload(body: Partial<AuthProfile>): AuthProfile {
  if (!body || typeof body.userId !== "string" || !body.userId.trim()) throw new Error("Invalid profile payload");
  return {
    userId: body.userId,
    email: typeof body.email === "string" ? body.email : "",
    name: typeof body.name === "string" ? body.name : null,
    role: typeof body.role === "string" ? body.role : undefined,
    avatarStyle: typeof body.avatarStyle === "string" ? body.avatarStyle : null,
    avatarSeed: typeof body.avatarSeed === "string" ? body.avatarSeed : null,
    avatarColor: typeof body.avatarColor === "string" ? body.avatarColor : null,
    newsKeywords: Array.isArray(body.newsKeywords) ? body.newsKeywords : [],
    emailOptIn: typeof body.emailOptIn === "boolean" ? body.emailOptIn : false,
    preferredCurrency: typeof body.preferredCurrency === "string" ? body.preferredCurrency : null,
    createdAt: typeof body.createdAt === "string" ? body.createdAt : null,
    updatedAt: typeof body.updatedAt === "string" ? body.updatedAt : null,
  };
}

export async function updateUserSettings(
  token: string,
  patch: UserSettingsPatch,
  options?: { signal?: AbortSignal },
): Promise<AuthProfile> {
  const response = await fetch(`${apiBase()}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...bearerHeader(token) },
    body: JSON.stringify(patch),
    signal: options?.signal,
    cache: "no-store",
  });
  if (!response.ok) throw await parseError(response);
  return profileFromPayload((await response.json()) as Partial<AuthProfile>);
}

export async function fetchUserSettings(token: string, options?: { signal?: AbortSignal }): Promise<UserSettings> {
  const response = await fetch(`${apiBase()}/api/settings`, {
    method: "GET",
    headers: { Accept: "application/json", ...bearerHeader(token) },
    signal: options?.signal,
    cache: "no-store",
  });
  if (!response.ok) throw await parseError(response);
  const body = (await response.json()) as Partial<UserSettings>;
  return {
    newsKeywords: Array.isArray(body.newsKeywords) ? body.newsKeywords.filter((value): value is string => typeof value === "string") : [],
    emailOptIn: body.emailOptIn === true,
    preferredCurrency: typeof body.preferredCurrency === "string" ? body.preferredCurrency : null,
    avatarStyle: typeof body.avatarStyle === "string" ? body.avatarStyle : null,
    avatarSeed: typeof body.avatarSeed === "string" ? body.avatarSeed : null,
    avatarColor: typeof body.avatarColor === "string" ? body.avatarColor : null,
  };
}

export function profileFromSettingsPayload(body: Partial<AuthProfile>): AuthProfile {
  return profileFromPayload(body);
}

