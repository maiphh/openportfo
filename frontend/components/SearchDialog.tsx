"use client";

import { useEffect, useState } from "react";
import AssetLink from "@/components/AssetLink";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { Button } from "@/components/ui/button";
import {
  ASSET_SEARCH_DEBOUNCE_MS,
  liveSearchQuery,
  optionalSearchQuote,
  searchLiveCatalog,
  searchResultKey,
  searchResultLinkId,
} from "@/lib/asset-search";
import { clearAuthToken, readAuthToken, writeAuthToken } from "@/lib/auth";
import type { AssetSearchHit } from "@/lib/portfolio";
import { cn, formatPct, formatPrice } from "@/lib/utils";

function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  );
}

function typeLabel(assetType: AssetSearchHit["assetType"]): string {
  return assetType === "crypto" ? "Crypto" : "Stock";
}

export default function SearchDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [hits, setHits] = useState<AssetSearchHit[]>([]);
  const [failedTypes, setFailedTypes] = useState<string[]>([]);
  const [searching, setSearching] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setToken(readAuthToken());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    setToken(readAuthToken());
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setHits([]);
      setFailedTypes([]);
      setSearching(false);
      setError(null);
      setTokenInput("");
    }
  }, [open]);

  useEffect(() => {
    if (!open || !hydrated) return;

    const q = liveSearchQuery(query);
    if (!q) {
      setHits([]);
      setFailedTypes([]);
      setSearching(false);
      setError(null);
      return;
    }

    const t = token ?? readAuthToken();
    if (!t) {
      setAuthRequired(true);
      setHits([]);
      setFailedTypes([]);
      setSearching(false);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setSearching(true);
      setError(null);
      try {
        const result = await searchLiveCatalog({
          q,
          token: t,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (result.authRequired) {
          clearAuthToken();
          setToken(null);
          setAuthRequired(true);
          setHits([]);
          setFailedTypes([]);
          return;
        }
        setAuthRequired(false);
        setHits(result.hits);
        setFailedTypes(result.failedTypes);
        if (result.failedTypes.length === 2) {
          setError("Search failed. Try again.");
        }
      } catch (err) {
        if (controller.signal.aborted || isAbortError(err)) return;
        setHits([]);
        setFailedTypes([]);
        setError(err instanceof Error ? err.message : "Search failed");
      } finally {
        if (!controller.signal.aborted) setSearching(false);
      }
    }, ASSET_SEARCH_DEBOUNCE_MS);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, open, hydrated, token]);

  if (!open) return null;

  const q = liveSearchQuery(query);
  const showSignIn = hydrated && (authRequired || !token);
  const signedIn = hydrated && !showSignIn;
  const showHelper = signedIn && !q && !searching;
  const showNoMatches = signedIn && Boolean(q) && !searching && hits.length === 0 && !error;
  const softError =
    signedIn && failedTypes.length === 1
      ? `${failedTypes[0] === "stock" ? "Stock" : "Crypto"} search failed. Showing other results.`
      : null;

  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center bg-black/60 px-4 pt-24" onClick={onClose}>
      <div
        className="w-full max-w-2xl overflow-hidden rounded-xl border border-gray-600 bg-gray-800 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          autoFocus
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search symbols or companies"
          className="h-14 w-full border-b border-gray-600 bg-transparent px-5 text-base text-gray-200 outline-none placeholder:text-gray-500"
        />
        <ul className="max-h-[420px] overflow-y-auto py-2">
          {showSignIn ? (
            <li className="px-5 py-6">
              <p className="text-sm font-medium text-gray-200">Sign in to search</p>
              <p className="mt-1 text-xs text-gray-500">
                Asset search requires a Bearer token. Paste it to continue (saved as{" "}
                <code className="text-teal-400">artryx.accessToken</code>).
              </p>
              <input
                value={tokenInput}
                onChange={(event) => setTokenInput(event.target.value)}
                placeholder="Bearer token or fake:userId"
                className="mt-3 h-9 w-full rounded-md border border-gray-600 bg-gray-900 px-3 text-sm text-gray-200 outline-none focus:border-teal-500"
              />
              <div className="mt-3 flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  disabled={!tokenInput.trim()}
                  onClick={() => {
                    writeAuthToken(tokenInput);
                    setToken(readAuthToken());
                    setTokenInput("");
                    setAuthRequired(false);
                    setError(null);
                  }}
                >
                  Sign in
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    clearAuthToken();
                    setToken(null);
                    setHits([]);
                  }}
                >
                  Clear token
                </Button>
              </div>
            </li>
          ) : null}

          {showHelper ? (
            <li className="px-5 py-8 text-center text-sm text-gray-500">Type to search</li>
          ) : null}

          {searching ? <li className="px-5 py-3 text-sm text-gray-500">Searching…</li> : null}

          {softError ? <li className="px-5 py-2 text-xs text-amber-400">{softError}</li> : null}

          {error ? <li className="px-5 py-3 text-sm text-red-400">{error}</li> : null}

          {showNoMatches ? (
            <li className="px-5 py-8 text-center text-sm text-gray-500">No matches</li>
          ) : null}

          {signedIn
            ? hits.map((hit) => {
                const quote = optionalSearchQuote(hit);
                return (
                  <li key={searchResultKey(hit)}>
                    <AssetLink
                      assetType={hit.assetType}
                      id={searchResultLinkId(hit)}
                      onClick={onClose}
                      className="flex w-full items-center gap-3 px-5 py-2.5 text-left hover:bg-gray-700/60 hover:text-inherit"
                    >
                      <CompanyLogo symbol={hit.symbol} size={24} />
                      <span className="w-16 font-semibold text-gray-200">{hit.symbol}</span>
                      <span className="min-w-0 flex-1 truncate text-sm text-gray-500">{hit.name}</span>
                      <span className="rounded bg-gray-700 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                        {typeLabel(hit.assetType)}
                      </span>
                      {quote.price != null ? (
                        <span className="tabular-nums text-sm text-gray-200">{formatPrice(quote.price)}</span>
                      ) : null}
                      {quote.changePct != null ? (
                        <span
                          className={cn(
                            "w-16 text-right text-sm tabular-nums",
                            quote.changePct >= 0 ? "text-teal-400" : "text-red-500",
                          )}
                        >
                          {formatPct(quote.changePct)}
                        </span>
                      ) : null}
                    </AssetLink>
                  </li>
                );
              })
            : null}
        </ul>
      </div>
    </div>
  );
}
