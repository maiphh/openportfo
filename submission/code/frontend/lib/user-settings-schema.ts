import { AVATAR_STYLES, type AvatarStyle } from "@/lib/avatar";

export { AVATAR_STYLES };
export type { AvatarStyle };

export function normalizeKeyword(value: string): string {
  return value.normalize("NFKC").trim();
}

export function normalizeKeywordList(values: readonly string[]): string[] {
  const output: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const normalized = normalizeKeyword(value);
    const key = normalized.toLocaleLowerCase();
    if (normalized && !seen.has(key)) {
      seen.add(key);
      output.push(normalized);
    }
  }
  return output;
}

export function validKeywordList(values: readonly string[]): boolean {
  return values.length <= 20 && values.every((value) => {
    const normalized = normalizeKeyword(value);
    return normalized.length >= 1
      && normalized.length <= 50
      && !Array.from(normalized).some((char) => /\p{Cc}|\p{Cf}/u.test(char));
  });
}

export function isValidAvatarStyle(value: string | null | undefined): value is AvatarStyle | "" {
  return value === "" || (typeof value === "string" && (AVATAR_STYLES as readonly string[]).includes(value));
}

export function normalizeAvatarSeed(value: string): string {
  return value.normalize("NFKC").trim();
}

export function validAvatarSeed(value: string): boolean {
  const normalized = normalizeAvatarSeed(value);
  return !normalized || (normalized.length <= 64 && !Array.from(normalized).some((char) => /\p{Cc}|\p{Cf}/u.test(char)));
}

export function normalizeAvatarColor(value: string): string | null {
  const trimmed = value.trim();
  const match = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(trimmed);
  if (!match) return null;
  const raw = match[1]!.toLowerCase();
  return raw.length === 3 ? raw.split("").map((char) => `${char}${char}`).join("") : raw;
}

export function validAvatarColor(value: string): boolean {
  return !value.trim() || normalizeAvatarColor(value) !== null;
}
