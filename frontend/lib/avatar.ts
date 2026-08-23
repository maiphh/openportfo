import type { AuthProfile } from "@/lib/auth";

export const AVATAR_STYLES = [
  "notionists",
  "notionists-neutral",
  "adventurer-neutral",
  "big-smile",
  "lorelei",
  "bottts",
  "thumbs",
  "shapes",
] as const;

export type AvatarStyle = (typeof AVATAR_STYLES)[number];

export type AvatarOptions = {
  seed: string;
  style?: AvatarStyle;
  backgroundColor?: string | null;
  size?: number;
};

const DEFAULT_AVATAR_STYLE: AvatarStyle = "notionists";
const HEX_COLOR = /^#?(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

function normalizeColor(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!HEX_COLOR.test(trimmed)) return null;
  return trimmed.replace(/^#/, "").toLowerCase();
}

function allowedStyle(value: string | undefined): AvatarStyle {
  return value && (AVATAR_STYLES as readonly string[]).includes(value)
    ? (value as AvatarStyle)
    : DEFAULT_AVATAR_STYLE;
}

/** Build a deterministic, allowlisted DiceBear v9 URL. */
export function buildAvatarUrl(options: AvatarOptions): string {
  const style = allowedStyle(options.style);
  const query = new URLSearchParams();
  query.set("seed", options.seed.trim());
  const backgroundColor = normalizeColor(options.backgroundColor);
  if (backgroundColor) query.set("backgroundColor", backgroundColor);
  if (Number.isInteger(options.size) && (options.size ?? 0) > 0) {
    query.set("size", String(options.size));
  }
  return `https://api.dicebear.com/9.x/${style}/svg?${query.toString()}`;
}

/** Stable identity preference: Cognito subject first, email as fallback. */
export function avatarSeedFor(profile: Pick<AuthProfile, "userId" | "email"> | null | undefined): string | null {
  const userId = profile?.userId?.trim();
  if (userId) return userId;
  const email = profile?.email?.trim();
  return email || null;
}

export function profileInitials(
  profile: Pick<AuthProfile, "name" | "email"> | null | undefined,
): string {
  const value = profile?.name?.trim() || profile?.email?.trim() || "";
  if (!value) return "";
  const parts = value.split(/\s+/).filter(Boolean);
  const initials = parts.length > 1 ? `${parts[0]?.[0] ?? ""}${parts[parts.length - 1]?.[0] ?? ""}` : value.slice(0, 2);
  return initials.toUpperCase().slice(0, 2);
}

