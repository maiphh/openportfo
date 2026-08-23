import { readFileSync } from "node:fs";
import { join } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { applyTheme, DEFAULT_THEME, resolveTheme, THEME_STORAGE_KEY } from "@/lib/theme";

describe("theme helpers", () => {
  beforeEach(() => document.documentElement.classList.add("dark"));

  it("resolves only light explicitly and defaults dark", () => {
    expect(resolveTheme("light")).toBe("light");
    expect(resolveTheme("dark")).toBe("dark");
    expect(resolveTheme(null)).toBe(DEFAULT_THEME);
  });

  it("applies the dark class to the document", () => {
    applyTheme("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    applyTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(THEME_STORAGE_KEY).toBe("openportfo.theme");
  });

  it("keeps light-mode chat errors at WCAG-AA contrast", () => {
    const chatPanel = readFileSync(join(process.cwd(), "components/chat/ChatPanel.tsx"), "utf8");
    const css = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");
    expect(chatPanel).toContain("text-red-400 dark:text-red-100");
    expect(chatPanel).toContain("text-red-400 dark:text-red-200");
    expect(css).toContain("--color-red-400: #b91c1c");

    const channel = (value: number) => {
      const s = value / 255;
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    };
    const luminance = (hex: string) => {
      const rgb = [0, 2, 4].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16)).map(channel);
      return 0.2126 * rgb[0]! + 0.7152 * rgb[1]! + 0.0722 * rgb[2]!;
    };
    const ratio = (foreground: string, background: string) => {
      const a = luminance(foreground);
      const b = luminance(background);
      return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    };
    // bg-red-400/[.06] over the light body surface #f6f8f8.
    const tintedSurface = [0, 1, 2].map((offset) => {
      const red = Number.parseInt("b91c1c".slice(offset * 2, offset * 2 + 2), 16);
      const body = Number.parseInt("f6f8f8".slice(offset * 2, offset * 2 + 2), 16);
      return Math.round(red * 0.06 + body * 0.94).toString(16).padStart(2, "0");
    }).join("");
    expect(ratio("b91c1c", tintedSurface)).toBeGreaterThanOrEqual(4.5);
  });
});
