import type { QuoteRow } from "@/types/markets";

export type RangeKey = "1D" | "1M" | "3M" | "1Y" | "5Y" | "All";

export type OverviewTab = "Financial" | "Technology" | "Services";

export type LogoSpec = {
  bg: string;
  fg: string;
  mark: string;
};

export const NAV_ITEMS = [
  {
    href: "/markets/stock",
    label: "Market",
    children: [
      { href: "/markets/stock", label: "Stock" },
      { href: "/markets/crypto", label: "Crypto" },
    ],
  },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/search", label: "Search" },
] as const;

export const MOCK_USER = {
  name: "phu",
  email: "phu@artryx.app",
};

export const RANGES: RangeKey[] = ["1D", "1M", "3M", "1Y", "5Y", "All"];

export const LOGOS: Record<string, LogoSpec> = {
  JPM: { bg: "#0b6cf0", fg: "#fff", mark: "JP" },
  WFC: { bg: "#d71e28", fg: "#fff", mark: "WF" },
  BAC: { bg: "#012169", fg: "#fff", mark: "BA" },
  HSBC: { bg: "#db0011", fg: "#fff", mark: "HS" },
  C: { bg: "#003b70", fg: "#fff", mark: "C" },
  MA: { bg: "#eb001b", fg: "#fff", mark: "MC" },
  V: { bg: "#1a1f71", fg: "#fff", mark: "V" },
  AAPL: { bg: "#555555", fg: "#fff", mark: "" },
  GOOGL: { bg: "#4285f4", fg: "#fff", mark: "G" },
  MSFT: { bg: "#00a4ef", fg: "#fff", mark: "⊞" },
  META: { bg: "#0668e1", fg: "#fff", mark: "∞" },
  ORCL: { bg: "#f80000", fg: "#fff", mark: "O" },
  INTC: { bg: "#0071c5", fg: "#fff", mark: "i" },
  AMZN: { bg: "#ff9900", fg: "#111", mark: "a" },
  BABA: { bg: "#ff6a00", fg: "#fff", mark: "A" },
  T: { bg: "#00a8e0", fg: "#fff", mark: "T" },
  NVDA: { bg: "#76b900", fg: "#111", mark: "N" },
  AMD: { bg: "#ed1c24", fg: "#fff", mark: "A" },
  MU: { bg: "#0d9488", fg: "#fff", mark: "µ" },
  AMGN: { bg: "#005eb8", fg: "#fff", mark: "A" },
  AVGO: { bg: "#cc092f", fg: "#fff", mark: "A" },
  NFLX: { bg: "#e50914", fg: "#fff", mark: "N" },
  TSLA: { bg: "#cc0000", fg: "#fff", mark: "T" },
  LLY: { bg: "#d52b1e", fg: "#fff", mark: "L" },
  JNJ: { bg: "#d51900", fg: "#fff", mark: "J" },
  UNH: { bg: "#0033a0", fg: "#fff", mark: "U" },
  WMT: { bg: "#0071ce", fg: "#fff", mark: "W" },
  COST: { bg: "#e31837", fg: "#fff", mark: "C" },
  HD: { bg: "#f96302", fg: "#fff", mark: "HD" },
  BRK: { bg: "#1a365d", fg: "#fff", mark: "BR" },
  XOM: { bg: "#ed1b2d", fg: "#fff", mark: "X" },
  CVX: { bg: "#0033a0", fg: "#fff", mark: "C" },
  PG: { bg: "#003da5", fg: "#fff", mark: "PG" },
  KO: { bg: "#f40009", fg: "#fff", mark: "C" },
  PEP: { bg: "#004b93", fg: "#fff", mark: "P" },
  DIS: { bg: "#113ccf", fg: "#fff", mark: "D" },
  NKE: { bg: "#111111", fg: "#fff", mark: "✓" },
  CRM: { bg: "#00a1e0", fg: "#fff", mark: "C" },
  ADBE: { bg: "#eb1000", fg: "#fff", mark: "Ae" },
  CSCO: { bg: "#049fd9", fg: "#fff", mark: "cs" },
  IBM: { bg: "#0530ad", fg: "#fff", mark: "IBM" },
  QCOM: { bg: "#3253dc", fg: "#fff", mark: "Q" },
  TXN: { bg: "#cc0000", fg: "#fff", mark: "ti" },
  AMAT: { bg: "#1f4e79", fg: "#fff", mark: "A" },
  NOW: { bg: "#81b5a1", fg: "#111", mark: "N" },
  UBER: { bg: "#000000", fg: "#fff", mark: "U" },
  ABBV: { bg: "#071d49", fg: "#fff", mark: "A" },
  MRK: { bg: "#00857c", fg: "#fff", mark: "M" },
  PFE: { bg: "#0093d0", fg: "#fff", mark: "P" },
  GS: { bg: "#7399c6", fg: "#111", mark: "GS" },
  MS: { bg: "#002b5c", fg: "#fff", mark: "MS" },
  SCHW: { bg: "#00a0df", fg: "#fff", mark: "S" },
  AXP: { bg: "#016fd0", fg: "#fff", mark: "A" },
  BLK: { bg: "#111111", fg: "#fff", mark: "B" },
  SPGI: { bg: "#f58025", fg: "#fff", mark: "S" },
  CAT: { bg: "#ffcd11", fg: "#111", mark: "C" },
  GE: { bg: "#0870c2", fg: "#fff", mark: "GE" },
  HON: { bg: "#e01e34", fg: "#fff", mark: "H" },
  BA: { bg: "#0033a0", fg: "#fff", mark: "BA" },
  UNP: { bg: "#002677", fg: "#fff", mark: "U" },
  RTX: { bg: "#e4002b", fg: "#fff", mark: "R" },
  NEE: { bg: "#0077c8", fg: "#fff", mark: "N" },
  SO: { bg: "#f2a900", fg: "#111", mark: "SO" },
  DUK: { bg: "#0072ce", fg: "#fff", mark: "D" },
  COP: { bg: "#e31837", fg: "#fff", mark: "C" },
  PM: { bg: "#1d1d1b", fg: "#fff", mark: "PM" },
  MO: { bg: "#4a1c2b", fg: "#fff", mark: "M" },
  MCD: { bg: "#ffc72c", fg: "#111", mark: "M" },
  SBUX: { bg: "#00704a", fg: "#fff", mark: "★" },
  TMO: { bg: "#e31937", fg: "#fff", mark: "T" },
  ISRG: { bg: "#0b3d91", fg: "#fff", mark: "I" },
  VRTX: { bg: "#3b6e8f", fg: "#fff", mark: "V" },
  LRCX: { bg: "#005eb8", fg: "#fff", mark: "L" },
  KLAC: { bg: "#00a3e0", fg: "#fff", mark: "K" },
  ADI: { bg: "#1c57a5", fg: "#fff", mark: "A" },
  INTU: { bg: "#2ca01c", fg: "#fff", mark: "I" },
  ACN: { bg: "#a100ff", fg: "#fff", mark: "A" },
  SHOP: { bg: "#96bf48", fg: "#111", mark: "S" },
  NFL: { bg: "#e50914", fg: "#fff", mark: "N" },
  CMCSA: { bg: "#2b9cd8", fg: "#fff", mark: "C" },
  VZ: { bg: "#cd040b", fg: "#fff", mark: "VZ" },
  TMUS: { bg: "#e20074", fg: "#fff", mark: "T" },
  LOW: { bg: "#004990", fg: "#fff", mark: "L" },
  TJX: { bg: "#ce0e2d", fg: "#fff", mark: "T" },
  BKNG: { bg: "#003580", fg: "#fff", mark: "B" },
  ABT: { bg: "#00a3e0", fg: "#fff", mark: "A" },
  DHR: { bg: "#e31837", fg: "#fff", mark: "D" },
  SYK: { bg: "#f58025", fg: "#fff", mark: "S" },
  PGR: { bg: "#0066b2", fg: "#fff", mark: "P" },
  CB: { bg: "#e31837", fg: "#fff", mark: "CB" },
  MMC: { bg: "#0b1f3a", fg: "#fff", mark: "M" },
  ICE: { bg: "#1e4d8c", fg: "#fff", mark: "I" },
  CME: { bg: "#0485cc", fg: "#fff", mark: "C" },
  DE: { bg: "#367c2b", fg: "#fff", mark: "DE" },
  UPS: { bg: "#351c15", fg: "#ffb500", mark: "UPS" },
  FDX: { bg: "#4d148c", fg: "#ff6600", mark: "Fd" },
  LMT: { bg: "#005288", fg: "#fff", mark: "L" },
  NOC: { bg: "#0033a0", fg: "#fff", mark: "N" },
  WM: { bg: "#0b5e2c", fg: "#fff", mark: "WM" },
  RSG: { bg: "#00529b", fg: "#fff", mark: "R" },
  AEP: { bg: "#ef3e42", fg: "#fff", mark: "A" },
  SRE: { bg: "#e31837", fg: "#fff", mark: "S" },
  SLB: { bg: "#0046ad", fg: "#fff", mark: "S" },
  EOG: { bg: "#e31837", fg: "#fff", mark: "E" },
  OXY: { bg: "#e31837", fg: "#fff", mark: "O" },
  CL: { bg: "#ed1c24", fg: "#fff", mark: "C" },
  MDLZ: { bg: "#4a1c6f", fg: "#fff", mark: "M" },
  EL: { bg: "#000000", fg: "#fff", mark: "EL" },
  TGT: { bg: "#cc0000", fg: "#fff", mark: "T" },
  CVS: { bg: "#cc0000", fg: "#fff", mark: "CVS" },
  CI: { bg: "#0079c1", fg: "#fff", mark: "CI" },
  ELV: { bg: "#003da5", fg: "#fff", mark: "E" },
  MDT: { bg: "#004b87", fg: "#fff", mark: "M" },
  GILD: { bg: "#d52b1e", fg: "#fff", mark: "G" },
  AMGN2: { bg: "#005eb8", fg: "#fff", mark: "A" },
  PANW: { bg: "#fa582d", fg: "#fff", mark: "P" },
  CRWD: { bg: "#e03e2d", fg: "#fff", mark: "C" },
  PLTR: { bg: "#111111", fg: "#fff", mark: "P" },
  APP: { bg: "#0b5fff", fg: "#fff", mark: "A" },
  BTC: { bg: "#f7931a", fg: "#111", mark: "₿" },
  ETH: { bg: "#627eea", fg: "#fff", mark: "Ξ" },
  BNB: { bg: "#f3ba2f", fg: "#111", mark: "B" },
  SOL: { bg: "#9945ff", fg: "#fff", mark: "S" },
  XRP: { bg: "#23292f", fg: "#fff", mark: "X" },
  ADA: { bg: "#0033ad", fg: "#fff", mark: "A" },
  AVAX: { bg: "#e84142", fg: "#fff", mark: "A" },
  DOT: { bg: "#e6007a", fg: "#fff", mark: "•" },
  DOGE: { bg: "#c2a633", fg: "#111", mark: "Ð" },
  LINK: { bg: "#2a5ada", fg: "#fff", mark: "L" },
  UNI: { bg: "#ff007a", fg: "#fff", mark: "U" },
  AAVE: { bg: "#b6509e", fg: "#fff", mark: "A" },
  MATIC: { bg: "#8247e5", fg: "#fff", mark: "M" },
  ATOM: { bg: "#2e3148", fg: "#fff", mark: "A" },
  LTC: { bg: "#345d9d", fg: "#fff", mark: "Ł" },
  NEAR: { bg: "#00c08b", fg: "#111", mark: "N" },
  APT: { bg: "#111111", fg: "#fff", mark: "A" },
  SUI: { bg: "#4da2ff", fg: "#111", mark: "S" },
  TON: { bg: "#0098ea", fg: "#fff", mark: "T" },
  SHIB: { bg: "#ffa409", fg: "#111", mark: "S" },
  PEPE: { bg: "#3d9a3d", fg: "#fff", mark: "P" },
  ARB: { bg: "#28a0f0", fg: "#fff", mark: "A" },
  OP: { bg: "#ff0420", fg: "#fff", mark: "O" },
  TRX: { bg: "#ff0013", fg: "#fff", mark: "T" },
};

export function logoFor(symbol: string): LogoSpec {
  return LOGOS[symbol] ?? { bg: "#30333a", fg: "#ccdadc", mark: symbol.slice(0, 2) };
}

function mulberry32(seed: number) {
  let s = seed >>> 0;
  return () => {
    s += 0x6d2b79f5;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashSymbol(symbol: string) {
  return symbol.split("").reduce((acc, ch, i) => acc + ch.charCodeAt(0) * (i + 13), 17);
}

export function sparklineFor(symbol: string, range: RangeKey): number[] {
  const points = { "1D": 78, "1M": 32, "3M": 64, "1Y": 96, "5Y": 120, All: 140 }[range];
  const rand = mulberry32(hashSymbol(symbol) + points * 9);
  const driftMap: Record<RangeKey, number> = {
    "1D": 0.0004,
    "1M": 0.0012,
    "3M": 0.0018,
    "1Y": 0.0024,
    "5Y": 0.003,
    All: 0.0028,
  };
  const volMap: Record<RangeKey, number> = {
    "1D": 0.006,
    "1M": 0.014,
    "3M": 0.018,
    "1Y": 0.022,
    "5Y": 0.028,
    All: 0.03,
  };
  const drift = driftMap[range];
  const vol = volMap[range];
  const data: number[] = [];
  let v = 100;
  for (let i = 0; i < points; i++) {
    const u1 = Math.max(rand(), 1e-9);
    const u2 = rand();
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    const dip = range === "1Y" && i > points * 0.35 && i < points * 0.48 ? -0.012 : 0;
    v = Math.max(12, v * (1 + drift + dip + vol * z));
    data.push(v);
  }
  return data;
}

export const RANGE_LABELS: Record<RangeKey, string[]> = {
  "1D": ["9:30", "11:00", "12:30", "14:00", "16:00"],
  "1M": ["W1", "W2", "W3", "W4"],
  "3M": ["Jun", "Jul", "Aug"],
  "1Y": ["Sep", "2026", "Apr", "Jul"],
  "5Y": ["2022", "2023", "2024", "2025", "2026"],
  All: ["2018", "2020", "2022", "2024", "2026"],
};

export const OVERVIEW_TABS: Record<OverviewTab, QuoteRow[]> = {
  Financial: [
    { symbol: "JPM", name: "JPMorgan Chase", value: 363.25, change: 2.29, changePct: 0.63, open: 360.1, high: 364.8, low: 359.4, prev: 360.96 },
    { symbol: "WFC", name: "Wells Fargo Co New", value: 87.4, change: -0.14, changePct: -0.16, open: 87.62, high: 88.05, low: 86.91, prev: 87.54 },
    { symbol: "BAC", name: "Bank Amer Corp", value: 64.21, change: 0.34, changePct: 0.53, open: 63.88, high: 64.55, low: 63.7, prev: 63.87 },
    { symbol: "HSBC", name: "Hsbc Hldgs Plc", value: 103.18, change: -0.62, changePct: -0.6, open: 103.84, high: 104.2, low: 102.81, prev: 103.8 },
    { symbol: "C", name: "Citigroup Inc", value: 137.65, change: 0.86, changePct: 0.63, open: 137.37, high: 138.21, low: 136.45, prev: 136.79 },
    { symbol: "MA", name: "Mastercard Incorporated", value: 574.31, change: 12.09, changePct: 2.15, open: 563.87, high: 578.5, low: 563.41, prev: 562.22 },
  ],
  Technology: [
    { symbol: "AAPL", name: "Apple", value: 310.03, change: 4.44, changePct: 1.45, open: 305.28, high: 311.49, low: 305.74, prev: 305.59 },
    { symbol: "GOOGL", name: "Alphabet", value: 344.2, change: 0.2, changePct: 0.06, open: 342.41, high: 344.87, low: 340.19, prev: 344.0 },
    { symbol: "MSFT", name: "Microsoft", value: 481.63, change: -1.28, changePct: -0.27, open: 481.54, high: 484.77, low: 477.15, prev: 482.91 },
    { symbol: "META", name: "Meta Platforms", value: 543.67, change: -25.3, changePct: -4.45, open: 551.54, high: 564.66, low: 542.21, prev: 568.97 },
    { symbol: "ORCL", name: "Oracle Corp", value: 142.79, change: -9.8, changePct: -6.43, open: 143.25, high: 146.0, low: 142.35, prev: 152.59 },
    { symbol: "INTC", name: "Intel Corp", value: 96.69, change: 4.86, changePct: 5.28, open: 92.76, high: 99.31, low: 92.15, prev: 91.83 },
  ],
  Services: [
    { symbol: "AMZN", name: "Amazon", value: 259.45, change: -1.86, changePct: -0.71, open: 260.63, high: 262.18, low: 257.73, prev: 261.31 },
    { symbol: "BABA", name: "Alibaba Group Hldg Ltd", value: 128.15, change: 3.44, changePct: 2.76, open: 127.16, high: 128.79, low: 124.71, prev: 124.71 },
    { symbol: "T", name: "At&t Inc", value: 24.9, change: 0.27, changePct: 1.08, open: 24.64, high: 25.21, low: 24.63, prev: 24.63 },
    { symbol: "WMT", name: "Walmart", value: 98.42, change: 0.31, changePct: 0.32, open: 98.1, high: 99.05, low: 97.8, prev: 98.11 },
    { symbol: "V", name: "Visa", value: 342.18, change: 1.44, changePct: 0.42, open: 340.5, high: 343.9, low: 339.8, prev: 340.74 },
  ],
};

export const SEARCH_UNIVERSE: QuoteRow[] = [
  ...OVERVIEW_TABS.Financial,
  ...OVERVIEW_TABS.Technology,
  ...OVERVIEW_TABS.Services,
  { symbol: "NVDA", name: "NVIDIA", value: 118.42, change: -2.84, changePct: -2.34, open: 121.1, high: 122.4, low: 117.8, prev: 121.26, assetType: "stock" },
  { symbol: "TSLA", name: "Tesla", value: 248.9, change: 2.16, changePct: 0.88, open: 246.2, high: 251.3, low: 245.1, prev: 246.74, assetType: "stock" },
  { symbol: "AMD", name: "Advanced Micro Devices", value: 148.22, change: -6.61, changePct: -4.27, open: 154.1, high: 155.4, low: 147.3, prev: 154.83, assetType: "stock" },
  { symbol: "BTC", name: "Bitcoin", value: 68420, change: 820, changePct: 1.21, open: 67600, high: 69100, low: 67250, prev: 67600, assetType: "crypto" },
  { symbol: "ETH", name: "Ethereum", value: 3420, change: -48, changePct: -1.38, open: 3468, high: 3510, low: 3395, prev: 3468, assetType: "crypto" },
]
  .map((row): QuoteRow => ({
    ...row,
    assetType: row.assetType === "crypto" ? "crypto" : "stock",
  }))
  .filter((row, index, arr) => arr.findIndex((r) => r.symbol === row.symbol) === index);
