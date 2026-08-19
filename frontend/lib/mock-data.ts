export type RangeKey = "1D" | "1M" | "3M" | "1Y" | "5Y" | "All";

export type OverviewTab = "Financial" | "Technology" | "Services";

export type LogoSpec = {
  bg: string;
  fg: string;
  mark: string;
};

export type QuoteRow = {
  symbol: string;
  name: string;
  value: number;
  change: number;
  changePct: number;
  open: number;
  high: number;
  low: number;
  prev: number;
};

export type QuoteGroup = {
  name: string;
  rows: QuoteRow[];
};

export type HeatmapStock = {
  symbol: string;
  name: string;
  changePct: number;
  marketCap: number;
};

export type HeatmapSector = {
  name: string;
  stocks: HeatmapStock[];
};

export type Story = {
  id: string;
  source: string;
  sourceColor: string;
  timeAgo: string;
  headline: string;
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

export const QUOTE_GROUPS: QuoteGroup[] = [
  {
    name: "FINANCIAL",
    rows: [OVERVIEW_TABS.Financial[3], OVERVIEW_TABS.Financial[4], OVERVIEW_TABS.Financial[5]],
  },
  { name: "TECHNOLOGY", rows: OVERVIEW_TABS.Technology },
  { name: "SERVICES", rows: OVERVIEW_TABS.Services.slice(0, 3) },
];

export const CRYPTO_QUOTE_GROUPS: QuoteGroup[] = [
  {
    name: "MAJOR",
    rows: [
      { symbol: "BTC", name: "Bitcoin", value: 97420.55, change: 1180.4, changePct: 1.23, open: 96240.1, high: 98110.0, low: 95880.2, prev: 96240.15 },
      { symbol: "ETH", name: "Ethereum", value: 3428.9, change: -28.15, changePct: -0.81, open: 3456.2, high: 3490.0, low: 3402.4, prev: 3457.05 },
      { symbol: "BNB", name: "BNB", value: 612.4, change: 4.22, changePct: 0.69, open: 608.1, high: 616.8, low: 604.5, prev: 608.18 },
      { symbol: "XRP", name: "XRP", value: 2.18, change: 0.04, changePct: 1.87, open: 2.14, high: 2.21, low: 2.11, prev: 2.14 },
    ],
  },
  {
    name: "LAYER 1",
    rows: [
      { symbol: "SOL", name: "Solana", value: 178.32, change: 3.41, changePct: 1.95, open: 174.8, high: 180.2, low: 173.4, prev: 174.91 },
      { symbol: "ADA", name: "Cardano", value: 0.78, change: -0.02, changePct: -2.5, open: 0.8, high: 0.81, low: 0.77, prev: 0.8 },
      { symbol: "AVAX", name: "Avalanche", value: 38.12, change: 0.54, changePct: 1.44, open: 37.55, high: 38.6, low: 37.2, prev: 37.58 },
      { symbol: "DOT", name: "Polkadot", value: 7.42, change: -0.11, changePct: -1.46, open: 7.54, high: 7.61, low: 7.33, prev: 7.53 },
      { symbol: "NEAR", name: "NEAR", value: 5.12, change: 0.18, changePct: 3.64, open: 4.94, high: 5.21, low: 4.88, prev: 4.94 },
      { symbol: "TON", name: "Toncoin", value: 5.86, change: -0.08, changePct: -1.35, open: 5.94, high: 6.02, low: 5.79, prev: 5.94 },
    ],
  },
  {
    name: "DEFI",
    rows: [
      { symbol: "UNI", name: "Uniswap", value: 9.84, change: 0.22, changePct: 2.29, open: 9.61, high: 9.95, low: 9.55, prev: 9.62 },
      { symbol: "AAVE", name: "Aave", value: 186.4, change: -3.1, changePct: -1.64, open: 189.5, high: 191.2, low: 184.8, prev: 189.5 },
      { symbol: "LINK", name: "Chainlink", value: 18.76, change: 0.41, changePct: 2.23, open: 18.32, high: 18.95, low: 18.2, prev: 18.35 },
    ],
  },
];

export const HEATMAP_SECTORS: HeatmapSector[] = [
  {
    name: "Electronic technology",
    stocks: [
      { symbol: "NVDA", name: "NVIDIA", changePct: -2.34, marketCap: 4300 },
      { symbol: "AAPL", name: "Apple", changePct: 1.45, marketCap: 3600 },
      { symbol: "AVGO", name: "Broadcom", changePct: -0.82, marketCap: 1480 },
      { symbol: "AMGN", name: "Amgen", changePct: -3.17, marketCap: 420 },
      { symbol: "MU", name: "Micron", changePct: -7.02, marketCap: 210 },
      { symbol: "AMD", name: "AMD", changePct: -4.27, marketCap: 280 },
      { symbol: "QCOM", name: "Qualcomm", changePct: 0.54, marketCap: 190 },
      { symbol: "TXN", name: "Texas Instruments", changePct: -0.31, marketCap: 175 },
      { symbol: "INTC", name: "Intel", changePct: 5.28, marketCap: 155 },
      { symbol: "AMAT", name: "Applied Materials", changePct: -1.18, marketCap: 150 },
      { symbol: "LRCX", name: "Lam Research", changePct: -0.94, marketCap: 125 },
      { symbol: "KLAC", name: "KLA", changePct: 0.22, marketCap: 110 },
      { symbol: "ADI", name: "Analog Devices", changePct: -0.41, marketCap: 105 },
    ],
  },
  {
    name: "Technology services",
    stocks: [
      { symbol: "MSFT", name: "Microsoft", changePct: 0.27, marketCap: 3700 },
      { symbol: "GOOGL", name: "Alphabet", changePct: 0.06, marketCap: 2180 },
      { symbol: "AMZN", name: "Amazon", changePct: -0.71, marketCap: 2320 },
      { symbol: "META", name: "Meta", changePct: -4.45, marketCap: 1420 },
      { symbol: "ORCL", name: "Oracle", changePct: -6.43, marketCap: 520 },
      { symbol: "NFLX", name: "Netflix", changePct: 2.38, marketCap: 410 },
      { symbol: "PLTR", name: "Palantir", changePct: 1.9, marketCap: 310 },
      { symbol: "CRM", name: "Salesforce", changePct: 0.82, marketCap: 255 },
      { symbol: "IBM", name: "IBM", changePct: 0.41, marketCap: 210 },
      { symbol: "CSCO", name: "Cisco", changePct: 1.15, marketCap: 220 },
      { symbol: "NOW", name: "ServiceNow", changePct: -0.62, marketCap: 180 },
      { symbol: "INTU", name: "Intuit", changePct: 0.33, marketCap: 175 },
      { symbol: "ACN", name: "Accenture", changePct: -0.21, marketCap: 190 },
      { symbol: "ADBE", name: "Adobe", changePct: -1.52, marketCap: 200 },
      { symbol: "PANW", name: "Palo Alto", changePct: 0.74, marketCap: 130 },
      { symbol: "UBER", name: "Uber", changePct: 1.48, marketCap: 165 },
      { symbol: "SHOP", name: "Shopify", changePct: 2.11, marketCap: 145 },
      { symbol: "APP", name: "AppLovin", changePct: 3.4, marketCap: 120 },
      { symbol: "CRWD", name: "CrowdStrike", changePct: -0.88, marketCap: 95 },
    ],
  },
  {
    name: "Retail trade",
    stocks: [
      { symbol: "WMT", name: "Walmart", changePct: 0.32, marketCap: 650 },
      { symbol: "COST", name: "Costco", changePct: 0.18, marketCap: 410 },
      { symbol: "HD", name: "Home Depot", changePct: -0.76, marketCap: 360 },
      { symbol: "LOW", name: "Lowe's", changePct: -0.28, marketCap: 140 },
      { symbol: "TJX", name: "TJX", changePct: 0.12, marketCap: 135 },
      { symbol: "TGT", name: "Target", changePct: -1.1, marketCap: 70 },
    ],
  },
  {
    name: "Health technology",
    stocks: [
      { symbol: "LLY", name: "Eli Lilly", changePct: 1.6, marketCap: 720 },
      { symbol: "UNH", name: "UnitedHealth", changePct: -0.52, marketCap: 460 },
      { symbol: "JNJ", name: "Johnson & Johnson", changePct: 1.33, marketCap: 390 },
      { symbol: "ABBV", name: "AbbVie", changePct: 0.44, marketCap: 330 },
      { symbol: "MRK", name: "Merck", changePct: -0.29, marketCap: 280 },
      { symbol: "TMO", name: "Thermo Fisher", changePct: -0.18, marketCap: 210 },
      { symbol: "ABT", name: "Abbott", changePct: 0.36, marketCap: 200 },
      { symbol: "ISRG", name: "Intuitive", changePct: 0.91, marketCap: 175 },
      { symbol: "PFE", name: "Pfizer", changePct: 0.82, marketCap: 155 },
      { symbol: "AMGN", name: "Amgen", changePct: -3.17, marketCap: 150 },
      { symbol: "DHR", name: "Danaher", changePct: -0.22, marketCap: 165 },
      { symbol: "SYK", name: "Stryker", changePct: 0.15, marketCap: 140 },
      { symbol: "VRTX", name: "Vertex", changePct: 0.58, marketCap: 120 },
      { symbol: "GILD", name: "Gilead", changePct: -0.47, marketCap: 110 },
      { symbol: "MDT", name: "Medtronic", changePct: 0.2, marketCap: 115 },
    ],
  },
  {
    name: "Finance",
    stocks: [
      { symbol: "BRK", name: "Berkshire", changePct: 0.95, marketCap: 920 },
      { symbol: "JPM", name: "JPMorgan", changePct: 0.63, marketCap: 710 },
      { symbol: "V", name: "Visa", changePct: 0.42, marketCap: 560 },
      { symbol: "MA", name: "Mastercard", changePct: 2.15, marketCap: 460 },
      { symbol: "BAC", name: "Bank of America", changePct: 0.53, marketCap: 310 },
      { symbol: "WFC", name: "Wells Fargo", changePct: -0.16, marketCap: 230 },
      { symbol: "GS", name: "Goldman Sachs", changePct: 1.12, marketCap: 185 },
      { symbol: "MS", name: "Morgan Stanley", changePct: 0.74, marketCap: 175 },
      { symbol: "AXP", name: "American Express", changePct: 0.91, marketCap: 170 },
      { symbol: "C", name: "Citigroup", changePct: 0.63, marketCap: 125 },
      { symbol: "SCHW", name: "Charles Schwab", changePct: 0.22, marketCap: 145 },
      { symbol: "BLK", name: "BlackRock", changePct: 0.31, marketCap: 135 },
      { symbol: "SPGI", name: "S&P Global", changePct: -0.19, marketCap: 140 },
      { symbol: "PGR", name: "Progressive", changePct: 0.4, marketCap: 125 },
      { symbol: "CB", name: "Chubb", changePct: 0.11, marketCap: 105 },
      { symbol: "MMC", name: "Marsh McLennan", changePct: 0.05, marketCap: 100 },
      { symbol: "ICE", name: "Intercontinental", changePct: 0.18, marketCap: 85 },
      { symbol: "CME", name: "CME Group", changePct: 0.09, marketCap: 90 },
    ],
  },
  {
    name: "Producer manufacturing",
    stocks: [
      { symbol: "CAT", name: "Caterpillar", changePct: 0.48, marketCap: 190 },
      { symbol: "GE", name: "GE Aerospace", changePct: 1.05, marketCap: 210 },
      { symbol: "HON", name: "Honeywell", changePct: -0.22, marketCap: 140 },
      { symbol: "DE", name: "Deere", changePct: -0.61, marketCap: 120 },
      { symbol: "RTX", name: "RTX", changePct: 0.37, marketCap: 160 },
      { symbol: "LMT", name: "Lockheed", changePct: 0.14, marketCap: 115 },
    ],
  },
  {
    name: "Consumer durables",
    stocks: [
      { symbol: "TSLA", name: "Tesla", changePct: 0.88, marketCap: 980 },
      { symbol: "AMZN", name: "Amazon", changePct: -0.71, marketCap: 80 },
    ],
  },
  {
    name: "Consumer services",
    stocks: [
      { symbol: "MCD", name: "McDonald's", changePct: 0.26, marketCap: 210 },
      { symbol: "DIS", name: "Disney", changePct: -0.54, marketCap: 190 },
      { symbol: "BKNG", name: "Booking", changePct: 0.72, marketCap: 165 },
      { symbol: "SBUX", name: "Starbucks", changePct: -1.24, marketCap: 105 },
      { symbol: "NKE", name: "Nike", changePct: -0.83, marketCap: 130 },
    ],
  },
  {
    name: "Energy minerals",
    stocks: [
      { symbol: "XOM", name: "Exxon Mobil", changePct: 0.41, marketCap: 470 },
      { symbol: "CVX", name: "Chevron", changePct: -0.33, marketCap: 280 },
      { symbol: "COP", name: "ConocoPhillips", changePct: 0.19, marketCap: 130 },
      { symbol: "EOG", name: "EOG", changePct: -0.47, marketCap: 75 },
      { symbol: "OXY", name: "Occidental", changePct: -1.12, marketCap: 55 },
    ],
  },
  {
    name: "Consumer non-durables",
    stocks: [
      { symbol: "PG", name: "Procter & Gamble", changePct: 0.21, marketCap: 360 },
      { symbol: "KO", name: "Coca-Cola", changePct: 0.38, marketCap: 280 },
      { symbol: "PEP", name: "PepsiCo", changePct: -0.16, marketCap: 220 },
      { symbol: "PM", name: "Philip Morris", changePct: 0.55, marketCap: 180 },
      { symbol: "MO", name: "Altria", changePct: 0.12, marketCap: 95 },
      { symbol: "MDLZ", name: "Mondelez", changePct: -0.24, marketCap: 90 },
      { symbol: "CL", name: "Colgate", changePct: 0.08, marketCap: 70 },
    ],
  },
  {
    name: "Utilities",
    stocks: [
      { symbol: "NEE", name: "NextEra", changePct: 0.29, marketCap: 150 },
      { symbol: "SO", name: "Southern", changePct: 0.11, marketCap: 95 },
      { symbol: "DUK", name: "Duke", changePct: 0.07, marketCap: 88 },
      { symbol: "AEP", name: "AEP", changePct: -0.14, marketCap: 55 },
      { symbol: "SRE", name: "Sempra", changePct: 0.22, marketCap: 52 },
    ],
  },
  {
    name: "Transportation",
    stocks: [
      { symbol: "UNP", name: "Union Pacific", changePct: 0.18, marketCap: 145 },
      { symbol: "UPS", name: "UPS", changePct: -0.66, marketCap: 95 },
      { symbol: "FDX", name: "FedEx", changePct: -0.41, marketCap: 65 },
      { symbol: "BA", name: "Boeing", changePct: 1.24, marketCap: 130 },
    ],
  },
  {
    name: "Health services",
    stocks: [
      { symbol: "ELV", name: "Elevance", changePct: -0.38, marketCap: 110 },
      { symbol: "CI", name: "Cigna", changePct: 0.16, marketCap: 95 },
      { symbol: "CVS", name: "CVS Health", changePct: -0.92, marketCap: 85 },
    ],
  },
  {
    name: "Communications",
    stocks: [
      { symbol: "T", name: "AT&T", changePct: 1.08, marketCap: 180 },
      { symbol: "VZ", name: "Verizon", changePct: 0.44, marketCap: 175 },
      { symbol: "TMUS", name: "T-Mobile", changePct: 0.61, marketCap: 250 },
      { symbol: "CMCSA", name: "Comcast", changePct: -0.35, marketCap: 140 },
    ],
  },
  {
    name: "Industrial services",
    stocks: [
      { symbol: "WM", name: "Waste Management", changePct: 0.27, marketCap: 90 },
      { symbol: "RSG", name: "Republic Services", changePct: 0.14, marketCap: 70 },
      { symbol: "SLB", name: "Schlumberger", changePct: -0.58, marketCap: 68 },
    ],
  },
  {
    name: "Process industries",
    stocks: [
      { symbol: "LIN", name: "Linde", changePct: 0.23, marketCap: 210 },
      { symbol: "SHW", name: "Sherwin-Williams", changePct: -0.19, marketCap: 90 },
      { symbol: "APD", name: "Air Products", changePct: 0.08, marketCap: 65 },
    ],
  },
  {
    name: "Commercial services",
    stocks: [
      { symbol: "PYPL", name: "PayPal", changePct: 1.55, marketCap: 75 },
      { symbol: "FI", name: "Fiserv", changePct: -0.42, marketCap: 85 },
      { symbol: "ADP", name: "ADP", changePct: 0.17, marketCap: 110 },
    ],
  },
];

export const CRYPTO_HEATMAP_SECTORS: HeatmapSector[] = [
  {
    name: "Layer 1",
    stocks: [
      { symbol: "BTC", name: "Bitcoin", changePct: 1.23, marketCap: 1920 },
      { symbol: "ETH", name: "Ethereum", changePct: -0.81, marketCap: 412 },
      { symbol: "SOL", name: "Solana", changePct: 1.95, marketCap: 84 },
      { symbol: "BNB", name: "BNB", changePct: 0.69, marketCap: 88 },
      { symbol: "ADA", name: "Cardano", changePct: -2.5, marketCap: 28 },
      { symbol: "AVAX", name: "Avalanche", changePct: 1.44, marketCap: 15 },
      { symbol: "TON", name: "Toncoin", changePct: -1.35, marketCap: 15 },
      { symbol: "DOT", name: "Polkadot", changePct: -1.46, marketCap: 11 },
      { symbol: "NEAR", name: "NEAR", changePct: 3.64, marketCap: 6 },
      { symbol: "APT", name: "Aptos", changePct: 0.88, marketCap: 5 },
      { symbol: "SUI", name: "Sui", changePct: 2.11, marketCap: 8 },
      { symbol: "ATOM", name: "Cosmos", changePct: -0.42, marketCap: 4 },
    ],
  },
  {
    name: "DeFi",
    stocks: [
      { symbol: "UNI", name: "Uniswap", changePct: 2.29, marketCap: 7 },
      { symbol: "AAVE", name: "Aave", changePct: -1.64, marketCap: 3 },
      { symbol: "LINK", name: "Chainlink", changePct: 2.23, marketCap: 12 },
      { symbol: "MKR", name: "Maker", changePct: 0.54, marketCap: 2 },
      { symbol: "CRV", name: "Curve", changePct: -1.12, marketCap: 1 },
    ],
  },
  {
    name: "Meme",
    stocks: [
      { symbol: "DOGE", name: "Dogecoin", changePct: 3.4, marketCap: 42 },
      { symbol: "SHIB", name: "Shiba Inu", changePct: 1.18, marketCap: 10 },
      { symbol: "PEPE", name: "Pepe", changePct: -4.2, marketCap: 5 },
      { symbol: "WIF", name: "dogwifhat", changePct: 2.7, marketCap: 2 },
    ],
  },
  {
    name: "Layer 2",
    stocks: [
      { symbol: "ARB", name: "Arbitrum", changePct: 0.76, marketCap: 4 },
      { symbol: "OP", name: "Optimism", changePct: -0.91, marketCap: 3 },
      { symbol: "MATIC", name: "Polygon", changePct: 0.33, marketCap: 6 },
      { symbol: "IMX", name: "Immutable", changePct: 1.05, marketCap: 2 },
    ],
  },
  {
    name: "Payments",
    stocks: [
      { symbol: "XRP", name: "XRP", changePct: 1.87, marketCap: 124 },
      { symbol: "LTC", name: "Litecoin", changePct: 0.22, marketCap: 6 },
      { symbol: "TRX", name: "TRON", changePct: 0.48, marketCap: 22 },
      { symbol: "XLM", name: "Stellar", changePct: -0.37, marketCap: 9 },
    ],
  },
];

export const TOP_STORIES: Story[] = [
  {
    id: "1",
    source: "Y",
    sourceColor: "#ef4444",
    timeAgo: "2 hours ago",
    headline: "UNTREE: Robot Maker Explodes 62% in Shanghai Debut. Price Discovery Malfunctions",
  },
  {
    id: "2",
    source: "M",
    sourceColor: "#0668e1",
    timeAgo: "2 hours ago",
    headline: "META: Meta's $1.4 Trillion Legal Nightmare Begins. Is the Stock at Risk?",
  },
  {
    id: "3",
    source: "S",
    sourceColor: "#22c55e",
    timeAgo: "yesterday",
    headline: "SPGX: SpaceX Stock Jumps 4% as Harvard, Nvidia, Norway Reveal Stakes",
  },
  {
    id: "4",
    source: "S",
    sourceColor: "#f97316",
    timeAgo: "yesterday",
    headline: "SMHX: Sandisk Jumps 9% as Anthropic's Revenue Run Rate Hits Warp Speed",
  },
  {
    id: "5",
    source: "R",
    sourceColor: "#fb923c",
    timeAgo: "4 days ago",
    headline: "RDDT: Reddit Stock Rockets 12% on S&P 500 Promotion. Passive Funds Must Buy",
  },
  {
    id: "6",
    source: "N",
    sourceColor: "#e50914",
    timeAgo: "4 days ago",
    headline: "NFLX: Netflix Stock Jumps 5% as Bill Ackman Returns for the Streaming Trade",
  },
  {
    id: "7",
    source: "A",
    sourceColor: "#555555",
    timeAgo: "5 days ago",
    headline: "AAPL: Apple Services Revenue Hits a Record as iPhone Cycle Steadies",
  },
  {
    id: "8",
    source: "N",
    sourceColor: "#76b900",
    timeAgo: "5 days ago",
    headline: "NVDA: Data-center demand cools for a session as buyers wait on earnings",
  },
];

export const SEARCH_UNIVERSE = [
  ...OVERVIEW_TABS.Financial,
  ...OVERVIEW_TABS.Technology,
  ...OVERVIEW_TABS.Services,
  { symbol: "NVDA", name: "NVIDIA", value: 118.42, change: -2.84, changePct: -2.34, open: 121.1, high: 122.4, low: 117.8, prev: 121.26 },
  { symbol: "TSLA", name: "Tesla", value: 248.9, change: 2.16, changePct: 0.88, open: 246.2, high: 251.3, low: 245.1, prev: 246.74 },
  { symbol: "AMD", name: "Advanced Micro Devices", value: 148.22, change: -6.61, changePct: -4.27, open: 154.1, high: 155.4, low: 147.3, prev: 154.83 },
].filter((row, index, arr) => arr.findIndex((r) => r.symbol === row.symbol) === index);
