"use client";

import { useEffect, useMemo, useState } from "react";
import AssetLink from "@/components/AssetLink";
import CompanyLogo from "@/components/dashboard/CompanyLogo";
import { SEARCH_UNIVERSE } from "@/lib/mock-data";
import { cn, formatPct, formatPrice } from "@/lib/utils";

export default function SearchDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return SEARCH_UNIVERSE;
    return SEARCH_UNIVERSE.filter(
      (row) => row.symbol.toLowerCase().includes(q) || row.name.toLowerCase().includes(q),
    );
  }, [query]);

  if (!open) return null;

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
          {results.length === 0 ? (
            <li className="px-5 py-8 text-center text-sm text-gray-500">No mock matches</li>
          ) : (
            results.map((row) => (
              <li key={row.symbol}>
                <AssetLink
                  assetType="stock"
                  id={row.symbol}
                  onClick={onClose}
                  className="flex w-full items-center gap-3 px-5 py-2.5 text-left hover:bg-gray-700/60 hover:text-inherit"
                >
                  <CompanyLogo symbol={row.symbol} size={24} />
                  <span className="w-16 font-semibold text-gray-200">{row.symbol}</span>
                  <span className="min-w-0 flex-1 truncate text-sm text-gray-500">{row.name}</span>
                  <span className="tabular-nums text-sm text-gray-200">{formatPrice(row.value)}</span>
                  <span
                    className={cn(
                      "w-16 text-right text-sm tabular-nums",
                      row.changePct >= 0 ? "text-teal-400" : "text-red-500",
                    )}
                  >
                    {formatPct(row.changePct)}
                  </span>
                </AssetLink>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
