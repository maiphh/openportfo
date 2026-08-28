"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ComponentType, type KeyboardEvent } from "react";
import ChatCliView from "@/components/chat/ChatCliView";
import type { ChatCommandMenuState } from "@/components/chat/ChatCommandMenu";
import type { ChatUiMessage } from "@/components/chat/ChatMessageRow";
import ChatStandardView from "@/components/chat/ChatStandardView";
import {
  completeChatCommand,
  matchChatCommands,
  type ChatCommandOption,
} from "@/lib/chat-commands";
import type { ChatViewMode } from "@/lib/chat-view";

export type ChatRendererProps = {
  messages: ChatUiMessage[];
  draft: string;
  statusText: string | null;
  error: string | null;
  sending: boolean;
  pending: boolean;
  pendingId: string | null;
  reducedMotion: boolean;
  fullscreen: boolean;
  signedIn: boolean;
  onDraftChange: (value: string) => void;
  onSubmit: () => void | Promise<void>;
  onSuggestion: (value: string) => void;
  onMessageEntered: (id: string) => void;
  onComposerReady: (focus: () => void) => void;
};

export type ChatRendererComponentProps = ChatRendererProps & {
  commandMenu: ChatCommandMenuState;
};

export const CHAT_RENDERERS: Readonly<Record<ChatViewMode, ComponentType<ChatRendererComponentProps>>> = {
  standard: ChatStandardView,
  cli: ChatCliView,
};

function useCommandMenu(value: string, onChange: (value: string) => void): ChatCommandMenuState {
  const match = useMemo(() => matchChatCommands(value), [value]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [dismissedValue, setDismissedValue] = useState<string | null>(null);
  const options = match?.options || [];
  const open = Boolean(match && options.length && dismissedValue !== value);
  const clampedIndex = options.length ? Math.min(activeIndex, options.length - 1) : 0;

  useEffect(() => {
    setActiveIndex(0);
    if (dismissedValue !== null && dismissedValue !== value) setDismissedValue(null);
  }, [dismissedValue, value]);

  const select = (option: ChatCommandOption) => {
    const leadingWhitespace = value.match(/^\s*/)?.[0] || "";
    onChange(`${leadingWhitespace}${completeChatCommand(option)}`);
    setDismissedValue(null);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>): boolean => {
    if (!open || !options.length) return false;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % options.length);
      return true;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + options.length) % options.length);
      return true;
    }
    // Để composer xử lý Enter khi đang gõ IME hoặc Shift+Enter trong Standard.
    // Chỉ hoàn tất chỉ thị dở dang bằng Enter không có phím bổ trợ hoặc Tab.
    if (event.nativeEvent.isComposing && (event.key === "Enter" || event.key === "Tab")) return false;
    if ((event.key === "Enter" && !event.shiftKey) || event.key === "Tab") {
      event.preventDefault();
      select(options[clampedIndex]);
      return true;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      setDismissedValue(value);
      return true;
    }
    return false;
  };

  return {
    open,
    options,
    activeIndex: clampedIndex,
    setActiveIndex,
    select,
    onKeyDown,
  };
}

export default function ChatRenderer({ mode, ...props }: ChatRendererProps & { mode: ChatViewMode }) {
  const commandMenu = useCommandMenu(props.draft, props.onDraftChange);
  const previousMode = useRef(mode);
  useLayoutEffect(() => {
    if (previousMode.current !== mode) {
      const inputId = mode === "cli" ? "personal-chat-cli-input" : "personal-chat-input";
      document.getElementById(inputId)?.focus();
    }
    previousMode.current = mode;
  }, [mode]);
  const Renderer = CHAT_RENDERERS[mode];
  return <Renderer {...props} commandMenu={commandMenu} />;
}
