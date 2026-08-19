import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

function fractionDigits(value: number, fallback = 2) {
  const abs = Math.abs(value);
  if (abs > 0 && abs < 0.01) return 6;
  if (abs > 0 && abs < 1) return 4;
  return fallback;
}

export function formatPrice(value: number, digits?: number) {
  const max = digits ?? fractionDigits(value);
  const min = Math.min(2, max);
  return value.toLocaleString("en-US", {
    minimumFractionDigits: min,
    maximumFractionDigits: max,
  });
}

export function formatSigned(value: number, digits?: number) {
  const places = digits ?? fractionDigits(value);
  const abs = Math.abs(value).toFixed(places);
  if (value > 0) return `+${abs}`;
  if (value < 0) return `-${abs}`;
  return Number(0).toFixed(places);
}

export function formatPct(value: number, digits = 2) {
  return `${formatSigned(value, digits)}%`;
}

export function changeTone(value: number) {
  if (value > 0) return "up" as const;
  if (value < 0) return "down" as const;
  return "flat" as const;
}

export function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

export function lerpColor(from: [number, number, number], to: [number, number, number], t: number) {
  const r = Math.round(lerp(from[0], to[0], t));
  const g = Math.round(lerp(from[1], to[1], t));
  const b = Math.round(lerp(from[2], to[2], t));
  return `rgb(${r}, ${g}, ${b})`;
}

/** TradingView-style heatmap: deep red → near-black → deep green. */
export function heatmapColor(changePct: number, min = -5.5, max = 5.5) {
  const clamped = Math.max(min, Math.min(max, changePct));
  if (clamped < 0) {
    const t = clamped / min;
    return lerpColor([32, 32, 36], [122, 22, 32], t);
  }
  if (clamped > 0) {
    const t = clamped / max;
    return lerpColor([32, 32, 36], [14, 98, 56], t);
  }
  return "rgb(32, 32, 36)";
}
