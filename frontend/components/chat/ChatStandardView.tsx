"use client";

import ChatComposer from "@/components/chat/ChatComposer";
import ChatMessageList from "@/components/chat/ChatMessageList";
import type { ChatRendererComponentProps } from "@/components/chat/ChatRenderer";

export default function ChatStandardView({
  messages,
  draft,
  statusText,
  error,
  sending,
  pending,
  pendingId,
  reducedMotion,
  fullscreen,
  signedIn,
  onDraftChange,
  onSubmit,
  onSuggestion,
  onMessageEntered,
  onComposerReady,
  commandMenu,
}: ChatRendererComponentProps) {
  return (
    <>
      <ChatMessageList
        messages={messages}
        statusText={statusText}
        pending={pending}
        pendingId={pendingId}
        reducedMotion={reducedMotion}
        fullscreen={fullscreen}
        empty={messages.length === 0}
        onSuggestion={onSuggestion}
        onMessageEntered={onMessageEntered}
      />
      {error ? <p className="mx-4 mb-2 rounded-xl border border-red-400/20 bg-red-400/[0.06] px-3 py-2.5 text-xs leading-5 text-red-400 dark:text-red-200" role="alert">{error}</p> : null}
      <ChatComposer
        value={draft}
        onChange={onDraftChange}
        onSubmit={onSubmit}
        signedIn={signedIn}
        sending={sending}
        fullscreen={fullscreen}
        onReady={onComposerReady}
        commandMenu={commandMenu}
      />
    </>
  );
}
