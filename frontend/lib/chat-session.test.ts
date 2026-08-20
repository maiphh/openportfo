import { describe, expect, it } from "vitest";
import {
  CHAT_SESSION_MAX_MESSAGES,
  CHAT_SESSION_MAX_CONTENT_CHARS,
  chatSessionKey,
  clearChatSession,
  loadChatSession,
  saveChatSession,
} from "@/lib/chat-session";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  };
}

describe("bounded chat sessions", () => {
  it("keeps sessions isolated by user and clips old/oversized content", () => {
    const storage = memoryStorage();
    const messages = Array.from({ length: CHAT_SESSION_MAX_MESSAGES + 10 }, (_, index) => ({
      id: String(index),
      role: index % 2 ? "assistant" as const : "user" as const,
      content: "x".repeat(CHAT_SESSION_MAX_CONTENT_CHARS + 100),
      createdAt: index,
    }));

    saveChatSession("user/a", messages, storage);
    saveChatSession("user-b", [{ id: "b", role: "user", content: "private", createdAt: 1 }], storage);

    const first = loadChatSession("user/a", storage);
    expect(first.length).toBeLessThanOrEqual(CHAT_SESSION_MAX_MESSAGES);
    expect(first.every((item) => item.content.length <= CHAT_SESSION_MAX_CONTENT_CHARS)).toBe(true);
    expect(loadChatSession("user-b", storage)[0]?.content).toBe("private");
    expect(chatSessionKey("user/a")).not.toBe(chatSessionKey("user-b"));
    expect(JSON.stringify(first)).not.toContain("user-b");
  });

  it("ignores malformed persisted data", () => {
    const storage = memoryStorage();
    storage.setItem(chatSessionKey("alice"), JSON.stringify([{ role: "system", content: "secret" }, "bad"]));
    expect(loadChatSession("alice", storage)).toEqual([]);
  });

  it("fails closed when browser storage reads or writes throw", () => {
    const broken = {
      getItem: () => { throw new Error("blocked"); },
      setItem: () => { throw new Error("quota"); },
      removeItem: () => { throw new Error("blocked"); },
    };
    expect(loadChatSession("alice", broken)).toEqual([]);
    expect(() => saveChatSession("alice", [{ id: "1", role: "user", content: "hello", createdAt: 1 }], broken)).not.toThrow();
    expect(() => clearChatSession("alice", broken)).not.toThrow();
  });
});
