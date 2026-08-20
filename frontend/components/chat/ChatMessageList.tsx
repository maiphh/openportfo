"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, MessageCircle } from "lucide-react";
import { ChatMessageRow, type ChatUiMessage } from "@/components/chat/ChatMessageRow";

const PIN_DISTANCE = 64;

type ChatMessageListProps = {
  messages: ChatUiMessage[];
  statusText: string | null;
  pending: boolean;
  pendingId?: string | null;
  reducedMotion?: boolean;
  empty?: boolean;
  onSuggestion?: (value: string) => void;
  onMessageEntered?: (id: string) => void;
};

const PUBLIC_STATUS_TEXTS = new Set([
  "Thinking about your request",
  "Writing a response",
  "Working on your request",
]);

function safeStatusText(value: string | null): string | null {
  if (!value) return null;
  return PUBLIC_STATUS_TEXTS.has(value) ? value : "Working on your request";
}

function isAtBottom(element: HTMLElement): boolean {
  return element.scrollHeight - element.scrollTop - element.clientHeight <= PIN_DISTANCE;
}

export default function ChatMessageList({ messages, statusText, pending, pendingId, reducedMotion = false, empty, onSuggestion, onMessageEntered }: ChatMessageListProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const enteredMessageIds = useRef(new Set<string>());
  const pinnedRef = useRef(true);
  const [showJump, setShowJump] = useState(false);

  const scrollToLatest = useCallback((behavior?: ScrollBehavior) => {
    const element = scrollRef.current;
    if (!element) return;
    pinnedRef.current = true;
    setShowJump(false);
    if (typeof element.scrollTo === "function") {
      element.scrollTo({ top: element.scrollHeight, behavior: reducedMotion ? "auto" : (behavior || "smooth") });
    } else {
      element.scrollTop = element.scrollHeight;
    }
  }, [reducedMotion]);

  const onScroll = useCallback(() => {
    const element = scrollRef.current;
    if (!element) return;
    const pinned = isAtBottom(element);
    pinnedRef.current = pinned;
    setShowJump(!pinned && messages.length > 0);
  }, [messages.length]);

  useEffect(() => {
    if (!pinnedRef.current) {
      setShowJump(messages.length > 0);
      return;
    }
    // Let the browser lay out the new row before measuring scrollHeight.
    const frame = typeof window !== "undefined" && typeof window.requestAnimationFrame === "function"
      ? window.requestAnimationFrame(() => scrollToLatest("auto"))
      : window.setTimeout(() => scrollToLatest("auto"), 0);
    return () => {
      if (typeof frame === "number" && typeof window !== "undefined" && typeof window.cancelAnimationFrame === "function") {
        window.cancelAnimationFrame(frame);
      } else if (typeof window !== "undefined") {
        window.clearTimeout(frame as number);
      }
    };
  }, [messages, pending, scrollToLatest]);

  useEffect(() => {
    if (!onMessageEntered) return;
    // Consume the entrance marker from the committed render. Keeping this
    // synchronous with the passive effect means a quick close/unmount cannot
    // cancel the handoff and replay the animation on the next open.
    const ids = messages
      .filter((message) => message.isNew && !enteredMessageIds.current.has(message.id))
      .map((message) => message.id);
    if (!ids.length) return;
    ids.forEach((id) => {
      enteredMessageIds.current.add(id);
      onMessageEntered(id);
    });
  }, [messages, onMessageEntered]);

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scrollRef}
        onScroll={onScroll}
        role="log"
        aria-label="Chat messages"
        aria-live="polite"
        aria-relevant="additions text"
        className="chat-message-log h-full min-w-0 overflow-y-auto overscroll-contain px-4 py-5"
      >
        {empty ? (
          <div className="flex min-h-full flex-col justify-center py-8">
            <div className="mx-auto w-full max-w-sm text-center">
              <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-2xl border border-teal-400/20 bg-teal-400/10 text-teal-400">
                <MessageCircle className="size-5" aria-hidden="true" />
              </div>
              <h3 className="text-base font-semibold text-gray-100">What can I help with?</h3>
              <p className="mt-2 text-sm leading-6 text-gray-500">Ask about your portfolio, a quote, holdings, watchlist, or recent market news.</p>
              <div className="mt-5 flex flex-wrap justify-center gap-2" aria-label="Suggested prompts">
                {["Show my portfolio", "Check a quote", "Find market news"].map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => onSuggestion?.(suggestion)}
                    className="min-h-11 rounded-full border border-gray-600 bg-gray-800/80 px-3 text-xs text-gray-300 transition-colors hover:border-teal-400/50 hover:bg-teal-400/10 hover:text-teal-200 focus:outline-none focus:ring-2 focus:ring-teal-400/60"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
            {messages.map((message) => {
              const activePendingId = pendingId || (pending ? messages.find((item) => item.streaming)?.id : null);
              return <ChatMessageRow key={message.id} message={message} statusText={message.id === activePendingId ? safeStatusText(statusText) : null} />;
            })}
          </div>
        )}
      </div>
      {showJump ? (
        <button
          type="button"
          onClick={() => scrollToLatest()}
          className="absolute bottom-4 left-1/2 inline-flex min-h-11 -translate-x-1/2 items-center gap-2 rounded-full border border-teal-400/30 bg-gray-800/95 px-3.5 text-xs font-medium text-teal-200 shadow-lg shadow-black/20 backdrop-blur transition hover:border-teal-300/60 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-teal-400/70"
          aria-label="Jump to latest"
        >
          <ArrowDown className="size-3.5" aria-hidden="true" />
          Jump to latest
        </button>
      ) : null}
    </div>
  );
}

export { PIN_DISTANCE, isAtBottom };
