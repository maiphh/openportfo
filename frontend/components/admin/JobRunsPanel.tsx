"use client";

import { useCallback, useEffect, useState } from "react";
import { useT } from "@/components/LanguageProvider";
import { fetchAdminJobRuns, type AdminJobRun } from "@/lib/admin-api";

function formatCounts(counts: Record<string, unknown>): string {
  const keys = ["written", "fetched", "sources_succeeded", "sources_failed", "sources_attempted"];
  const parts = keys
    .filter((key) => counts[key] !== undefined)
    .map((key) => `${key}=${String(counts[key])}`);
  return parts.length ? parts.join(", ") : "—";
}

export default function JobRunsPanel({ token }: { token: string }) {
  const t = useT();
  const [runs, setRuns] = useState<AdminJobRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRuns(await fetchAdminJobRuns(token, { jobType: "news", limit: 20 }));
    } catch {
      setError(t("admin.runs.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t, token]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="space-y-4 rounded-xl border border-gray-700 bg-gray-800 p-4" aria-labelledby="admin-runs-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="admin-runs-heading" className="text-xl font-semibold text-gray-100">
            {t("admin.runs.title")}
          </h2>
          <p className="mt-1 text-sm text-gray-500">{t("admin.runs.subtitle")}</p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded border border-gray-600 px-3 py-1 text-sm text-gray-200"
        >
          {t("admin.runs.refresh")}
        </button>
      </div>
      {error ? (
        <p role="alert" className="text-sm text-red-300">
          {error}
        </p>
      ) : null}
      {loading ? (
        <p aria-busy="true" className="text-sm text-gray-400">
          {t("admin.runs.loading")}
        </p>
      ) : runs.length === 0 ? (
        <p className="text-sm text-gray-400">{t("admin.runs.empty")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <caption className="sr-only">{t("admin.runs.title")}</caption>
            <thead className="border-b border-gray-700 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-2 py-2">{t("admin.runs.status")}</th>
                <th className="px-2 py-2">{t("admin.runs.started")}</th>
                <th className="px-2 py-2">{t("admin.runs.counts")}</th>
                <th className="px-2 py-2">{t("admin.runs.message")}</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.runId} className="border-b border-gray-700 align-top">
                  <td className="px-2 py-2 text-gray-100">{run.status}</td>
                  <td className="px-2 py-2 text-gray-400">{run.startedAt || "—"}</td>
                  <td className="px-2 py-2 text-gray-300">{formatCounts(run.counts)}</td>
                  <td className="px-2 py-2 text-gray-400">{run.message || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
