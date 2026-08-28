"use client";

import { useCallback, useEffect, useState } from "react";
import { useT } from "@/components/LanguageProvider";
import {
  fetchAdminSettings,
  runAdminNewsJob,
  updateAdminSettings,
  type AdminJobRun,
  type AdminSettings,
} from "@/lib/admin-api";
import { AuthApiError } from "@/lib/auth";

type Props = {
  token: string;
  onNewsFetched?: (run: AdminJobRun) => void;
};

export default function JobControlsPanel({ token, onNewsFetched }: Props) {
  const t = useT();
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [fetching, setFetching] = useState(false);
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
    if (!settings || busy || fetching) return;
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

  const fetchNewsNow = async () => {
    if (fetching || busy) return;
    setFetching(true);
    setError(null);
    setNotice(null);
    try {
      const run = await runAdminNewsJob(token);
      const written = run.counts?.written;
      setNotice(
        t("admin.jobs.fetchDone")
          .replace("{status}", run.status)
          .replace("{written}", written === undefined ? "—" : String(written)),
      );
      onNewsFetched?.(run);
    } catch {
      setError(t("admin.jobs.fetchError"));
    } finally {
      setFetching(false);
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
        <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center">
          <label className="flex items-center gap-3 text-sm text-gray-100">
            <input
              type="checkbox"
              checked={Boolean(settings.jobs.news)}
              disabled={busy || fetching}
              aria-label={t("admin.jobs.news")}
              onChange={() => void toggleNews()}
            />
            {t("admin.jobs.news")}
          </label>
          <button
            type="button"
            disabled={busy || fetching}
            onClick={() => void fetchNewsNow()}
            className="rounded border border-teal-700/60 bg-teal-900/40 px-3 py-1.5 text-sm text-teal-100 disabled:opacity-50"
          >
            {fetching ? t("admin.jobs.fetching") : t("admin.jobs.fetchNow")}
          </button>
        </div>
      )}
    </section>
  );
}
