import { describe, expect, it } from "vitest";
import { DICTIONARY, LANGS, resolveLang, translate } from "@/lib/i18n";

describe("chrome translations", () => {
  it("has a Vietnamese entry for every English key", () => {
    for (const key of Object.keys(DICTIONARY.en)) expect(DICTIONARY.vi[key]).toBeTruthy();
  });

  it("resolves language and falls back to English/key", () => {
    expect(resolveLang("vi")).toBe("vi");
    expect(resolveLang("fr")).toBe("en");
    expect(translate("vi", "nav.portfolio")).toBe("Danh mục");
    expect(translate("en", "missing.key")).toBe("missing.key");
    expect(LANGS).toEqual(["en", "vi"]);
  });
});

