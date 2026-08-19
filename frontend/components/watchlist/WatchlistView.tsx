"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import AuthGate from "@/components/auth/AuthGate";
import { Button } from "@/components/ui/button";
import AddWatchlistModal from "@/components/watchlist/AddWatchlistModal";
import WatchlistTable from "@/components/watchlist/WatchlistTable";
import { clearAuthToken, readAuthToken } from "@/lib/auth";
import type { AssetSearchHit } from "@/lib/portfolio";
import {
  addWatchlist,
  fetchWatchlist,
  removeWatchlist,
  watchlistItemKey,
  WatchlistApiError,
  type WatchlistItem,
} from "@/lib/watchlist";

function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  );
}

function WatchlistSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-600" data-testid="watchlist-skeleton">
      <div className="space-y-3 px-3 py-4">
        {Array.from({ length: 6 }).map((_, row) => (
          <div key={row} className="flex items-center gap-4">
            <div className="h-3 w-28 animate-pulse rounded bg-gray-700/60" />
            <div className="ml-auto h-3 w-16 animate-pulse rounded bg-gray-700/60" />
            <div className="h-3 w-12 animate-pulse rounded bg-gray-700/60" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function WatchlistView() {
  const { currency, convertToDisplay } = useDisplayCurrency();
  const [token, setToken] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [items, setItems] = useState<WatchlistItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authRequired, setAuthRequired] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [mutateBusy, setMutateBusy] = useState(false);
  const [mutateError, setMutateError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const loadAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setToken(readAuthToken());
    setHydrated(true);
  }, []);

  useEffect(() => {
    return () => {
      loadAbortRef.current?.abort();
    };
  }, []);

  const handleAuthFailure = useCallback((detail?: string) => {
    clearAuthToken();
    setToken(null);
    setAuthRequired(true);
    setItems(null);
    setError(detail?.trim() || "Sign in required to view watchlist.");
    setMutateError(null);
  }, []);

  const load = useCallback(async () => {
    const t = readAuthToken();
    setToken(t);
    if (!t) {
      setAuthRequired(true);
      setItems(null);
      setError(null);
      return;
    }

    loadAbortRef.current?.abort();
    const controller = new AbortController();
    loadAbortRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const next = await fetchWatchlist({ token: t, signal: controller.signal });
      if (controller.signal.aborted) return;
      setItems(next);
      setAuthRequired(false);
    } catch (err) {
      if (controller.signal.aborted || isAbortError(err)) return;
      if (err instanceof WatchlistApiError && err.authRequired) {
        handleAuthFailure(err.detail);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load watchlist");
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, [handleAuthFailure]);

  useEffect(() => {
    if (!hydrated) return;
    void load();
  }, [hydrated, load]);

  const openAdd = () => {
    setMutateError(null);
    setModalOpen(true);
  };

  const handleAdd = async (hit: AssetSearchHit) => {
    setMutateBusy(true);
    setMutateError(null);
    const snapshot = items;
    try {
      await addWatchlist(
        {
          assetType: hit.assetType,
          symbol: hit.symbol,
          assetId: hit.assetId,
        },
        { token },
      );
      setModalOpen(false);
      await load();
    } catch (err) {
      if (err instanceof WatchlistApiError) {
        if (err.authRequired) {
          setModalOpen(false);
          handleAuthFailure(err.detail);
        } else if (err.conflict) {
          setItems(snapshot);
          setMutateError(err.detail || "Already on your watchlist.");
        } else {
          setMutateError(err.detail);
        }
      } else {
        setMutateError(err instanceof Error ? err.message : "Add failed");
      }
    } finally {
      setMutateBusy(false);
    }
  };

  const handleRemove = async (item: WatchlistItem) => {
    const key = watchlistItemKey(item);
    setBusyKey(key);
    setError(null);
    try {
      await removeWatchlist(item.assetType, item.symbol, { token });
      setItems((prev) => (prev ? prev.filter((row) => watchlistItemKey(row) !== key) : prev));
    } catch (err) {
      if (err instanceof WatchlistApiError) {
        if (err.authRequired) {
          handleAuthFailure(err.detail);
        } else {
          setError(err.detail);
        }
      } else {
        setError(err instanceof Error ? err.message : "Remove failed");
      }
    } finally {
      setBusyKey(null);
    }
  };

  if (!hydrated) {
    return <div className="py-16 text-center text-sm text-gray-500">Loading watchlist…</div>;
  }

  if (authRequired || !token) {
    return (
      <AuthGate
        title="Watchlist"
        description="Watchlist APIs require a Bearer access token. Paste a temporary token (saved as artryx.accessToken). Cognito Hosted UI is not configured in this environment."
        error={error}
        nextPath="/watchlist/"
        onTokenSaved={() => {
          setToken(readAuthToken());
          setAuthRequired(false);
          setError(null);
          void load();
        }}
      />
    );
  }

  const rows = items ?? [];
  const isEmpty = !loading && rows.length === 0 && !error;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-100">Watchlist</h1>
          <p className="text-sm text-gray-500">
            Names you track without a holding · display currency {currency} (header switcher)
          </p>
        </div>
        <Button type="button" onClick={openAdd}>
          Add to watchlist
        </Button>
      </div>

      {error && (
        <div
          className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400"
          data-testid="watchlist-error"
        >
          <p>{error}</p>
          <Button type="button" variant="outline" size="sm" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      )}

      {loading && !items ? (
        <WatchlistSkeleton />
      ) : isEmpty ? (
        <div className="rounded-xl border border-dashed border-gray-600 bg-gray-800/40 px-6 py-16 text-center">
          <p className="text-gray-300">No names on your watchlist yet.</p>
          <p className="mt-1 text-sm text-gray-500">Search a VN stock or crypto to glance at quotes without adding a holding.</p>
          <Button type="button" className="mt-4" onClick={openAdd}>
            Add to watchlist
          </Button>
        </div>
      ) : items ? (
        <WatchlistTable
          items={rows}
          displayCurrency={currency}
          convertToDisplay={convertToDisplay}
          onRemove={handleRemove}
          busyKey={busyKey}
        />
      ) : null}

      <AddWatchlistModal
        open={modalOpen}
        busy={mutateBusy}
        error={mutateError}
        onClose={() => setModalOpen(false)}
        onSubmit={handleAdd}
      />
    </div>
  );
}
