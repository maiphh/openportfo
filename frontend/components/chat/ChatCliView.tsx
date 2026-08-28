"use client";

import { FormEvent, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowDown } from "lucide-react";
import { CodexExec } from "@/components/brainless/codex/codex-exec";
import { CodexHeader } from "@/components/brainless/codex/codex-header";
import { CodexMessage } from "@/components/brainless/codex/codex-message";
import { CodexPrompt } from "@/components/brainless/codex/codex-prompt";
import { CodexWorking } from "@/components/brainless/codex/codex-working";
import ChatCommandMenu from "@/components/chat/ChatCommandMenu";
import SafeMarkdown from "@/components/chat/SafeMarkdown";
import { safeActivity, type ChatUiMessage } from "@/components/chat/ChatMessageRow";
import { isAtBottom } from "@/components/chat/ChatMessageList";
import type { ChatRendererComponentProps } from "@/components/chat/ChatRenderer";
import type { ChatToolActivity } from "@/lib/chat";

function execStatus(status: ChatToolActivity["status"]): "ok" | "error" | "run" {
  if (status === "started") return "run";
  if (status === "failed") return "error";
  return "ok";
}

function execResult(status: ChatToolActivity["status"]): string {
  if (status === "started") return "running";
  if (status === "failed") return "failed";
  return "done";
}

function activityDescription(status: ChatToolActivity["status"]): string {
  if (status === "started") return "in progress";
  if (status === "failed") return "failed";
  return "complete";
}

function CliActivities({ activities }: { activities?: ChatToolActivity[] }) {
  const visibleActivities = (activities || []).slice(0, 12).map(safeActivity);
  if (!visibleActivities.length) return null;
  return (
    <div className="mt-2 space-y-1 pl-[2ch]" aria-label="Assistant activity">
      {visibleActivities.map((activity, index) => (
        <div
          key={`${activity.name}-${index}`}
          aria-label={`${activity.label}: ${activityDescription(activity.status)}`}
          data-testid="cli-tool-activity"
        >
          <CodexExec
            command={activity.label}
            result={execResult(activity.status)}
            status={execStatus(activity.status)}
          />
        </div>
      ))}
    </div>
  );
}

function CliMessage({ message }: { message: ChatUiMessage }) {
  const isAssistant = message.role === "assistant";
  const content = isAssistant ? (
    message.content ? <SafeMarkdown content={message.content} /> : null
  ) : (
    <span className="whitespace-pre-wrap break-words">{message.content}</span>
  );

  return (
    <div
      className={`min-w-0 space-y-1 ${isAssistant ? "" : "rounded border border-[#5cc2e0]/35 bg-[#252525] px-3 py-2"}`}
      data-role={message.role}
      data-message-tone={isAssistant ? "assistant" : "user"}
      data-streaming={message.streaming ? "true" : "false"}
      data-restored={message.isNew ? "false" : "true"}
      data-testid="cli-message"
    >
      <CodexMessage role={isAssistant ? "assistant" : "user"}>
        {message.failure ? (
          <div role="alert" className={message.failure.ambiguous ? "chat-ambiguous-alert" : undefined}>
            {content || "Unable to complete the chat request."}
            {message.failure.ambiguous ? (
              <p className="mt-2 border-t border-amber-200/15 pt-2 text-xs leading-5 text-amber-100">
                Verify your holdings or watchlist before trying again. No automatic retry was made.
              </p>
            ) : null}
          </div>
        ) : (
          content
        )}
      </CodexMessage>
      {isAssistant ? <CliActivities activities={message.activities} /> : null}
    </div>
  );
}

function CliEmptyState({ onSuggestion }: { onSuggestion: (value: string) => void }) {
  return (
    <div className="space-y-3">
      <CodexMessage>Ready for a portfolio question.</CodexMessage>
      <p className="pl-[2ch] text-xs leading-5 text-[#7a7a7a]">
        Ask about your portfolio, a quote, holdings, watchlist, or recent market news.
      </p>
      <div className="flex flex-wrap gap-x-4 gap-y-1 pl-[2ch]" aria-label="Suggested prompts">
        {["Show my portfolio", "Check a quote", "Find market news"].map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onSuggestion(suggestion)}
            className="font-mono text-left text-xs text-[#5cc2e0] underline-offset-2 hover:underline focus:outline-none focus-visible:ring-1 focus-visible:ring-[#5cc2e0]/60"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatCliView({ messages, draft, statusText, error, sending, pending, pendingId, reducedMotion, fullscreen, signedIn, onDraftChange, onSubmit, onSuggestion, onMessageEntered, onComposerReady, commandMenu }: ChatRendererComponentProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const composingRef = useRef(false);
  const enteredMessageIds = useRef(new Set<string>());
  const pinnedRef = useRef(true);
  const [showJump, setShowJump] = useState(false);

  useLayoutEffect(() => {
    onComposerReady(() => inputRef.current?.focus());
  }, [onComposerReady]);

  useEffect(() => {
    const ids = messages
      .filter((message) => message.isNew && !enteredMessageIds.current.has(message.id))
      .map((message) => message.id);
    if (!ids.length) return;
    ids.forEach((id) => {
      enteredMessageIds.current.add(id);
      onMessageEntered(id);
    });
  }, [messages, onMessageEntered]);

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
    const frame = typeof window !== "undefined" && typeof window.requestAnimationFrame === "function"
      ? window.requestAnimationFrame(() => scrollToLatest("auto"))
      : window.setTimeout(() => scrollToLatest("auto"), 0);
    return () => {
      if (typeof frame !== "number" || typeof window === "undefined") return;
      if (typeof window.cancelAnimationFrame === "function") window.cancelAnimationFrame(frame);
      else window.clearTimeout(frame);
    };
  }, [messages, pending, scrollToLatest, statusText]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void onSubmit();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && (event.nativeEvent.isComposing || composingRef.current)) return;
    if (commandMenu.onKeyDown(event)) return;
    if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
    event.preventDefault();
    void onSubmit();
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-[#1a1a1a] text-[#ededed]" data-reduced-motion={reducedMotion ? "true" : "false"} data-fullscreen={fullscreen ? "true" : "false"} data-testid="chat-cli-view">
      <div className="relative min-h-0 flex-1">
        <div
          ref={scrollRef}
          onScroll={onScroll}
          role="log"
          aria-label="CLI chat messages"
          data-fullscreen={fullscreen ? "true" : "false"}
          aria-live="polite"
          aria-relevant="additions text"
          className="h-full min-w-0 overflow-y-auto overscroll-contain px-4 py-4"
        >
          <div className={`${fullscreen ? "" : "mx-auto "}flex w-full max-w-3xl flex-col gap-3 font-mono text-[13px] leading-[1.6]`}>
            <CodexHeader
              title="OpenPortfo Agent CLI"
              showVersion={false}
              model="OpenRouter-configurable agent"
              modelCommand=""
              directory="authenticated session"
              workspaceLabel="session"
            />
            {messages.length ? messages.map((message) => (
              <div key={message.id} data-pending={message.id === pendingId ? "true" : "false"}>
                <CliMessage message={message} />
              </div>
            )) : <CliEmptyState onSuggestion={onSuggestion} />}
            {pending ? <CodexWorking label={statusText || "Working"} /> : null}
          </div>
        </div>
        {showJump ? (
          <button
            type="button"
            onClick={() => scrollToLatest()}
            className="absolute bottom-4 left-1/2 inline-flex min-h-11 -translate-x-1/2 items-center gap-2 rounded-full border border-[#5cc2e0]/40 bg-[#252525] px-3.5 text-xs font-medium text-[#b7e9f5] shadow-lg shadow-black/20 focus:outline-none focus-visible:ring-1 focus-visible:ring-[#5cc2e0]"
            aria-label="Jump to latest"
          >
            <ArrowDown className="size-3.5" aria-hidden="true" />
            Jump to latest
          </button>
        ) : null}
      </div>

      {error ? <p className="mx-4 mb-2 rounded border border-red-400/30 bg-red-400/[0.06] px-3 py-2 text-xs leading-5 text-red-200" role="alert">{error}</p> : null}
      <form onSubmit={handleSubmit} aria-label="CLI message composer" data-fullscreen={fullscreen ? "true" : "false"} className="shrink-0 border-t border-[#3a3a3a] bg-[#1a1a1a] px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3">
        <ChatCommandMenu state={commandMenu} variant="cli" />
        <CodexPrompt
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          onCompositionStart={() => { composingRef.current = true; }}
          onCompositionEnd={() => { composingRef.current = false; }}
          onKeyDown={handleKeyDown}
          inputRef={inputRef}
          id="personal-chat-cli-input"
          ariaDescribedBy="personal-chat-cli-input-help personal-chat-cli-input-count"
          ariaControls={commandMenu.open ? "cli-chat-command-menu" : undefined}
          ariaExpanded={commandMenu.open}
          ariaActiveDescendant={commandMenu.open ? `chat-command-cli-${commandMenu.activeIndex}` : undefined}
          placeholder={signedIn ? "Ask about your portfolio…" : "Sign in to start chatting"}
          disabled={!signedIn}
          maxLength={8_000}
          model="OpenRouter-configurable agent"
          directory="authenticated session"
          inputClassName="text-sm"
        />
        <div className="mt-1 flex items-center justify-between gap-3 pl-[2ch] font-mono text-[10px] text-[#7a7a7a]">
          <p id="personal-chat-cli-input-help">Enter to send</p>
          <span id="personal-chat-cli-input-count" aria-live="polite" aria-label={`${draft.length.toLocaleString()} of 8,000 characters`} className={draft.length > 7_800 ? "text-[#e0af68]" : undefined}>{draft.length.toLocaleString()}/8,000</span>
        </div>
        <button type="submit" disabled={!draft.trim() || sending || !signedIn} className="sr-only">Send message</button>
      </form>
    </div>
  );
}

export { CliActivities, CliMessage, execResult, execStatus };
