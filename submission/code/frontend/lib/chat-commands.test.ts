import { describe, expect, it } from "vitest";
import {
  CHAT_COMMANDS,
  CHAT_SLASH_ALIASES,
  completeChatCommand,
  expandChatCommand,
  matchChatCommands,
} from "@/lib/chat-commands";
import { PUBLIC_CHAT_TOOL_NAMES, isPublicChatTool } from "@/lib/chat-tools";

describe("chat commands", () => {
  it("filters slash aliases and exact tool mentions", () => {
    expect(matchChatCommands("/quo")?.options.map((option) => option.token)).toEqual(["/quote"]);
    expect(matchChatCommands("@get_q")?.options.map((option) => option.token)).toEqual(["@get_quote"]);
    expect(matchChatCommands("ask /quote")?.options).toBeUndefined();
    expect(matchChatCommands("/quote BTC")?.options).toBeUndefined();
  });

  it("completes a selected command with room for arguments", () => {
    const option = matchChatCommands("/port")?.options[0];
    expect(option).toBeDefined();
    expect(completeChatCommand(option!)).toBe("/portfolio ");
  });

  it("expands only allow-listed directives into bounded agent tool instructions", () => {
    expect(expandChatCommand("/quote BTC")).toBe(
      "Use the get_quote tool to handle this request. User input: BTC",
    );
    expect(expandChatCommand("@get_quote AAPL")).toBe(
      "Use the get_quote tool to handle this request. User input: AAPL",
    );
    expect(expandChatCommand("@analyze_portfolio")).toBe(
      "Use the analyze_portfolio tool to handle this request.",
    );
    expect(expandChatCommand("/unknown secret")).toBe("/unknown secret");
    expect(expandChatCommand("ordinary question")).toBe("ordinary question");
  });

  it("keeps @ mentions exactly aligned with the canonical public tool names", () => {
    const mentionTools = CHAT_COMMANDS
      .filter((option) => option.token.startsWith("@"))
      .map((option) => option.tool);
    expect(mentionTools).toEqual(PUBLIC_CHAT_TOOL_NAMES);
  });

  it("maps every slash alias to a canonical public tool", () => {
    expect(CHAT_SLASH_ALIASES.every((alias) => isPublicChatTool(alias.tool))).toBe(true);
  });

  it("leaves unknown tool names literal and unexpanded", () => {
    expect(isPublicChatTool("not_a_public_tool")).toBe(false);
    expect(expandChatCommand("@not_a_public_tool AAPL")).toBe("@not_a_public_tool AAPL");
    expect(expandChatCommand("/not-a-command AAPL")).toBe("/not-a-command AAPL");
  });
});
