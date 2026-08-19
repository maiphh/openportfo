import { describe, expect, it } from "vitest";
import {
  CRYPTO_STATIC_SEED,
  STOCK_STATIC_SEED,
  buildStaticAssetParams,
} from "@/lib/static-asset-params";

describe("buildStaticAssetParams", () => {
  it(
    "always includes crypto seeds even when markets API is down",
    async () => {
      const params = await buildStaticAssetParams("crypto");
      const ids = params.map((p) => p.id);
      expect(ids).toContain("btc");
      expect(ids).toContain("bitcoin");
      expect(ids.length).toBeGreaterThanOrEqual(CRYPTO_STATIC_SEED.length);
    },
    15_000,
  );

  it(
    "always includes stock seeds even when markets API is down",
    async () => {
      const params = await buildStaticAssetParams("stock");
      const ids = params.map((p) => p.id);
      expect(ids).toContain("VNM");
      expect(ids).toContain("VCB");
      expect(ids.length).toBeGreaterThanOrEqual(STOCK_STATIC_SEED.length);
    },
    15_000,
  );
});
