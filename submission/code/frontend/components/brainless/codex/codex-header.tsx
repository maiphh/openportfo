import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * CodexHeader — Codex CLI's launch card. Monochrome and terse, matching the
 * real `>_ OpenAI Codex` box with its model / directory rows.
 */
export function CodexHeader({
  version = "v0.132.0",
  showVersion = true,
  title = "OpenAI Codex",
  model = "gpt-5.6-sol low",
  modelCommand = "/model",
  directory = "~/dev/brainless",
  workspaceLabel = "directory",
  className,
}: {
  version?: string;
  showVersion?: boolean;
  title?: string;
  model?: string;
  modelCommand?: string;
  directory?: string;
  workspaceLabel?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "min-w-0 rounded-[6px] border border-[#3a3a3a] px-3 py-3 font-mono text-[13px] leading-[1.7] text-[#ededed] sm:px-4",
        className,
      )}
    >
      <div className="flex min-w-0 flex-wrap items-baseline gap-x-2">
        <span aria-hidden className="shrink-0 text-[#7a7a7a]">
          {">_"}
        </span>
        <span className="font-medium">{title}</span>
        {showVersion ? <span className="text-[#7a7a7a]">({version})</span> : null}
      </div>
      <div className="mt-2 grid min-w-0 grid-cols-[max-content_minmax(0,1fr)] gap-x-3">
        <span className="text-[#7a7a7a]">model:</span>
        <span className="min-w-0 break-words">
          {model}
          {modelCommand ? (
            <>
              <span className="ml-3 text-[#5cc2e0]">{modelCommand}</span>
              <span className="ml-1 text-[#7a7a7a]">to change</span>
            </>
          ) : null}
        </span>
        <span className="text-[#7a7a7a]">{workspaceLabel}:</span>
        <span className="truncate">{directory}</span>
      </div>
    </div>
  );
}
