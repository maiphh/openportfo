export const CHAT_VIEW_MODE_KEY = "openportfo.chat-view-mode.v1";

export type ChatViewMode = "standard" | "cli";

export const DEFAULT_CHAT_VIEW_MODE: ChatViewMode = "standard";

type ReadStorage = Pick<Storage, "getItem">;
type WriteStorage = Pick<Storage, "setItem">;

function browserStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function isChatViewMode(value: unknown): value is ChatViewMode {
  return value === "standard" || value === "cli";
}

export function readChatViewMode(storage?: ReadStorage | null): ChatViewMode {
  const target = storage === undefined ? browserStorage() : storage;
  if (!target) return DEFAULT_CHAT_VIEW_MODE;
  try {
    const value = target.getItem(CHAT_VIEW_MODE_KEY);
    return isChatViewMode(value) ? value : DEFAULT_CHAT_VIEW_MODE;
  } catch {
    return DEFAULT_CHAT_VIEW_MODE;
  }
}

export function persistChatViewMode(mode: ChatViewMode, storage?: WriteStorage | null): void {
  if (!isChatViewMode(mode)) return;
  const target = storage === undefined ? browserStorage() : storage;
  if (!target) return;
  try {
    target.setItem(CHAT_VIEW_MODE_KEY, mode);
  } catch {
    // A blocked or full local store must not affect chatting.
  }
}

export const saveChatViewMode = persistChatViewMode;
