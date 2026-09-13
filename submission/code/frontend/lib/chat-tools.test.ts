import { describe, expect, it } from "vitest";
import {
  PUBLIC_CHAT_TOOL_LABELS,
  PUBLIC_CHAT_TOOL_NAMES,
  PUBLIC_CHAT_TOOL_REGISTRY,
  isMutatingPublicChatTool,
  isPublicChatTool,
  publicChatToolLabel,
} from "@/lib/chat-tools";

describe("canonical public chat tools", () => {
  it("derives labels and names from one registry", () => {
    expect(PUBLIC_CHAT_TOOL_NAMES).toEqual(Object.keys(PUBLIC_CHAT_TOOL_REGISTRY));
    expect(PUBLIC_CHAT_TOOL_NAMES.every((name) => PUBLIC_CHAT_TOOL_LABELS[name] === PUBLIC_CHAT_TOOL_REGISTRY[name].label)).toBe(true);
  });

  it("rejects inherited or unknown names at the untrusted stream boundary", () => {
    expect(isPublicChatTool("toString")).toBe(false);
    expect(isPublicChatTool("__proto__")).toBe(false);
    expect(isPublicChatTool("unknown_tool")).toBe(false);
    expect(publicChatToolLabel("unknown_tool")).toBe("Assistant action");
  });

  it("keeps mutation classification in the canonical definitions", () => {
    expect(isMutatingPublicChatTool("add_holding")).toBe(true);
    expect(isMutatingPublicChatTool("remove_holding")).toBe(true);
    expect(isMutatingPublicChatTool("get_quote")).toBe(false);
    expect(isMutatingPublicChatTool("unknown_tool")).toBe(false);
  });
});
