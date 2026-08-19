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
