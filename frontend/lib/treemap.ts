export type TreemapInput = {
  id: string;
  value: number;
  children?: TreemapInput[];
  symbol?: string;
  changePct?: number;
  sector?: string;
};

export type TreemapRect = {
  id: string;
  value: number;
  x: number;
  y: number;
  width: number;
  height: number;
  children?: TreemapRect[];
  symbol?: string;
  changePct?: number;
  sector?: string;
};

type Box = { x: number; y: number; w: number; h: number };

function worst(row: number[], side: number) {
  if (row.length === 0 || side <= 0) return Infinity;
  const sum = row.reduce((a, b) => a + b, 0);
  const max = Math.max(...row);
  const min = Math.min(...row);
  return Math.max((side * side * max) / (sum * sum), (sum * sum) / (side * side * min));
}

function toRect(node: TreemapInput, x: number, y: number, width: number, height: number): TreemapRect {
  return {
    id: node.id,
    value: node.value,
    x,
    y,
    width,
    height,
    symbol: node.symbol,
    changePct: node.changePct,
    sector: node.sector,
  };
}

function layoutRow(row: TreemapInput[], box: Box, vertical: boolean): TreemapRect[] {
  const sum = row.reduce((a, n) => a + n.value, 0);
  const { x, y, w, h } = box;
  let cursor = vertical ? y : x;

  return row.map((node) => {
    if (vertical) {
      const height = (node.value / sum) * h;
      const rect = toRect(node, x, cursor, w, height);
      cursor += height;
      return rect;
    }
    const width = (node.value / sum) * w;
    const rect = toRect(node, cursor, y, width, h);
    cursor += width;
    return rect;
  });
}

function squarify(nodes: TreemapInput[], box: Box): TreemapRect[] {
  if (nodes.length === 0 || box.w <= 0 || box.h <= 0) return [];

  const total = nodes.reduce((a, n) => a + n.value, 0);
  if (total <= 0) return [];

  const scaled = nodes
    .map((n) => ({ ...n, value: (n.value / total) * box.w * box.h }))
    .filter((n) => n.value > 0)
    .sort((a, b) => b.value - a.value);

  const placed: TreemapRect[] = [];
  let row: TreemapInput[] = [];
  let rest = scaled;
  let remaining = { ...box };

  const flush = () => {
    if (row.length === 0) return;
    const rowArea = row.reduce((a, n) => a + n.value, 0);
    const vertical = remaining.w >= remaining.h;
    const side = vertical ? remaining.h : remaining.w;
    const thickness = rowArea / side;
    const rowBox = vertical
      ? { x: remaining.x, y: remaining.y, w: thickness, h: remaining.h }
      : { x: remaining.x, y: remaining.y, w: remaining.w, h: thickness };
    placed.push(...layoutRow(row, rowBox, vertical));
    remaining = vertical
      ? { x: remaining.x + thickness, y: remaining.y, w: remaining.w - thickness, h: remaining.h }
      : { x: remaining.x, y: remaining.y + thickness, w: remaining.w, h: remaining.h - thickness };
    row = [];
  };

  while (rest.length > 0) {
    const next = rest[0];
    const side = Math.min(remaining.w, remaining.h);
    const candidate = [...row, next];
    if (
      row.length === 0 ||
      worst(
        candidate.map((n) => n.value),
        side,
      ) <=
        worst(
          row.map((n) => n.value),
          side,
        )
    ) {
      row = candidate;
      rest = rest.slice(1);
    } else {
      flush();
    }
  }
  flush();
  return placed;
}

function applyGap(rect: TreemapRect, gap: number): TreemapRect {
  const g = gap / 2;
  return {
    ...rect,
    x: rect.x + g,
    y: rect.y + g,
    width: Math.max(0, rect.width - gap),
    height: Math.max(0, rect.height - gap),
  };
}

export function layoutTreemap(nodes: TreemapInput[], width: number, height: number, gap = 2): TreemapRect[] {
  return squarify(nodes, { x: 0, y: 0, w: width, h: height }).map((node) => {
    const source = nodes.find((n) => n.id === node.id);
    const gapped = applyGap(node, gap);
    if (source?.children?.length) {
      const label = Math.min(18, Math.max(0, gapped.height * 0.12));
      const childGap = Math.max(1, gap * 0.6);
      const innerH = Math.max(0, gapped.height - label);
      gapped.children = layoutTreemap(source.children, gapped.width, innerH, childGap).map((child) => ({
        ...child,
        x: child.x + gapped.x,
        y: child.y + gapped.y + label,
      }));
    }
    return gapped;
  });
}
