"use client";

import { RANGE_LABELS, type RangeKey } from "@/lib/mock-data";

export default function Sparkline({
  data,
  range,
  height = 168,
}: {
  data: number[];
  range: RangeKey;
  height?: number;
}) {
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
  const labels = RANGE_LABELS[range];

  return (
    <svg viewBox={`0 0 ${width} ${height + 22}`} className="h-auto w-full" role="img" aria-label="Price sparkline">
      <defs>
        <linearGradient id="artryx-spark-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0FEDBE" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#0FEDBE" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#artryx-spark-fill)" />
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
