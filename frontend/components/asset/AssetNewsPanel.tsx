"use client";

import { useEffect, useState } from "react";
import {
  fetchNews,
  isAbortError,
  mapNewsItems,
  NewsApiError,
  type TopStory,
} from "@/lib/news";
import type { AssetKind } from "@/lib/asset";
import { Button } from "@/components/ui/button";

type Props = {
  assetType: AssetKind;
  symbol: string;
  name: string;
  assetId: string;
};

export default function AssetNewsPanel({ assetType, symbol, name, assetId }: Props) {
  const [stories, setStories] = useState<TopStory[]>([]);
  const [status, setStatus] = useState<"loading" | "live" | "empty" | "auth" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    setError(null);
    fetchNews({
      limit: 12,
      assetType,
      symbol,
      name,
      assetId,
      signal: controller.signal,
    })
      .then((items) => {
        if (controller.signal.aborted) return;
        const mapped = mapNewsItems(items);
        setStories(mapped);
        setStatus(mapped.length === 0 ? "empty" : "live");
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted || isAbortError(err)) return;
        setStories([]);
        if (err instanceof NewsApiError && err.authRequired) {
          setStatus("auth");
          return;
        }
        setStatus("error");
        setError(err instanceof Error ? err.message : "News unavailable");
      });
    return () => controller.abort();
  }, [assetId, assetType, name, reloadKey, symbol]);

  return (
    <section className="surface-card p-4" data-testid="asset-news">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-gray-200">Related news</h2>
          <p className="mt-0.5 text-xs text-gray-500">
            From stored headlines matching {symbol}
            {name ? ` / ${name}` : ""}
          </p>
        </div>
        {status === "error" ? (
          <Button type="button" size="sm" variant="outline" onClick={() => setReloadKey((k) => k + 1)}>
            Retry
          </Button>
        ) : null}
      </div>

      {status === "loading" ? (
        <p className="py-6 text-center text-sm text-gray-500">Loading news…</p>
      ) : null}
      {status === "auth" ? (
        <p className="py-6 text-center text-sm text-gray-500">Sign in to see news</p>
      ) : null}
      {status === "empty" ? (
        <p className="py-6 text-center text-sm text-gray-500">No matching stories yet</p>
      ) : null}
      {status === "error" ? (
        <p className="py-6 text-center text-sm text-gray-500">{error ?? "News unavailable"}</p>
      ) : null}
      {status === "live" ? (
        <ul className="space-y-4">
          {stories.map((story) => (
            <li key={story.id} className="border-b border-gray-700/80 pb-3 last:border-0 last:pb-0">
              {story.timeAgo ? <p className="mb-1 text-xs text-gray-500">{story.timeAgo}</p> : null}
              <p className="text-[11px] uppercase tracking-wide text-gray-500">{story.source}</p>
              {story.url ? (
                <a
                  href={story.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-0.5 block text-sm text-gray-100 transition-colors hover:text-teal-400"
                >
                  {story.title}
                </a>
              ) : (
                <p className="mt-0.5 text-sm text-gray-100">{story.title}</p>
              )}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
