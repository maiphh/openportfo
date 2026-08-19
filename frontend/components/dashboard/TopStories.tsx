"use client";

import { useEffect, useState } from "react";
import AssetLink from "@/components/AssetLink";
import { Button } from "@/components/ui/button";
import {
  fetchNews,
  isAbortError,
  mapNewsItems,
  NEWS_DEFAULT_LIMIT,
  NewsApiError,
  type TopStory,
} from "@/lib/news";

function StoriesSkeleton() {
  return (
    <ul className="space-y-5" data-testid="top-stories-skeleton">
      {Array.from({ length: 6 }).map((_, index) => (
        <li key={index} className="flex gap-3">
          <span className="mt-0.5 h-6 w-6 shrink-0 animate-pulse rounded-full bg-gray-700/60" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="h-3 w-16 animate-pulse rounded bg-gray-700/60" />
            <div className="h-4 w-full animate-pulse rounded bg-gray-700/60" />
            <div className="h-4 w-3/4 animate-pulse rounded bg-gray-700/60" />
          </div>
        </li>
      ))}
    </ul>
  );
}

function StoryHeadline({ story }: { story: TopStory }) {
  const className = "text-[15px] leading-snug text-gray-200";
  if (story.url) {
    return (
      <a
        href={story.url}
        target="_blank"
        rel="noopener noreferrer"
        className={`${className} transition-colors hover:text-teal-400`}
      >
        {story.title}
      </a>
    );
  }
  return <p className={className}>{story.title}</p>;
}

export default function TopStories() {
  const [stories, setStories] = useState<TopStory[]>([]);
  const [status, setStatus] = useState<"loading" | "live" | "empty" | "auth" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStories([]);
    setStatus("loading");
    setError(null);
    fetchNews({ limit: NEWS_DEFAULT_LIMIT, signal: controller.signal })
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
          setError(null);
          return;
        }
        setStatus("error");
        setError(err instanceof Error ? err.message : "News unavailable");
      });
    return () => controller.abort();
  }, [reloadKey]);

  return (
    <div className="w-full">
      <h3 className="mb-5 text-2xl font-semibold text-gray-100">Top Stories</h3>
      <div className="min-h-[480px] overflow-y-auto rounded-lg border border-gray-600 bg-gray-800 p-4 xl:h-[560px]">
        {status === "loading" ? <StoriesSkeleton /> : null}

        {status === "auth" ? (
          <div
            className="flex h-full min-h-[400px] flex-col items-center justify-center gap-2 px-4 text-center"
            data-testid="top-stories-auth"
          >
            <p className="text-sm text-gray-400">Sign in to see news</p>
          </div>
        ) : null}

        {status === "empty" ? (
          <div
            className="flex h-full min-h-[400px] flex-col items-center justify-center px-4 text-center"
            data-testid="top-stories-empty"
          >
            <p className="text-sm text-gray-400">No stories yet</p>
          </div>
        ) : null}

        {status === "error" ? (
          <div
            className="flex h-full min-h-[400px] flex-col items-center justify-center gap-3 px-4 text-center"
            data-testid="top-stories-error"
          >
            <p className="text-sm text-gray-400">{error ?? "News unavailable"}</p>
            <Button type="button" variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          </div>
        ) : null}

        {status === "live" ? (
          <ul className="space-y-5" data-testid="top-stories-list">
            {stories.map((story) => (
              <li key={story.id} className="flex gap-3">
                <span
                  className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white"
                  style={{ background: story.sourceColor }}
                >
                  {story.sourceInitial}
                </span>
                <div className="min-w-0">
                  {story.timeAgo ? <p className="mb-1 text-xs text-gray-500">{story.timeAgo}</p> : null}
                  {story.symbols.length > 0 ? (
                    <p className="mb-1 flex flex-wrap gap-x-2 gap-y-1 text-[13px]">
                      {story.symbols.map((tag) => (
                        <AssetLink
                          key={`${story.id}-${tag.id}`}
                          assetType={tag.assetType}
                          id={tag.id}
                          className="font-semibold text-teal-400"
                        >
                          {tag.symbol}
                        </AssetLink>
                      ))}
                    </p>
                  ) : null}
                  <StoryHeadline story={story} />
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
