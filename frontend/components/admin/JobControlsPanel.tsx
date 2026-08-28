"use client";

import { useCallback, useEffect, useState } from "react";
import { useT } from "@/components/LanguageProvider";
import {
  fetchAdminSettings,
  updateAdminSettings,
  type AdminSettings,
} from "@/lib/admin-api";
import { AuthApiError } from "@/lib/auth";

export default function JobControlsPanel({ token }: { token: string }) {
  const t = useT();
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSettings(await fetchAdminSettings(token));
    } catch {
      setError(t("admin.jobs.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t, token]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleNews = async () => {
    if (!settings || busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    const nextEnabled = !Boolean(settings.jobs.news);
    const optimistic = {
      ...settings,
      jobs: { ...settings.jobs, news: nextEnabled },
    };
    setSettings(optimistic);
    try {
      const updated = await updateAdminSettings(token, settings.version, {
        jobs: { news: nextEnabled },
      });
      setSettings(updated);
    } catch (reason: unknown) {
      if (reason instanceof AuthApiError && reason.status === 409) {
        setNotice(t("admin.jobs.conflict"));
        try {
          setSettings(await fetchAdminSettings(token));
        } catch {
          setError(t("admin.jobs.loadError"));
        }
      } else {
        setSettings(settings);
        setError(t("admin.jobs.saveError"));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="space-y-4 rounded-xl border border-gray-700 bg-gray-800 p-4" aria-labelledby="admin-jobs-heading">
      <div>
        <h2 id="admin-jobs-heading" className="text-xl font-semibold text-gray-100">
          {t("admin.jobs.title")}
        </h2>
        <p className="mt-1 text-sm text-gray-500">{t("admin.jobs.subtitle")}</p>
      </div>
      {error ? (
        <p role="alert" className="text-sm text-red-300">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p role="status" className="text-sm text-amber-200">
          {notice}
        </p>
      ) : null}
      {loading || !settings ? (
        <p aria-busy="true" className="text-sm text-gray-400">
          {t("admin.jobs.loading")}
        </p>
      ) : (
        <label className="flex items-center gap-3 text-sm text-gray-100">
          <input
            type="checkbox"
            checked={Boolean(settings.jobs.news)}
            aria-label={t("admin.jobs.news")}
            onChange={() => void toggleNews()}
          />
          {t("admin.jobs.news")}
        </label>
      )}
    </section>
  );
}
