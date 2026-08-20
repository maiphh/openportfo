import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export {
  displayFractionDigits,
  formatPct,
  formatPrice,
  formatMoney,
  formatQty,
  formatSigned,
} from "./number-format";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
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
