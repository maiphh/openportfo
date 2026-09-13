"use client";

import { useCallback, useEffect, useState } from "react";
import { useT } from "@/components/LanguageProvider";
import {
  createAdminRssSource,
  deleteAdminRssSource,
  fetchAdminRssSources,
  updateAdminRssSource,
  type AdminRssSource,
} from "@/lib/admin-api";
import { AuthApiError } from "@/lib/auth";

function isPublicHttpUrl(raw: string): boolean {
  try {
    const parsed = new URL(raw.trim());
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export default function RssSourcesPanel({ token }: { token: string }) {
  const t = useT();
  const [sources, setSources] = useState<AdminRssSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSources(await fetchAdminRssSources(token));
    } catch (reason: unknown) {
      if (reason instanceof AuthApiError && reason.status === 403) {
        setError(t("admin.rss.forbidden"));
      } else {
        setError(t("admin.rss.loadError"));
      }
    } finally {
      setLoading(false);
    }
  }, [t, token]);

  useEffect(() => {
    void load();
  }, [load]);

  const addSource = async () => {
    const trimmedName = name.trim();
    const trimmedUrl = url.trim();
    if (!trimmedName || !isPublicHttpUrl(trimmedUrl)) {
      setError(t("admin.rss.validationError"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await createAdminRssSource(token, {
        name: trimmedName,
        url: trimmedUrl,
        enabled: true,
      });
      setSources((current) => [...current, created]);
      setName("");
      setUrl("");
    } catch (reason: unknown) {
      if (reason instanceof AuthApiError && reason.status === 400) {
        setError(t("admin.rss.validationError"));
      } else if (reason instanceof AuthApiError && reason.status === 403) {
        setError(t("admin.rss.forbidden"));
      } else {
        setError(t("admin.rss.saveError"));
      }
    } finally {
      setBusy(false);
    }
  };

  const toggleEnabled = async (source: AdminRssSource) => {
    setError(null);
    const optimistic = { ...source, enabled: !source.enabled };
    setSources((current) =>
      current.map((item) => (item.sourceId === source.sourceId ? optimistic : item)),
    );
    try {
      const next = await updateAdminRssSource(token, source.sourceId, {
        enabled: optimistic.enabled,
      });
      setSources((current) =>
        current.map((item) => (item.sourceId === next.sourceId ? next : item)),
      );
    } catch {
      setSources((current) =>
        current.map((item) => (item.sourceId === source.sourceId ? source : item)),
      );
      setError(t("admin.rss.saveError"));
    }
  };

  const remove = async (source: AdminRssSource) => {
    setBusy(true);
    setError(null);
    try {
      await deleteAdminRssSource(token, source.sourceId);
      setSources((current) => current.filter((item) => item.sourceId !== source.sourceId));
    } catch {
      setError(t("admin.rss.saveError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="space-y-4 rounded-xl border border-gray-700 bg-gray-800 p-4" aria-labelledby="admin-rss-heading">
      <div>
        <h2 id="admin-rss-heading" className="text-xl font-semibold text-gray-100">
          {t("admin.rss.title")}
        </h2>
        <p className="mt-1 text-sm text-gray-500">{t("admin.rss.subtitle")}</p>
      </div>
      {error ? (
        <p role="alert" className="text-sm text-red-300">
          {error}
        </p>
      ) : null}
      {loading ? (
        <p aria-busy="true" className="text-sm text-gray-400">
          {t("admin.rss.loading")}
        </p>
      ) : sources.length === 0 ? (
        <p className="text-sm text-gray-400">{t("admin.rss.empty")}</p>
      ) : (
        <ul className="space-y-3">
          {sources.map((source) => (
            <li
              key={source.sourceId}
              className="flex flex-col gap-2 border-b border-gray-700 pb-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <p className="font-medium text-gray-100">{source.name}</p>
                <p className="truncate text-xs text-gray-500">{source.url}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-2 text-sm text-gray-200">
                  <input
                    type="checkbox"
                    checked={source.enabled}
                    aria-label={`${t("admin.rss.enabled")} ${source.name}`}
                    onChange={() => void toggleEnabled(source)}
                  />
                  {t("admin.rss.enabled")}
                </label>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void remove(source)}
                  className="rounded border border-gray-600 px-3 py-1 text-sm text-gray-200 disabled:opacity-50"
                >
                  {t("admin.rss.delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <form
        className="grid gap-3 sm:grid-cols-[1fr_2fr_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          void addSource();
        }}
      >
        <label className="text-sm text-gray-200">
          {t("admin.rss.name")}
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-1 w-full rounded border border-gray-600 bg-gray-900 px-2 py-2 text-gray-100"
            autoComplete="off"
          />
        </label>
        <label className="text-sm text-gray-200">
          {t("admin.rss.url")}
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            className="mt-1 w-full rounded border border-gray-600 bg-gray-900 px-2 py-2 text-gray-100"
            inputMode="url"
            autoComplete="off"
          />
        </label>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded bg-teal-400 px-4 py-2 text-sm font-medium text-teal-950 disabled:opacity-50 sm:w-auto"
          >
            {t("admin.rss.add")}
          </button>
        </div>
      </form>
    </section>
  );
}
