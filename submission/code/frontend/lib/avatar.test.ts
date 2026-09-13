import { describe, expect, it } from "vitest";
import { AVATAR_STYLES, avatarSeedFor, buildAvatarUrl, profileInitials } from "@/lib/avatar";

describe("avatar helpers", () => {
  it("builds a deterministic v9 URL with the default style", () => {
    const first = buildAvatarUrl({ seed: "Ada Lovelace" });
    expect(first).toBe(buildAvatarUrl({ seed: "Ada Lovelace" }));
    const url = new URL(first);
    expect(url.pathname).toBe("/9.x/notionists/svg");
    expect(url.searchParams.get("seed")).toBe("Ada Lovelace");
  });

  it("only allows the approved styles", () => {
    expect(AVATAR_STYLES).toContain("notionists");
    expect(new URL(buildAvatarUrl({ seed: "one", style: "bottts" })).pathname).toContain("/bottts/");
    expect(new URL(buildAvatarUrl({ seed: "one", style: "not-an-style" as never })).pathname).toContain("/notionists/");
  });

  it("normalizes valid hex colors and omits invalid values", () => {
    expect(new URL(buildAvatarUrl({ seed: "one", backgroundColor: "#0ed2a8" })).searchParams.get("backgroundColor")).toBe("0ed2a8");
    expect(new URL(buildAvatarUrl({ seed: "one", backgroundColor: "xyz" })).searchParams.has("backgroundColor")).toBe(false);
  });

  it("passes only positive integer sizes", () => {
    expect(new URL(buildAvatarUrl({ seed: "one", size: 40 })).searchParams.get("size")).toBe("40");
    expect(new URL(buildAvatarUrl({ seed: "one", size: 0 })).searchParams.has("size")).toBe(false);
    expect(new URL(buildAvatarUrl({ seed: "one", size: 2.5 })).searchParams.has("size")).toBe(false);
  });

  it("trims identity and prefers userId over email", () => {
    expect(avatarSeedFor({ userId: " sub-1 ", email: "a@example.com" })).toBe("sub-1");
    expect(avatarSeedFor({ userId: "  ", email: " a@example.com " })).toBe("a@example.com");
    expect(avatarSeedFor(null)).toBeNull();
  });

  it("creates at most two uppercase initials", () => {
    expect(profileInitials({ name: "Ada Lovelace", email: "a@example.com" })).toBe("AL");
    expect(profileInitials({ name: null, email: "a@example.com" })).toBe("A@");
    expect(profileInitials(null)).toBe("");
  });
});

