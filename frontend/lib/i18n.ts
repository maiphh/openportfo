export const LANGUAGE_STORAGE_KEY = "openportfo.language";
export const LANGS = ["en", "vi"] as const;
export type Lang = (typeof LANGS)[number];
export const DEFAULT_LANG: Lang = "en";

export const DICTIONARY: Record<Lang, Record<string, string>> = {
  en: {
    "nav.market": "Market",
    "nav.market.stock": "Stock",
    "nav.market.crypto": "Crypto",
    "nav.portfolio": "Portfolio",
    "nav.watchlist": "Watchlist",
    "nav.search": "Search",
    "nav.collapse": "Collapse sidebar",
    "nav.expand": "Expand sidebar",
    "nav.openMenu": "Open navigation menu",
    "settings.title": "Settings",
    "settings.appearance": "Appearance",
    "settings.appearance.light": "Light",
    "settings.appearance.dark": "Dark",
    "settings.language": "Language",
    "settings.language.en": "English",
    "settings.language.vi": "Tiếng Việt",
    "settings.currency": "Display currency",
    "settings.fxRates": "View FX rates…",
    "settings.account.guest": "Guest",
    "settings.account.signedOut": "Not signed in",
    "settings.signIn": "Sign in",
    "settings.signOut": "Sign out",
    "common.close": "Close",
    "search.placeholder": "Search symbols or companies",
  },
  vi: {
    "nav.market": "Thị trường",
    "nav.market.stock": "Cổ phiếu",
    "nav.market.crypto": "Tiền mã hóa",
    "nav.portfolio": "Danh mục",
    "nav.watchlist": "Theo dõi",
    "nav.search": "Tìm kiếm",
    "nav.collapse": "Thu gọn thanh bên",
    "nav.expand": "Mở rộng thanh bên",
    "nav.openMenu": "Mở menu điều hướng",
    "settings.title": "Cài đặt",
    "settings.appearance": "Giao diện",
    "settings.appearance.light": "Sáng",
    "settings.appearance.dark": "Tối",
    "settings.language": "Ngôn ngữ",
    "settings.language.en": "English",
    "settings.language.vi": "Tiếng Việt",
    "settings.currency": "Tiền tệ hiển thị",
    "settings.fxRates": "Xem tỷ giá…",
    "settings.account.guest": "Khách",
    "settings.account.signedOut": "Chưa đăng nhập",
    "settings.signIn": "Đăng nhập",
    "settings.signOut": "Đăng xuất",
    "common.close": "Đóng",
    "search.placeholder": "Tìm mã cổ phiếu hoặc công ty",
  },
};

export function resolveLang(raw: string | null): Lang {
  return raw === "vi" ? "vi" : DEFAULT_LANG;
}

export function translate(lang: Lang, key: string): string {
  return DICTIONARY[lang]?.[key] ?? DICTIONARY.en[key] ?? key;
}

export function readStoredLang(
  storage?: Pick<Storage, "getItem"> | null,
): Lang {
  let source = storage;
  if (source === undefined && typeof window !== "undefined") {
    try { source = window.localStorage; } catch { source = null; }
  }
  try {
    return resolveLang(source?.getItem(LANGUAGE_STORAGE_KEY) ?? null);
  } catch {
    return DEFAULT_LANG;
  }
}

export function writeStoredLang(
  lang: Lang,
  storage?: Pick<Storage, "setItem"> | null,
): void {
  let target = storage;
  if (target === undefined && typeof window !== "undefined") {
    try { target = window.localStorage; } catch { target = null; }
  }
  try {
    target?.setItem(LANGUAGE_STORAGE_KEY, lang);
  } catch {
    // Preference remains active in memory for this session.
  }
}
