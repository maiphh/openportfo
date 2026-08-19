"use client";

import type { ChartRange } from "@/lib/asset";

const RANGE_AXIS: Record<ChartRange, string[]> = {
  "7d": ["7d ago", "Now"],
  "30d": ["30d ago", "Now"],
  "90d": ["90d ago", "Now"],
  "1y": ["1y ago", "Now"],
};

export default function AssetHistoryChart({
  data,
  range,
  height = 200,
}: {
  data: number[];
  range: ChartRange;
  height?: number;
}) {
  if (data.length < 2) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-gray-600 bg-gray-900/40 text-sm text-gray-500"
        style={{ height }}
      >
        No chart data for this range.
      </div>
    );
  }

  const width = 640;
  const padX = 8;
  const padY = 12;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = Math.max(max - min, 0.0001);

  const points = data.map((value, i) => {
    const x = padX + (i / Math.max(data.length - 1, 1)) * (width - padX * 2);
    const y = padY + (1 - (value - min) / span) * (height - padY * 2);
    return { x, y };
  });

  const line = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" ");
  const area = `${line} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z`;
  const labels = RANGE_AXIS[range];

  return (
    <svg viewBox={`0 0 ${width} ${height + 22}`} className="h-auto w-full" role="img" aria-label="Asset price history">
      <defs>
        <linearGradient id="asset-history-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0FEDBE" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#0FEDBE" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#asset-history-fill)" />
      <path d={line} fill="none" stroke="#0FEDBE" strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
      {labels.map((label, i) => {
        const x = padX + (i / Math.max(labels.length - 1, 1)) * (width - padX * 2);
        return (
          <text key={label} x={x} y={height + 16} textAnchor="middle" fill="#9095A1" fontSize="11">
            {label}
          </text>
        );
      })}
    </svg>
  );
}
