import { afterEach, describe, expect, it, vi } from "vitest";
import {
  CRYPTO_STATIC_SEED,
  STOCK_STATIC_SEED,
  buildStaticAssetParams,
} from "@/lib/static-asset-params";

afterEach(() => {
  vi.unstubAllGlobals();
});

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

  it("drops non-ASCII and unsafe symbols from market payloads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/heatmap")) {
          return new Response(
            JSON.stringify({
              sectors: [
                {
                  name: "x",
                  stocks: [
                    { symbol: "VNM", name: "Vinamilk", changePct: 1, marketCap: 1 },
                    { symbol: "币安人生", name: "bad", changePct: 1, marketCap: 1 },
                    { symbol: "[id]", name: "template", changePct: 1, marketCap: 1 },
                    { symbol: "", name: "empty", changePct: 1, marketCap: 1 },
                  ],
                },
              ],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(JSON.stringify({ groups: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );

    const params = await buildStaticAssetParams("stock");
    const ids = params.map((p) => p.id);
    expect(ids).toContain("VNM");
    expect(ids).not.toContain("币安人生");
    expect(ids).not.toContain("[id]");
    expect(ids.every((id) => /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(id))).toBe(true);
  });
});
