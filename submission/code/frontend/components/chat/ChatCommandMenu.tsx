"use client";

import { useEffect, useRef, type KeyboardEvent } from "react";
import type { ChatCommandOption } from "@/lib/chat-commands";

export type ChatCommandMenuState = {
  open: boolean;
  options: ChatCommandOption[];
  activeIndex: number;
  setActiveIndex: (index: number) => void;
  select: (option: ChatCommandOption) => void;
  onKeyDown: (event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => boolean;
};

export default function ChatCommandMenu({
  state,
  variant,
}: {
  state: ChatCommandMenuState;
  variant: "standard" | "cli";
}) {
  const optionRefs = useRef<Array<HTMLLIElement | null>>([]);
  useEffect(() => {
    optionRefs.current.length = state.options.length;
    if (!state.open || !state.options.length) return;
    optionRefs.current[state.activeIndex]?.scrollIntoView?.({ block: "nearest" });
  }, [state.activeIndex, state.open, state.options, variant]);

  if (!state.open || !state.options.length) return null;
  const cli = variant === "cli";
  return (
    <ul
      id={`${variant}-chat-command-menu`}
      role="listbox"
      aria-label="Agent commands and tools"
      className={cli
        ? "mb-2 max-h-52 space-y-0.5 overflow-y-auto border-y border-[#3a3a3a] py-1 pl-[2ch] font-mono text-[12px]"
        : "mb-2 max-h-52 space-y-1 overflow-y-auto rounded-xl border border-gray-600 bg-gray-900/95 p-1.5 shadow-xl"}
    >
      {state.options.map((option, index) => {
        const active = index === state.activeIndex;
        return (
          <li
            key={option.token}
            id={`chat-command-${variant}-${index}`}
            role="option"
            aria-selected={active}
            tabIndex={-1}
            ref={(element) => { optionRefs.current[index] = element; }}
            onMouseEnter={() => state.setActiveIndex(index)}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => state.select(option)}
            className={cli
              ? `flex w-full min-w-0 cursor-pointer items-baseline gap-3 px-1 py-0.5 ${active ? "text-[#ededed]" : "text-[#7a7a7a]"}`
              : `flex w-full min-w-0 cursor-pointer items-start gap-3 rounded-lg px-2.5 py-2 ${active ? "bg-gray-700 text-gray-100" : "text-gray-400"}`}
          >
            <span className={`shrink-0 ${cli ? "w-[20ch] text-[#5cc2e0]" : "font-mono text-xs text-teal-400"}`}>
              {option.token}
            </span>
            <span className="min-w-0 truncate text-xs">{option.description}</span>
          </li>
        );
      })}
    </ul>
  );
}
