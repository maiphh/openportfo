"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useT } from "@/components/LanguageProvider";
import UserAvatar from "@/components/UserAvatar";
import AdminUserEditor from "@/components/admin/AdminUserEditor";
import JobControlsPanel from "@/components/admin/JobControlsPanel";
import JobRunsPanel from "@/components/admin/JobRunsPanel";
import RssSourcesPanel from "@/components/admin/RssSourcesPanel";
import { fetchAdminUsers, updateAdminUserRole, type AdminUserRow } from "@/lib/admin-api";
import { AuthApiError } from "@/lib/auth";
import { useAuthProfile } from "@/lib/use-auth-profile";

export default function AdminPageClient() {
  const t = useT();
  const auth = useAuthProfile();
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [rowError, setRowError] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<string | null>(null);
  const [runsRefreshKey, setRunsRefreshKey] = useState(0);
  const editButtons = useRef<Record<string, HTMLButtonElement | null>>({});
  const loadingRef = useRef(false);

  const roleErrorMessage = (reason: unknown) => {
    if (!(reason instanceof AuthApiError)) return t("admin.roleError");
    if (reason.message === "whitelist_admin") return t("admin.whitelistError");
    if (reason.message === "last_admin") return t("admin.lastAdminError");
    if (reason.message === "role_conflict") return t("admin.conflictError");
    return t("admin.roleError");
  };

  const load = useCallback(async (nextCursor: string | null = null) => {
    if (!auth.token || auth.profile?.role !== "admin" || loadingRef.current) return;
    loadingRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const page = await fetchAdminUsers(auth.token, { limit: 25, cursor: nextCursor });
      setUsers((current) => {
        const merged = nextCursor ? [...current, ...page.items] : page.items;
        const seen = new Set<string>();
        return merged.filter((item) => !seen.has(item.userId) && seen.add(item.userId));
      });
      setCursor(page.nextCursor);
    } catch {
      setError(t("admin.loadError"));
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [auth.profile?.role, auth.token, t]);

  useEffect(() => {
    if (auth.profile?.role === "admin") void load();
  }, [auth.profile?.role, load]);

  if (!auth.hydrated || (auth.loading && !auth.profile)) {
    return (
      <div aria-busy="true" className="mx-auto max-w-6xl animate-pulse px-4">
        <div className="h-8 w-48 rounded bg-gray-700" />
        <div className="mt-6 h-72 rounded bg-gray-800" />
      </div>
    );
  }
  if (!auth.token || !auth.profile) {
    return (
      <section className="mx-auto max-w-xl rounded-xl border border-gray-700 bg-gray-800 p-8 text-center">
        <h1 className="text-2xl font-semibold text-gray-100">{t("admin.title")}</h1>
        <p className="mt-3 text-sm text-gray-400">{t("settings.signInPrompt")}</p>
        {auth.cognitoConfigured ? (
          <button
            type="button"
            onClick={() => void auth.signIn("/admin")}
            className="mt-6 rounded bg-teal-400 px-4 py-2 text-teal-950"
          >
            {t("settings.signIn")}
          </button>
        ) : null}
      </section>
    );
  }
  if (auth.profile.role !== "admin") {
    return (
      <section className="mx-auto max-w-xl rounded-xl border border-red-900/50 bg-gray-800 p-8 text-center">
        <h1 className="text-2xl font-semibold text-gray-100">{t("admin.title")}</h1>
        <p role="alert" className="mt-3 text-sm text-red-300">{t("admin.forbidden")}</p>
      </section>
    );
  }
  const accessToken = auth.token;

  const updateRole = async (user: AdminUserRow, role: "user" | "admin") => {
    if (busy[user.userId] || user.roleManagedByEnv) return;
    setBusy((current) => ({ ...current, [user.userId]: true }));
    setRowError((current) => ({ ...current, [user.userId]: "" }));
    try {
      const next = await updateAdminUserRole(accessToken, user.userId, role);
      setUsers((current) => current.map((item) => (item.userId === next.userId ? next : item)));
      if (next.isCurrentUser) auth.replaceProfile(next);
    } catch (reason: unknown) {
      setRowError((current) => ({ ...current, [user.userId]: roleErrorMessage(reason) }));
      if (reason instanceof AuthApiError && reason.status === 409) {
        window.setTimeout(() => void load(null), 0);
      }
    } finally {
      setBusy((current) => ({ ...current, [user.userId]: false }));
    }
  };

  return (
    <section className="mx-auto max-w-6xl space-y-6 px-4">
      <div>
        <h1 className="text-3xl font-semibold text-gray-100">{t("admin.title")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("admin.subtitle")}</p>
      </div>
      {error ? <p role="alert" className="text-sm text-red-300">{error}</p> : null}
      <div className="overflow-x-auto rounded-xl border border-gray-700 bg-gray-800">
        <table className="w-full min-w-[680px] text-left text-sm">
          <caption className="sr-only">{t("admin.title")}</caption>
          <thead className="border-b border-gray-700 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">{t("admin.user")}</th>
              <th className="px-4 py-3">{t("admin.role")}</th>
              <th className="px-4 py-3">{t("admin.created")}</th>
              <th className="px-4 py-3">{t("admin.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.userId} className="border-b border-gray-700 align-top">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <UserAvatar profile={user} />
                    <div>
                      <p className="font-medium text-gray-100">{user.name || user.email || user.userId}</p>
                      <p className="text-xs text-gray-500">{user.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <select
                    aria-label={`${t("admin.role")} ${user.email || user.userId}`}
                    value={user.role}
                    disabled={Boolean(busy[user.userId]) || user.roleManagedByEnv}
                    onChange={(event) => void updateRole(user, event.target.value as "user" | "admin")}
                    className="rounded border border-gray-600 bg-gray-900 px-2 py-1 text-gray-100"
                  >
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                  </select>
                  {user.roleManagedByEnv ? (
                    <span className="ml-2 text-xs text-teal-300">{t("admin.managedByEnv")}</span>
                  ) : null}
                  {rowError[user.userId] ? (
                    <p role="alert" className="mt-1 text-xs text-red-300">{rowError[user.userId]}</p>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-gray-400">{user.createdAt || "—"}</td>
                <td className="px-4 py-3">
                  <button
                    ref={(node) => {
                      editButtons.current[user.userId] = node;
                    }}
                    type="button"
                    aria-expanded={editing === user.userId}
                    aria-controls={`admin-editor-${user.userId}`}
                    onClick={() => setEditing((current) => (current === user.userId ? null : user.userId))}
                    className="rounded border border-gray-600 px-3 py-1 text-sm text-gray-200"
                  >
                    {t("admin.edit")}
                  </button>
                  {editing === user.userId ? (
                    <div id={`admin-editor-${user.userId}`}>
                      <AdminUserEditor
                        auth={auth}
                        user={user}
                        onClose={() => {
                          setEditing(null);
                          requestAnimationFrame(() => editButtons.current[user.userId]?.focus());
                        }}
                        onSaved={(next) => {
                          setUsers((current) =>
                            current.map((item) => (item.userId === next.userId ? next : item)),
                          );
                          setEditing(null);
                          requestAnimationFrame(() => editButtons.current[user.userId]?.focus());
                          if (next.isCurrentUser) auth.replaceProfile(next);
                        }}
                      />
                    </div>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {cursor ? (
        <button
          type="button"
          disabled={loading}
          onClick={() => void load(cursor)}
          className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-200 disabled:opacity-50"
        >
          {loading ? t("admin.loading") : t("admin.loadMore")}
        </button>
      ) : null}
      <RssSourcesPanel token={accessToken} />
      <JobControlsPanel
        token={accessToken}
        onNewsFetched={() => setRunsRefreshKey((key) => key + 1)}
      />
      <JobRunsPanel token={accessToken} refreshKey={runsRefreshKey} />
    </section>
  );
}
