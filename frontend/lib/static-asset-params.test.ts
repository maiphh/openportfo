import { describe, expect, it } from "vitest";
import { CRYPTO_STATIC_SEED } from "@/lib/static-asset-params";

describe("CRYPTO_STATIC_SEED", () => {
  it("includes common tickers for news symbol inference", () => {
    expect(CRYPTO_STATIC_SEED).toContain("btc");
    expect(CRYPTO_STATIC_SEED).toContain("usdt");
    expect(CRYPTO_STATIC_SEED.length).toBeGreaterThan(5);
  });
});
