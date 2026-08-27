"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { CompanyTimelineEvent } from "@/lib/asset";
import { cn } from "@/lib/utils";

const COLLAPSED_COUNT = 4;

export default function CompanyTimeline({
  events,
  className,
}: {
  events: CompanyTimelineEvent[];
  className?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const years = events.map((event) => event.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const span = Math.max(maxYear - minYear, 1);
  const canToggle = events.length > COLLAPSED_COUNT;
  const visible = expanded || !canToggle ? events : events.slice(0, COLLAPSED_COUNT);
  const hiddenCount = Math.max(events.length - COLLAPSED_COUNT, 0);

  return (
    <div className={cn("space-y-4", className)}>
      <div className="rounded-lg border border-gray-700/80 bg-gray-900/40 px-3 py-3">
        <div className="mb-2 flex items-center justify-between text-[11px] tabular-nums text-gray-500">
          <span>{minYear}</span>
          <span>
            {events.length} milestones · {span + 1} years
          </span>
          <span>{maxYear}</span>
        </div>
        <div className="relative h-2 rounded-full bg-gray-700/80">
          <div className="absolute inset-y-0 left-0 rounded-full bg-teal-400/70" style={{ width: "100%" }} />
          {events.map((event, index) => {
            const left = ((event.year - minYear) / span) * 100;
            return (
              <span
                key={`${event.year}-${index}-dot`}
                title={`${event.when}: ${event.text}`}
                className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-gray-900 bg-teal-400 shadow-[0_0_0_2px_rgb(20_20_20/0.9)]"
                style={{ left: `${left}%` }}
              />
            );
          })}
        </div>
      </div>

      <ol className="relative ml-2 space-y-0 border-l border-gray-600/80 pl-5">
        {visible.map((event, index) => (
          <li key={`${event.year}-${index}`} className="relative pb-5 last:pb-0">
            <span className="absolute -left-[1.45rem] top-1.5 size-2.5 rounded-full bg-teal-400 ring-4 ring-gray-800" />
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <time className="text-xs font-semibold tabular-nums text-teal-300">{event.when}</time>
              <span className="text-[11px] text-gray-500">{event.year}</span>
            </div>
            <p className="mt-1 text-sm leading-relaxed text-gray-300">{event.text}</p>
          </li>
        ))}
      </ol>

      {canToggle ? (
        <button
          type="button"
          aria-expanded={expanded}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-gray-400 transition-colors hover:bg-gray-700/50 hover:text-gray-100"
          onClick={() => setExpanded((value) => !value)}
        >
          <ChevronDown
            className={cn("size-4 transition-transform duration-200", expanded && "rotate-180")}
            aria-hidden="true"
          />
          {expanded ? "Show less" : `Show ${hiddenCount} more`}
        </button>
      ) : null}
    </div>
  );
}
