import { describe, expect, it } from "vitest";
import {
  isValidAvatarStyle,
  normalizeAvatarColor,
  normalizeKeywordList,
  validAvatarColor,
  validAvatarSeed,
  validKeywordList,
} from "@/lib/user-settings-schema";

describe("user settings schema", () => {
  it("normalizes and de-duplicates keyword patches without changing their order", () => {
    expect(normalizeKeywordList(["  BTC ", "btc", "VND", "  "])).toEqual(["BTC", "VND"]);
    expect(validKeywordList(["BTC", "VND"])).toBe(true);
    expect(validKeywordList([" "])).toBe(false);
    expect(validKeywordList(["x".repeat(51)])).toBe(false);
  });

  it("accepts only the approved avatar style/seed/color values", () => {
    expect(isValidAvatarStyle("notionists")).toBe(true);
    expect(isValidAvatarStyle("unknown-style")).toBe(false);
    expect(validAvatarSeed("stable-seed")).toBe(true);
    expect(validAvatarSeed("x".repeat(65))).toBe(false);
    expect(normalizeAvatarColor("#ABC")).toBe("aabbcc");
    expect(normalizeAvatarColor("nope")).toBeNull();
    expect(validAvatarColor("#12abef")).toBe(true);
    expect(validAvatarColor("#nope")).toBe(false);
  });
});
