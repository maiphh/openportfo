/**
 * Known crypto tickers/ids used for news symbol typing (BL-007).
 * Not used for route generation — asset detail is `/asset?type=&id=`.
 */
export const CRYPTO_STATIC_SEED = [
  "btc",
  "bitcoin",
  "eth",
  "ethereum",
  "usdt",
  "tether",
  "bnb",
  "sol",
  "solana",
  "xrp",
  "ada",
  "cardano",
  "doge",
  "dogecoin",
] as const;
