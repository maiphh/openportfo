"use client";

import { FormEvent, useLayoutEffect, useRef } from "react";
import { LoaderCircle, Send } from "lucide-react";

type ChatComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (event?: FormEvent) => void | Promise<void>;
  disabled?: boolean;
  signedIn?: boolean;
  sending?: boolean;
  onReady?: (focus: () => void) => void;
};

export default function ChatComposer({ value, onChange, onSubmit, disabled, signedIn, sending, onReady }: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const composingRef = useRef(false);

  const resize = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    const nextHeight = Math.min(Math.max(textarea.scrollHeight, 44), 132);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > 132 ? "auto" : "hidden";
  };

  useLayoutEffect(resize, [value]);

  useLayoutEffect(() => {
    onReady?.(() => textareaRef.current?.focus());
  }, [onReady]);

  return (
    <form onSubmit={(event) => { event.preventDefault(); void onSubmit(event); }} className="border-t border-gray-700/80 bg-gray-800/80 px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3">
      <label htmlFor="personal-chat-input" className="sr-only">Message the personal assistant</label>
      <div className="chat-composer flex items-end gap-2 rounded-2xl border border-gray-600 bg-gray-900/80 px-2.5 py-2 transition-colors focus-within:border-teal-400/70 focus-within:ring-1 focus-within:ring-teal-400/25">
        <textarea
          ref={textareaRef}
          id="personal-chat-input"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onCompositionStart={() => { composingRef.current = true; }}
          onCompositionEnd={() => { composingRef.current = false; }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && !composingRef.current) {
              event.preventDefault();
              void onSubmit();
            }
          }}
          rows={1}
          maxLength={8_000}
          disabled={disabled || !signedIn}
          placeholder={signedIn ? "Ask anything about your portfolio…" : "Sign in to start chatting"}
          aria-describedby="personal-chat-input-help personal-chat-input-count"
          className="min-h-11 max-h-[132px] flex-1 resize-none bg-transparent px-1.5 py-1 text-sm leading-6 text-gray-100 outline-none placeholder:text-gray-500 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={disabled || sending || !value.trim() || !signedIn}
          aria-label={sending ? "Sending message" : "Send message"}
          className="inline-flex size-11 shrink-0 items-center justify-center rounded-xl bg-teal-400 text-teal-950 transition hover:bg-teal-300 focus:outline-none focus:ring-2 focus:ring-teal-200/80 disabled:cursor-not-allowed disabled:opacity-35"
        >
          {sending ? <LoaderCircle className="size-4.5 animate-spin" aria-hidden="true" /> : <Send className="size-4.5" aria-hidden="true" />}
        </button>
      </div>
      <div className="mt-2 flex items-center justify-between gap-3 px-1 text-[10px] text-gray-500">
        <p id="personal-chat-input-help">Enter to send · Shift+Enter for a new line</p>
        <span id="personal-chat-input-count" aria-live="polite" aria-label={`${value.length.toLocaleString()} of 8,000 characters`} className={value.length > 7_800 ? "text-amber-300/80" : ""}>{value.length.toLocaleString()}/8,000</span>
      </div>
    </form>
  );
}
