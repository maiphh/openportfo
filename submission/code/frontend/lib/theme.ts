export const THEME_STORAGE_KEY = "openportfo.theme";
export type Theme = "light" | "dark";
export const DEFAULT_THEME: Theme = "dark";

export function resolveTheme(raw: string | null): Theme {
  return raw === "light" ? "light" : DEFAULT_THEME;
}

export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function readStoredTheme(
  storage?: Pick<Storage, "getItem"> | null,
): Theme {
  let source = storage;
  if (source === undefined && typeof window !== "undefined") {
    try { source = window.localStorage; } catch { source = null; }
  }
  try {
    return resolveTheme(source?.getItem(THEME_STORAGE_KEY) ?? null);
  } catch {
    return DEFAULT_THEME;
  }
}

export function writeStoredTheme(
  theme: Theme,
  storage?: Pick<Storage, "setItem"> | null,
): void {
  let target = storage;
  if (target === undefined && typeof window !== "undefined") {
    try { target = window.localStorage; } catch { target = null; }
  }
  try {
    target?.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Preference remains active in memory for this session.
  }
}
