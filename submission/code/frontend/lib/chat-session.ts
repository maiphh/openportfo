"use client";

/** Bounded, browser-only chat history keyed by the authenticated profile. */

export const CHAT_SESSION_PREFIX = "openportfo.chat.v1";
export const CHAT_SESSION_MAX_MESSAGES = 50;
export const CHAT_SESSION_MAX_CONTENT_CHARS = 8_000;
export const CHAT_SESSION_MAX_BYTES = 240_000;

export type ChatSessionMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
};

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function defaultStorage(): StorageLike | null {
  if (typeof window === "undefined") return null;
  try {
    // Transcripts are private browser state; do not persist them across a
    // browser restart or expose one user's conversation to a later session.
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function chatSessionKey(userId: string): string {
  // Encoding prevents a profile identifier from changing the storage
  // namespace. The key is local-only and is never sent to the API.
  return `${CHAT_SESSION_PREFIX}:${encodeURIComponent(userId.trim())}`;
}

function cleanMessage(value: unknown, index: number): ChatSessionMessage | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<ChatSessionMessage>;
  if (candidate.role !== "user" && candidate.role !== "assistant") return null;
  if (typeof candidate.content !== "string" || !candidate.content.trim()) return null;
  const createdAt = typeof candidate.createdAt === "number" && Number.isFinite(candidate.createdAt)
    ? candidate.createdAt
    : Date.now();
  return {
    id: typeof candidate.id === "string" && candidate.id.trim() ? candidate.id : `restored-${index}`,
    role: candidate.role,
    content: candidate.content.slice(0, CHAT_SESSION_MAX_CONTENT_CHARS),
    createdAt,
  };
}

function boundedMessages(messages: readonly ChatSessionMessage[]): ChatSessionMessage[] {
  let result = messages
    .map((message, index) => cleanMessage(message, index))
    .filter((message): message is ChatSessionMessage => message !== null)
    .slice(-CHAT_SESSION_MAX_MESSAGES);

  // Bound serialized storage as well as item count. Remove the oldest turns
  // until a pathological pasted transcript fits the quota budget.
  while (result.length > 1 && JSON.stringify(result).length > CHAT_SESSION_MAX_BYTES) {
    result = result.slice(1);
  }
  return result;
}

export function loadChatSession(
  userId: string,
  storage: StorageLike | null | undefined = defaultStorage(),
): ChatSessionMessage[] {
  if (!userId.trim() || !storage) return [];
  try {
    const raw = storage.getItem(chatSessionKey(userId));
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return boundedMessages(parsed as ChatSessionMessage[]);
  } catch {
    return [];
  }
}

export function saveChatSession(
  userId: string,
  messages: readonly ChatSessionMessage[],
  storage: StorageLike | null | undefined = defaultStorage(),
): void {
  if (!userId.trim() || !storage) return;
  try {
    const bounded = boundedMessages(messages);
    if (!bounded.length) {
      storage.removeItem(chatSessionKey(userId));
      return;
    }
    storage.setItem(chatSessionKey(userId), JSON.stringify(bounded));
  } catch {
    // Private mode and quota errors must not prevent chat from working.
  }
}

export function clearChatSession(
  userId: string,
  storage: StorageLike | null | undefined = defaultStorage(),
): void {
  if (!userId.trim() || !storage) return;
  try {
    storage.removeItem(chatSessionKey(userId));
  } catch {
    // Ignore unavailable storage.
  }
}

export function isChatSessionMessage(value: unknown): value is ChatSessionMessage {
  return cleanMessage(value, 0) !== null;
}
