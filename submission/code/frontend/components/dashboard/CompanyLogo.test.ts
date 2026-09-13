import { afterEach, describe, expect, it } from "vitest";
import { preferLogoSrc, vnStockLogoUrl } from "@/components/dashboard/CompanyLogo";
import { rememberLogo } from "@/lib/logo-cache";

describe("asset logos", () => {
  afterEach(() => {
    sessionStorage.clear();
  });

  it("uses the shared VN CDN for every stock surface", () => {
    expect(vnStockLogoUrl("acb")).toBe(
      "https://companiesmarketcap.com/img/company-logos/128/ACB.VN.png",
    );
    expect(
      preferLogoSrc({
        symbol: "ACB",
        assetType: "stock",
        imageUrl: "https://www.google.com/s2/favicons?domain=acb.com.vn&sz=128",
      }),
    ).toBe("https://companiesmarketcap.com/img/company-logos/128/ACB.VN.png");
  });

  it("prefers CoinGecko imageUrl for crypto", () => {
    expect(
      preferLogoSrc({
        symbol: "BTC",
        assetType: "crypto",
        imageUrl: "https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
      }),
    ).toBe("https://assets.coingecko.com/coins/images/1/large/bitcoin.png");
  });

  it("falls back to session logo cache for crypto without src", () => {
    rememberLogo(
      "crypto",
      "ETH",
      "https://assets.coingecko.com/coins/images/279/large/ethereum.png",
    );
    expect(preferLogoSrc({ symbol: "ETH", assetType: "crypto" })).toBe(
      "https://assets.coingecko.com/coins/images/279/large/ethereum.png",
    );
  });
});
