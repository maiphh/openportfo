"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AllocationPie from "@/components/portfolio/AllocationPie";
import HoldingFormModal from "@/components/portfolio/HoldingFormModal";
import HoldingsTable from "@/components/portfolio/HoldingsTable";
import PortfolioSummaryCards from "@/components/portfolio/PortfolioSummaryCards";
import { Button } from "@/components/ui/button";
import { clearAuthToken, readAuthToken, writeAuthToken } from "@/lib/auth";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import {
  createHolding,
  deleteHolding,
  fetchPortfolio,
  parseMoney,
  PortfolioApiError,
  refreshPortfolio,
  updateHolding,
  type AssetTypeFilter,
  type HoldingMutation,
  type PortfolioLine,
  type PortfolioResponse,
} from "@/lib/portfolio";

export default function PortfolioDashboard() {
  const { currency, convertToDisplay } = useDisplayCurrency();
  const [token, setToken] = useState<string | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [filter, setFilter] = useState<AssetTypeFilter>("all");
  const [data, setData] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authRequired, setAuthRequired] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [editing, setEditing] = useState<PortfolioLine | null>(null);
  /** Currency of the cost field currently shown in the modal. */
  const [formCostCurrency, setFormCostCurrency] = useState(currency);
  const [mutateBusy, setMutateBusy] = useState(false);
  const [mutateError, setMutateError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  useEffect(() => {
    setToken(readAuthToken());
    setHydrated(true);
  }, []);

  const load = useCallback(
    async (opts?: { force?: boolean }) => {
      const t = readAuthToken();
      setToken(t);
      if (!t) {
        setAuthRequired(true);
        setData(null);
        setError(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const next = opts?.force
          ? await refreshPortfolio({ displayCurrency: currency, assetType: filter, token: t })
          : await fetchPortfolio({ displayCurrency: currency, assetType: filter, token: t });
        setData(next);
        setAuthRequired(false);
      } catch (err) {
        if (err instanceof PortfolioApiError && err.authRequired) {
          setAuthRequired(true);
          setData(null);
          setError("Sign in required to view portfolio.");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load portfolio");
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [currency, filter],
  );

  useEffect(() => {
    if (!hydrated) return;
    void load();
  }, [hydrated, load]);

  const lines = data?.lines ?? [];
  const isEmpty = hydrated && !authRequired && !loading && lines.length === 0 && filter === "all";

  const pieItems = useMemo(() => {
    return lines
      .map((line) => {
        const value =
          parseMoney(line.marketValueDisplay) ??
          (line.currency === currency ? parseMoney(line.marketValue) : null) ??
          0;
        return {
          key: `${line.assetType}:${line.symbol}`,
          label: line.symbol,
          value: value ?? 0,
        };
      })
      .filter((i) => i.value > 0);
  }, [lines, currency]);

  const openCreate = () => {
    setModalMode("create");
    setEditing(null);
    setFormCostCurrency(currency);
    setMutateError(null);
    setModalOpen(true);
  };

  const openEdit = (line: PortfolioLine) => {
    const native = parseMoney(line.avgCost);
    const inSession = native == null ? null : convertToDisplay(native, line.currency);
    setModalMode("edit");
    if (inSession != null) {
      setFormCostCurrency(currency);
      setEditing({ ...line, avgCost: String(inSession) });
    } else {
      // FX missing: keep native units so save does not mis-convert.
      setFormCostCurrency(line.currency as typeof currency);
      setEditing(line);
    }
    setMutateError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (payload: HoldingMutation) => {
    setMutateBusy(true);
    setMutateError(null);
    try {
      const costCurrency = modalMode === "edit" ? formCostCurrency : payload.currency;
      if (modalMode === "create") {
        await createHolding({ ...payload, currency: costCurrency }, { token });
      } else if (editing) {
        await updateHolding(
          editing.assetType,
          editing.symbol,
          {
            qty: payload.qty,
            avgCost: payload.avgCost,
            currency: costCurrency,
            note: payload.note,
          },
          { token },
        );
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      if (err instanceof PortfolioApiError) {
        setMutateError(err.detail);
        if (err.authRequired) setAuthRequired(true);
      } else {
        setMutateError(err instanceof Error ? err.message : "Save failed");
      }
    } finally {
      setMutateBusy(false);
    }
  };

  const handleDelete = async (line: PortfolioLine) => {
    const key = `${line.assetType}:${line.symbol}`;
    if (!window.confirm(`Delete ${line.symbol}?`)) return;
    setBusyKey(key);
    setError(null);
    try {
      await deleteHolding(line.assetType, line.symbol, { token });
      await load();
    } catch (err) {
      if (err instanceof PortfolioApiError) {
        setError(err.detail);
        if (err.authRequired) setAuthRequired(true);
      } else {
        setError(err instanceof Error ? err.message : "Delete failed");
      }
    } finally {
      setBusyKey(null);
    }
  };

  if (!hydrated) {
    return <div className="py-16 text-center text-sm text-gray-500">Loading portfolio…</div>;
  }

  if (authRequired || !token) {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-gray-600 bg-gray-800/60 p-6">
        <h1 className="text-xl font-semibold text-gray-100">Portfolio</h1>
        <p className="mt-2 text-sm text-gray-400">
          Cognito Bearer auth is required. Paste an access token (stored as{" "}
          <code className="text-teal-400">artryx.accessToken</code>) to continue. Full Cognito Hosted UI can replace
          this gate later.
        </p>
        <input
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
          placeholder="Bearer token or fake:userId"
          className="mt-4 h-10 w-full rounded-md border border-gray-600 bg-gray-900 px-3 text-sm text-gray-200 outline-none focus:border-teal-500"
        />
        <div className="mt-3 flex gap-2">
          <Button
            type="button"
            onClick={() => {
              writeAuthToken(tokenInput);
              setToken(readAuthToken());
              setTokenInput("");
              void load();
            }}
            disabled={!tokenInput.trim()}
          >
            Sign in
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              clearAuthToken();
              setToken(null);
              setData(null);
            }}
          >
            Clear token
          </Button>
        </div>
        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-100">Portfolio</h1>
          <p className="text-sm text-gray-500">
            One implicit portfolio · display currency {currency} (header switcher)
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={loading || refreshing}
            onClick={() => {
              setRefreshing(true);
              void load({ force: true });
            }}
          >
            {refreshing ? "Refreshing…" : "Refresh"}
          </Button>
          <Button type="button" onClick={openCreate}>
            Add holding
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["all", "crypto", "stock"] as const).map((f) => (
          <Button key={f} type="button" size="sm" variant={filter === f ? "default" : "outline"} onClick={() => setFilter(f)}>
            {f === "all" ? "All" : f === "crypto" ? "Crypto" : "Stock"}
          </Button>
        ))}
      </div>

      {error && (
        <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</div>
      )}

      {loading && !data ? (
        <div className="py-16 text-center text-sm text-gray-500">Loading holdings…</div>
      ) : isEmpty ? (
        <div className="rounded-xl border border-dashed border-gray-600 bg-gray-800/40 px-6 py-16 text-center">
          <p className="text-gray-300">No holdings yet.</p>
          <p className="mt-1 text-sm text-gray-500">Add your first VN stock or crypto position to open the portfolio.</p>
          <Button type="button" className="mt-4" onClick={openCreate}>
            Add holding
          </Button>
        </div>
      ) : data ? (
        <>
          <PortfolioSummaryCards data={data} fallbackCurrency={currency} />
          <AllocationPie items={pieItems} currency={currency} />
          <HoldingsTable
            lines={lines}
            displayCurrency={currency}
            onEdit={openEdit}
            onDelete={handleDelete}
            busyKey={busyKey}
          />
        </>
      ) : null}

      <HoldingFormModal
        open={modalOpen}
        mode={modalMode}
        displayCurrency={formCostCurrency}
        initial={editing}
        busy={mutateBusy}
        error={mutateError}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
