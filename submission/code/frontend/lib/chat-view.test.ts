import { describe, expect, it } from "vitest";
import {
  CHAT_VIEW_MODE_KEY,
  DEFAULT_CHAT_VIEW_MODE,
  persistChatViewMode,
  readChatViewMode,
} from "@/lib/chat-view";

function storage(initial?: string): Storage {
  let value = initial ?? null;
  return {
    getItem: () => value,
    setItem: (_key: string, next: string) => { value = next; },
    removeItem: () => { value = null; },
    clear: () => { value = null; },
    key: () => null,
    length: 0,
  } as Storage;
}

describe("chat view preference", () => {
  it("accepts only the bounded view vocabulary and falls back safely", () => {
    expect(readChatViewMode(storage("cli"))).toBe("cli");
    expect(readChatViewMode(storage("<script>alert(1)</script>"))).toBe(DEFAULT_CHAT_VIEW_MODE);
    expect(readChatViewMode(storage(""))).toBe(DEFAULT_CHAT_VIEW_MODE);
  });

  it("persists the selected mode under the local UI preference key", () => {
    const target = storage();
    persistChatViewMode("cli", target);
    expect(target.getItem(CHAT_VIEW_MODE_KEY)).toBe("cli");
    persistChatViewMode("standard", target);
    expect(target.getItem(CHAT_VIEW_MODE_KEY)).toBe("standard");
  });
});
