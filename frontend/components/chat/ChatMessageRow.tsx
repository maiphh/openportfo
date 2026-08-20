"use client";

import { memo, useState } from "react";
import { Check, CircleAlert, LoaderCircle, Sparkles } from "lucide-react";
import type { ChatToolActivity } from "@/lib/chat";
import type { ChatSessionMessage } from "@/lib/chat-session";
import SafeMarkdown from "@/components/chat/SafeMarkdown";

export type ChatUiMessage = ChatSessionMessage & {
  activities?: ChatToolActivity[];
  streaming?: boolean;
  isNew?: boolean;
  failure?: { ambiguous?: boolean };
};

// Keep the UI boundary closed even when a test or an older deployment feeds
// an untrusted activity object directly into the component.
const PUBLIC_CHAT_TOOL_LABELS: Readonly<Record<string, string>> = {
  search_assets: "Searching assets",
  add_holding: "Updating holdings",
  remove_holding: "Updating holdings",
  list_holdings: "Reading holdings",
  get_portfolio: "Reading portfolio",
  get_quote: "Checking a quote",
  analyze_asset: "Analyzing an asset",
  analyze_portfolio: "Analyzing portfolio",
  get_news: "Reading market news",
  add_watchlist: "Updating watchlist",
  remove_watchlist: "Updating watchlist",
};

function safeActivity(activity: ChatToolActivity): ChatToolActivity {
  const name = typeof activity?.name === "string" && PUBLIC_CHAT_TOOL_LABELS[activity.name]
    ? activity.name
    : "assistant_action";
  const status = activity?.status === "started" || activity?.status === "failed"
    ? activity.status
    : "completed";
  return {
    name,
    label: PUBLIC_CHAT_TOOL_LABELS[name] || "Assistant action",
    status,
  };
}

function activityLabel(status: ChatToolActivity["status"]): string {
  if (status === "started") return "in progress";
  if (status === "failed") return "could not complete";
  return "complete";
}

function ActivityTimeline({ activities }: { activities: ChatToolActivity[] }) {
  const visibleActivities = activities.slice(0, 12).map(safeActivity);
  if (!visibleActivities.length) return null;
  return (
    <div className="mt-3 border-t border-gray-700/70 pt-2.5" aria-label="Assistant activity">
      <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-[0.12em] text-gray-500">
        <Sparkles className="size-3 text-teal-400" aria-hidden="true" />
        Activity
      </div>
      <ul className="space-y-1" aria-label="Assistant tool activity">
        {visibleActivities.map((activity, index) => (
          <li
            key={`${activity.name}-${index}`}
            className="flex items-center gap-2 text-xs text-gray-400"
            aria-label={`${activity.label}: ${activityLabel(activity.status)}`}
          >
            <span className="flex size-4 shrink-0 items-center justify-center rounded-full bg-gray-800 text-gray-500" aria-hidden="true">
              {activity.status === "started" ? (
                <LoaderCircle className="size-3 animate-spin text-teal-400" />
              ) : activity.status === "failed" ? (
                <CircleAlert className="size-3 text-amber-300" />
              ) : (
                <Check className="size-3 text-emerald-400" />
              )}
            </span>
            <span>{activity.label}</span>
            <span className="sr-only">{activityLabel(activity.status)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ThinkingIndicator({ label }: { label?: string }) {
  return (
    <div className="chat-thinking flex items-center gap-2 text-sm text-gray-400" role="status" aria-label={label || "Thinking"}>
      <span className="chat-thinking__dots inline-flex items-center gap-1" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <span>{label || "Thinking about your request"}</span>
    </div>
  );
}

export const ChatMessageRow = memo(function ChatMessageRow({ message, statusText }: { message: ChatUiMessage; statusText?: string | null }) {
  // The parent marker is durable state used to coordinate persistence. Latch
  // its initial value for this mount so clearing that marker does not cancel
  // the entrance animation already in progress. A later reopen mounts a new
  // row with the cleared marker and therefore has no entrance class.
  const [animateEntrance] = useState(() => Boolean(message.isNew));
  const isAssistant = message.role === "assistant";
  const showThinking = isAssistant && message.streaming && !message.content;
  const showStatus = isAssistant && Boolean(statusText) && message.streaming;
  const content = isAssistant ? <SafeMarkdown content={message.content || "No response."} /> : <p className="whitespace-pre-wrap break-words leading-6">{message.content}</p>;
  return (
    <article
      className={`chat-message-row ${animateEntrance ? "chat-message-row--new" : ""} ${isAssistant ? "chat-message-row--assistant" : "chat-message-row--user"}`}
      data-role={message.role}
      data-streaming={message.streaming ? "true" : "false"}
      data-restored={animateEntrance ? "false" : "true"}
    >
      <div className="mb-1 flex items-center gap-2 px-1 text-[10px] font-medium uppercase tracking-[0.12em] text-gray-500">
        <span className={isAssistant ? "text-teal-400" : "text-gray-500"}>{isAssistant ? "Assistant" : "You"}</span>
        {message.streaming ? <span className="text-teal-400" aria-label="Streaming">Live</span> : null}
      </div>
      <div className={isAssistant ? `chat-message-bubble chat-message-bubble--assistant${message.failure?.ambiguous ? " chat-message-bubble--ambiguous" : ""}` : "chat-message-bubble chat-message-bubble--user"}>
        {showThinking ? <ThinkingIndicator label={statusText || undefined} /> : message.failure ? (
          <div role="alert" className={message.failure.ambiguous ? "chat-ambiguous-alert" : undefined}>
            {content}
            {message.failure.ambiguous ? (
              <p className="mt-2 border-t border-amber-200/15 pt-2 text-xs leading-5 text-amber-100">
                Verify your holdings or watchlist before trying again. No automatic retry was made.
              </p>
            ) : null}
          </div>
        ) : content}
        {showStatus && !showThinking ? <div className="mt-3 border-t border-gray-700/70 pt-2.5"><ThinkingIndicator label={statusText || undefined} /></div> : null}
        {isAssistant && message.activities?.length ? <ActivityTimeline activities={message.activities} /> : null}
      </div>
    </article>
  );
});

export { ActivityTimeline, ThinkingIndicator, safeActivity };
