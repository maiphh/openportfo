"use client";

import { useEffect, useRef, useState } from "react";
import { useT } from "@/components/LanguageProvider";
import UserAvatar from "@/components/UserAvatar";
import { updateAdminUserSettings, type AdminUserRow } from "@/lib/admin-api";
import { AuthApiError } from "@/lib/auth";
import type { UserSettingsPatch } from "@/lib/settings-api";
import type { AuthProfileController } from "@/lib/use-auth-profile";
import {
  AVATAR_STYLES,
  normalizeAvatarColor,
  normalizeAvatarSeed,
  normalizeKeywordList,
  validAvatarColor,
  validAvatarSeed,
  validKeywordList,
} from "@/lib/user-settings-schema";

export default function AdminUserEditor({
  auth,
  user,
  onClose,
  onSaved,
}: {
  auth: AuthProfileController;
  user: AdminUserRow;
  onClose: () => void;
  onSaved: (next: AdminUserRow) => void;
}) {
  const t = useT();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [keywords, setKeywords] = useState((user.newsKeywords ?? []).join(", "));
  const [emailOptIn, setEmailOptIn] = useState(user.emailOptIn ?? false);
  const [currency, setCurrency] = useState(user.preferredCurrency ?? "");
  const [style, setStyle] = useState(user.avatarStyle ?? "");
  const [seed, setSeed] = useState(user.avatarSeed ?? "");
  const [color, setColor] = useState(user.avatarColor ? `#${user.avatarColor}` : "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  const keywordValues = keywords.trim() ? keywords.split(",").map((item) => item.trim()) : [];
  const valid = validKeywordList(keywordValues)
    && validAvatarSeed(seed)
    && validAvatarColor(color)
    && (style === "" || (AVATAR_STYLES as readonly string[]).includes(style));
  const save = async () => {
    if (!auth.token || busy || !valid) return;
    setBusy(true);
    setError(null);
    const patch: UserSettingsPatch = {
      newsKeywords: normalizeKeywordList(keywordValues),
      emailOptIn,
      preferredCurrency: currency === "USD" || currency === "VND" || currency === "EUR" ? currency : null,
      avatarStyle: style || null,
      avatarSeed: normalizeAvatarSeed(seed) || null,
      avatarColor: normalizeAvatarColor(color),
    };
    try {
      onSaved(await updateAdminUserSettings(auth.token, user.userId, patch));
    } catch (reason: unknown) {
      setError(reason instanceof AuthApiError ? t("admin.settingsError") : t("admin.settingsError"));
    } finally {
      setBusy(false);
    }
  };

  const errorId = "admin-user-settings-error";
  return (
    <aside className="mt-3 rounded-lg border border-gray-600 bg-gray-900/60 p-4" aria-label={t("admin.editUser")} aria-busy={busy}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3"><UserAvatar profile={user} /><div><h3 ref={headingRef} tabIndex={-1} className="font-medium text-gray-100">{user.name || user.email || user.userId}</h3><p className="text-xs text-gray-500">{user.email}</p></div></div>
        <button type="button" onClick={onClose} className="text-sm text-gray-400 underline">{t("common.close")}</button>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="text-sm text-gray-200">{t("settings.currency")}<select value={currency} onChange={(event) => setCurrency(event.target.value)} className="mt-1 w-full rounded border border-gray-600 bg-gray-800 px-2 py-2"><option value="">—</option><option>USD</option><option>VND</option><option>EUR</option></select></label>
        <label className="flex items-end gap-2 text-sm text-gray-200"><input type="checkbox" checked={emailOptIn} onChange={(event) => setEmailOptIn(event.target.checked)} /> {t("settings.emailOptIn")}</label>
        <label className="text-sm text-gray-200">{t("settings.keywords")}<input value={keywords} onChange={(event) => setKeywords(event.target.value)} aria-invalid={!validKeywordList(keywordValues)} aria-describedby={!validKeywordList(keywordValues) ? errorId : undefined} className="mt-1 w-full rounded border border-gray-600 bg-gray-800 px-2 py-2" /></label>
        <label className="text-sm text-gray-200">{t("settings.avatarSeed")}<input value={seed} maxLength={64} onChange={(event) => setSeed(event.target.value)} aria-invalid={!validAvatarSeed(seed)} aria-describedby={!validAvatarSeed(seed) ? errorId : undefined} className="mt-1 w-full rounded border border-gray-600 bg-gray-800 px-2 py-2" /></label>
        <label className="text-sm text-gray-200">{t("settings.avatarStyle")}<select value={style} onChange={(event) => setStyle(event.target.value)} aria-invalid={style !== "" && !(AVATAR_STYLES as readonly string[]).includes(style)} aria-describedby={style !== "" && !(AVATAR_STYLES as readonly string[]).includes(style) ? errorId : undefined} className="mt-1 w-full rounded border border-gray-600 bg-gray-800 px-2 py-2"><option value="">—</option>{AVATAR_STYLES.map((candidate) => <option key={candidate} value={candidate}>{candidate}</option>)}</select></label>
        <label className="text-sm text-gray-200">{t("settings.avatarColor")}<input value={color} onChange={(event) => setColor(event.target.value)} aria-invalid={!validAvatarColor(color)} aria-describedby={!validAvatarColor(color) ? errorId : undefined} className="mt-1 w-full rounded border border-gray-600 bg-gray-800 px-2 py-2" /></label>
      </div>
      {!valid ? <p id={errorId} role="alert" className="mt-3 text-sm text-red-300">{t("settings.invalidAvatar")}</p> : null}
      {error ? <p role="alert" className="mt-3 text-sm text-red-300">{error}</p> : null}
      <button type="button" disabled={busy || !valid} onClick={() => void save()} className="mt-4 rounded bg-teal-400 px-3 py-2 text-sm font-medium text-teal-950 disabled:opacity-50">{busy ? t("settings.saving") : t("settings.save")}</button>
    </aside>
  );
}
