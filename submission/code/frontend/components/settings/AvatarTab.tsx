"use client";

import { useEffect, useMemo, useState } from "react";
import UserAvatar from "@/components/UserAvatar";
import { useT } from "@/components/LanguageProvider";
import { AVATAR_STYLES, type AvatarStyle } from "@/lib/avatar";
import { updateUserSettings } from "@/lib/settings-api";
import type { AuthProfileController } from "@/lib/use-auth-profile";
import { normalizeAvatarColor, normalizeAvatarSeed, validAvatarColor, validAvatarSeed } from "@/lib/user-settings-schema";

function randomSeed(): string {
  const bytes = new Uint32Array(2);
  if (typeof crypto !== "undefined" && crypto.getRandomValues) crypto.getRandomValues(bytes);
  else bytes[0] = Math.floor(Math.random() * 0xffffffff);
  return Array.from(bytes, (value) => value.toString(36)).join("");
}

export default function AvatarTab({ auth }: { auth: AuthProfileController }) {
  const t = useT();
  const profile = auth.profile;
  const [style, setStyle] = useState<AvatarStyle | null>((profile?.avatarStyle as AvatarStyle) || null);
  const [seed, setSeed] = useState(profile?.avatarSeed ?? "");
  const [color, setColor] = useState(profile?.avatarColor ? `#${profile.avatarColor}` : "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setStyle((profile?.avatarStyle as AvatarStyle) || null);
    setSeed(profile?.avatarSeed ?? "");
    setColor(profile?.avatarColor ? `#${profile.avatarColor}` : "");
  }, [profile?.avatarColor, profile?.avatarSeed, profile?.avatarStyle]);

  const preview = useMemo(
    () => profile
      ? { ...profile, avatarStyle: style ?? "notionists", avatarSeed: seed || null, avatarColor: color.replace(/^#/, "") || null }
      : null,
    [color, profile, seed, style],
  );
  const dirty = style !== ((profile?.avatarStyle as AvatarStyle) || null)
    || seed !== (profile?.avatarSeed ?? "")
    || color.replace(/^#/, "").toLowerCase() !== (profile?.avatarColor ?? "");
  const valid = validAvatarSeed(seed) && validAvatarColor(color);

  const save = async () => {
    if (!auth.token || busy || !dirty) return;
    setBusy(true); setError(null); setSuccess(false);
    try {
      const updated = await updateUserSettings(auth.token, {
        avatarStyle: style,
        avatarSeed: normalizeAvatarSeed(seed) || null,
        avatarColor: normalizeAvatarColor(color),
      });
      auth.replaceProfile(updated);
      setSuccess(true);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : t("settings.saveError"));
    } finally { setBusy(false); }
  };

  const useDefault = () => {
    setStyle(null);
    setSeed("");
    setColor("");
    setError(null);
    setSuccess(false);
  };
  const revertEdits = () => {
    setStyle((profile?.avatarStyle as AvatarStyle) || null);
    setSeed(profile?.avatarSeed ?? "");
    setColor(profile?.avatarColor ? `#${profile.avatarColor}` : "");
    setError(null);
    setSuccess(false);
  };
  return (
    <div className="space-y-5" aria-busy={busy}>
      <div className="flex items-center gap-4 rounded-xl border border-gray-700 bg-gray-900/40 p-4"><UserAvatar profile={preview} className="h-20 w-20" /><div><p className="text-sm font-medium text-gray-100">{t("settings.avatarPreview")}</p><p className="text-xs text-gray-500">{t("settings.avatarPreviewHint")}</p></div></div>
      <fieldset><legend className="mb-2 text-sm font-medium text-gray-200">{t("settings.avatarStyle")}</legend><div role="radiogroup" aria-label={t("settings.avatarStyle")} className="grid grid-cols-2 gap-2 sm:grid-cols-4">{AVATAR_STYLES.map((candidate) => { const selected = (style ?? "notionists") === candidate; return <button key={candidate} type="button" role="radio" aria-checked={selected} onClick={() => setStyle(candidate)} className={`rounded-md border px-2 py-2 text-xs ${selected ? "border-teal-400 text-teal-200" : "border-gray-700 text-gray-400"}`}>{candidate}</button>; })}</div></fieldset>
      <div><label htmlFor="avatar-seed" className="mb-1 block text-sm font-medium text-gray-200">{t("settings.avatarSeed")}</label><div className="flex gap-2"><input id="avatar-seed" value={seed} maxLength={64} onChange={(event) => setSeed(event.target.value)} aria-invalid={!validAvatarSeed(seed)} aria-describedby={!validAvatarSeed(seed) ? "avatar-seed-error" : undefined} className="min-w-0 flex-1 rounded-md border border-gray-600 bg-gray-900 px-3 py-2 text-gray-100" /><button type="button" onClick={() => setSeed(randomSeed())} className="rounded-md border border-gray-600 px-3 py-2 text-sm text-gray-200">{t("settings.randomize")}</button></div>{!validAvatarSeed(seed) ? <p id="avatar-seed-error" role="alert" className="mt-1 text-xs text-red-300">{t("settings.invalidAvatar")}</p> : null}</div>
      <div><label htmlFor="avatar-color" className="mb-1 block text-sm font-medium text-gray-200">{t("settings.avatarColor")}</label><div className="flex items-center gap-2"><input id="avatar-color" type="color" value={/^#[0-9a-f]{6}$/i.test(color) ? color : "#14b8a6"} onChange={(event) => setColor(event.target.value)} aria-label={t("settings.avatarColor")} aria-invalid={!validAvatarColor(color)} aria-describedby={!validAvatarColor(color) ? "avatar-color-error" : undefined} /><button type="button" onClick={() => setColor("")} className="rounded-md border border-gray-600 px-3 py-2 text-sm text-gray-200">{t("settings.clear")}</button></div>{!validAvatarColor(color) ? <p id="avatar-color-error" role="alert" className="mt-1 text-xs text-red-300">{t("settings.invalidAvatar")}</p> : null}</div>
      {error ? <p role="alert" className="text-sm text-red-300">{error}</p> : null}{success ? <p role="status" className="text-sm text-teal-300">{t("settings.saved")}</p> : null}
      <div className="flex flex-wrap gap-2"><button type="button" disabled={!dirty || !valid || busy} onClick={() => void save()} className="rounded-md bg-teal-400 px-4 py-2 text-sm font-medium text-teal-950 disabled:opacity-50">{busy ? t("settings.saving") : t("settings.save")}</button><button type="button" disabled={busy} onClick={useDefault} className="rounded-md border border-gray-600 px-4 py-2 text-sm text-gray-200">{t("settings.useDefault")}</button><button type="button" disabled={busy || !dirty} onClick={revertEdits} className="rounded-md border border-gray-600 px-4 py-2 text-sm text-gray-200">{t("settings.revert")}</button></div>
    </div>
  );
}
