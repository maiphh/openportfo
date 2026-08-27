"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AssetHistoryChart from "@/components/asset/AssetHistoryChart";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import HoldingFormModal from "@/components/portfolio/HoldingFormModal";
import { Button } from "@/components/ui/button";
import { useDisplayCurrency } from "@/components/currency/CurrencyProvider";
import {
  AssetApiError,
  buildAssetStats,
  buildExternalLinks,
  CHART_RANGES,
  DEFAULT_CHART_RANGE,
  fallbackDescription,
  fetchAssetDetail,
  fetchAssetHistory,
  historyChartPoints,
  parseChartRange,
  toPrefillHit,
  type AssetDetailDto,
  type AssetHistoryDto,
  type AssetKind,
  type ChartMode,
  type ChartRange,
} from "@/lib/asset";
import AuthGate from "@/components/auth/AuthGate";
import { clearAuthToken, readAuthToken } from "@/lib/auth";
import {
  createHolding,
  PortfolioApiError,
  type AssetSearchHit,
  type HoldingMutation,
} from "@/lib/portfolio";
import { cn, formatPct, formatPrice } from "@/lib/utils";

function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  );
}

function parseNum(value: string | number | null | undefined): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export default function AssetDetailView({
  assetType,
  id,
}: {
  assetType: AssetKind;
  id: string;
}) {
  const { currency } = useDisplayCurrency();
  // Query-route ids have already been decoded by URLSearchParams, while the
  // legacy dynamic routes may still pass an encoded segment. Never let a
  // malformed percent escape crash the detail page.
  const slug = (() => {
    try {
      return decodeURIComponent(id);
    } catch {
      return id;
    }
  })();
  const [token, setToken] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);
  const [detail, setDetail] = useState<AssetDetailDto | null>(null);
  const [history, setHistory] = useState<AssetHistoryDto | null>(null);
  const [range, setRange] = useState<ChartRange>(DEFAULT_CHART_RANGE);
  const [chartMode, setChartMode] = useState<ChartMode>("line");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [prefill, setPrefill] = useState<AssetSearchHit | null>(null);
  const [mutateBusy, setMutateBusy] = useState(false);
  const [mutateError, setMutateError] = useState<string | null>(null);
  const [addedNote, setAddedNote] = useState<string | null>(null);
  const detailAbortRef = useRef<AbortController | null>(null);
  const historyAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setToken(readAuthToken());
    setHydrated(true);
  }, []);

  useEffect(() => {
    return () => {
      detailAbortRef.current?.abort();
      historyAbortRef.current?.abort();
    };
  }, []);

  const handleAuthFailure = useCallback((detailMsg?: string) => {
    clearAuthToken();
    setToken(null);
    setAuthRequired(true);
    setDetail(null);
    setHistory(null);
    setError(detailMsg?.trim() || "Sign in required to view asset detail.");
    setNotFound(false);
  }, []);

  const loadDetail = useCallback(async () => {
    const t = readAuthToken();
    setToken(t);
    if (!t) {
      setAuthRequired(true);
      setDetail(null);
      setHistory(null);
      setError(null);
      setNotFound(false);
      return;
    }

    detailAbortRef.current?.abort();
    const controller = new AbortController();
    detailAbortRef.current = controller;

    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const next = await fetchAssetDetail({
        assetType,
        slug,
        currency,
        range: null,
        token: t,
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setDetail(next);
      setAuthRequired(false);
    } catch (err) {
      if (controller.signal.aborted || isAbortError(err)) return;
      if (err instanceof AssetApiError && err.authRequired) {
        handleAuthFailure(err.detail);
      } else if (err instanceof AssetApiError && err.notFound) {
        setNotFound(true);
        setDetail(null);
        setError(err.detail || "Asset not found");
      } else {
        setError(err instanceof Error ? err.message : "Failed to load asset");
        setDetail(null);
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [assetType, currency, handleAuthFailure, slug]);

  const loadHistory = useCallback(
    async (nextRange: ChartRange) => {
      const t = readAuthToken();
      if (!t) return;

      historyAbortRef.current?.abort();
      const controller = new AbortController();
      historyAbortRef.current = controller;

      // Drop prior series so range tabs never paint mismatched labels vs points (AC6).
      setHistory(null);
      setHistoryLoading(true);
      try {
        const series = await fetchAssetHistory({
          assetType,
          slug,
          currency,
          range: nextRange,
          token: t,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setHistory(series);
      } catch (err) {
        if (controller.signal.aborted || isAbortError(err)) return;
        if (err instanceof AssetApiError && err.authRequired) {
          handleAuthFailure(err.detail);
          return;
        }
        // Keep page usable when history fails.
        setHistory({
          assetType,
          symbol: slug,
          assetId: slug,
          range: nextRange,
          nativeCurrency: assetType === "crypto" ? "USD" : "VND",
          displayCurrency: currency,
          points: [],
          fx: { status: "missing" },
        });
      } finally {
        if (!controller.signal.aborted) setHistoryLoading(false);
      }
    },
    [assetType, currency, handleAuthFailure, slug],
  );

  useEffect(() => {
    if (!hydrated) return;
    void loadDetail();
  }, [hydrated, loadDetail]);

  useEffect(() => {
    if (!hydrated || authRequired || !token || notFound) return;
    void loadHistory(range);
  }, [authRequired, hydrated, loadHistory, notFound, range, token]);

  const stats = useMemo(
    () => (detail ? buildAssetStats(detail.assetType, detail.profile, detail.quote) : []),
    [detail],
  );
  const links = useMemo(() => (detail ? buildExternalLinks(detail.profile) : []), [detail]);
  const historyReady =
    history != null && parseChartRange(String(history.range)) === range && !historyLoading;
  const preferDisplay = Boolean(history?.fx?.rate) || detail?.fx?.status !== "missing";
  const chartPoints = useMemo(
    () => (historyReady ? historyChartPoints(history, preferDisplay) : []),
    [history, historyReady, preferDisplay],
  );
  const chartRange = historyReady ? parseChartRange(String(history?.range)) : range;
  const chartCurrency =
    preferDisplay && history?.displayCurrency
      ? history.displayCurrency
      : history?.nativeCurrency || detail?.displayCurrency || currency;

  const price = detail?.quote
    ? parseNum(detail.quote.priceDisplay) ?? parseNum(detail.quote.price)
    : null;
  const priceCurrency =
    detail?.quote?.priceDisplay != null ? detail.displayCurrency : detail?.quote?.currency || detail?.nativeCurrency;
  const changePct = parseNum(detail?.quote?.changePercent24h);
  const priceRefreshing = loading && detail != null;

  const openAddHolding = () => {
    if (!detail) return;
    setPrefill(toPrefillHit(detail));
    setMutateError(null);
    setAddedNote(null);
    setModalOpen(true);
  };

  const handleSubmit = async (payload: HoldingMutation) => {
    setMutateBusy(true);
    setMutateError(null);
    try {
      await createHolding(payload, { token });
      setModalOpen(false);
      setAddedNote(`${payload.symbol} added to portfolio.`);
    } catch (err) {
      if (err instanceof PortfolioApiError) {
        if (err.authRequired) {
          setModalOpen(false);
          handleAuthFailure(err.detail);
        } else {
          setMutateError(err.detail);
        }
      } else {
        setMutateError(err instanceof Error ? err.message : "Save failed");
      }
    } finally {
      setMutateBusy(false);
    }
  };

  if (!hydrated) {
    return <div className="py-16 text-center text-sm text-gray-500">Loading asset…</div>;
  }

  if (authRequired || !token) {
    return (
      <AuthGate
        title="Asset detail"
        description={
          "Asset detail APIs require a Bearer access token. Paste a temporary token (saved as openportfo.accessToken). Cognito Hosted UI is not configured in this environment."
        }
        error={error}
        onTokenSaved={() => {
          setToken(readAuthToken());
          setAuthRequired(false);
          setError(null);
          void loadDetail();
        }}
      />
    );
  }

  if (loading && !detail) {
    return <div className="py-16 text-center text-sm text-gray-500">Loading {slug}…</div>;
  }

  if (notFound) {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-amber-500/30 bg-amber-500/5 px-6 py-10 text-center">
        <p className="text-sm uppercase tracking-wide text-amber-400">404</p>
        <h1 className="mt-2 text-xl font-semibold text-gray-100">Asset not found</h1>
        <p className="mt-2 text-sm text-gray-400">
          No {assetType} matched <span className="font-mono text-gray-200">{slug}</span>.
        </p>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
        {error || "Failed to load asset"}
      </div>
    );
  }

  const description = detail.profile?.description?.trim() || fallbackDescription(detail);
  const imageUrl = detail.profile?.imageUrl?.trim() || null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <CompanyLogo
            symbol={detail.symbol}
            size={56}
            src={imageUrl}
            assetType={detail.assetType}
          />
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-wide text-gray-500">
              {detail.assetType} · {detail.nativeCurrency}
              {detail.displayCurrency !== detail.nativeCurrency ? ` → ${detail.displayCurrency}` : ""}
            </p>
            <h1 className="truncate text-2xl font-semibold text-gray-100">
              {detail.name}{" "}
              <span className="font-medium text-gray-500">{detail.symbol}</span>
            </h1>
            <div className="mt-2 flex flex-wrap items-baseline gap-3">
              <span
                className={cn(
                  "text-3xl font-semibold tabular-nums text-gray-100",
                  priceRefreshing && "opacity-50",
                )}
              >
                {price == null ? "—" : `${formatPrice(price)} ${priceCurrency || ""}`.trim()}
              </span>
              {changePct != null && (
                <span
                  className={cn(
                    "text-sm tabular-nums",
                    changePct > 0 && "text-teal-400",
                    changePct < 0 && "text-red-500",
                    changePct === 0 && "text-gray-400",
                    priceRefreshing && "opacity-50",
                  )}
                >
                  {formatPct(changePct)} 24h
                </span>
              )}
              {priceRefreshing && (
                <span className="rounded bg-gray-700/80 px-2 py-0.5 text-[11px] uppercase tracking-wide text-gray-400">
                  Updating {currency}…
                </span>
              )}
            </div>
            {detail.fx?.status === "missing" && detail.displayCurrency !== detail.nativeCurrency && (
              <p className="mt-1 text-xs text-amber-400">FX unavailable — showing native price.</p>
            )}
          </div>
        </div>
        <Button type="button" onClick={openAddHolding}>
          Add to portfolio
        </Button>
      </div>

      {addedNote && (
        <div className="rounded-md border border-teal-500/30 bg-teal-500/10 px-3 py-2 text-sm text-teal-300">
          {addedNote}
        </div>
      )}
      {error && !notFound && (
        <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</div>
      )}

      <section className="rounded-xl border border-gray-600 bg-gray-800/40 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-gray-200">Price history</h2>
          <div className="flex flex-wrap gap-1">
            {CHART_RANGES.map((item) => (
              <Button
                key={item.value}
                type="button"
                size="sm"
                variant={range === item.value ? "default" : "outline"}
                disabled={historyLoading}
                onClick={() => setRange(parseChartRange(item.value))}
              >
                {item.label}
              </Button>
            ))}
          </div>
        </div>
        {!historyReady ? (
          <div className="py-16 text-center text-sm text-gray-500">Loading chart…</div>
        ) : (
          <AssetHistoryChart
            points={chartPoints}
            range={chartRange}
            currency={chartCurrency}
            mode={chartMode}
            onModeChange={setChartMode}
          />
        )}
      </section>

      <section className="rounded-xl border border-gray-600 bg-gray-800/40 p-4">
        <h2 className="mb-2 text-sm font-semibold text-gray-200">About</h2>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-300">{description}</p>
      </section>

      {stats.length > 0 && (
        <section className="rounded-xl border border-gray-600 bg-gray-800/40 p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-200">
            {detail.assetType === "crypto" ? "Crypto stats" : "Stock stats"}
          </h2>
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {stats.map((row) => (
              <div key={row.label} className="rounded-lg bg-gray-900/50 px-3 py-2">
                <dt className="text-[11px] uppercase tracking-wide text-gray-500">{row.label}</dt>
                <dd className="mt-1 text-sm tabular-nums text-gray-100">{row.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {links.length > 0 && (
        <section className="rounded-xl border border-gray-600 bg-gray-800/40 p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-200">Links</h2>
          <ul className="flex flex-wrap gap-2">
            {links.map((link) => (
              <li key={`${link.label}:${link.href}`}>
                <a
                  href={link.href}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex rounded-md border border-gray-600 px-3 py-1.5 text-sm text-teal-400 hover:border-teal-500/50 hover:bg-gray-700/40"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <HoldingFormModal
        open={modalOpen}
        mode="create"
        displayCurrency={currency}
        prefill={prefill}
        busy={mutateBusy}
        error={mutateError}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
