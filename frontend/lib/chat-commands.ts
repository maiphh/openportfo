import {
  PUBLIC_CHAT_TOOL_NAMES,
  PUBLIC_CHAT_TOOL_REGISTRY,
  type PublicChatToolName,
} from "@/lib/chat-tools";

export type ChatCommandTrigger = "/" | "@";

export type ChatCommandOption = {
  token: string;
  tool: PublicChatToolName;
  label: string;
  description: string;
};

type ChatSlashAlias = {
  token: string;
  tool: PublicChatToolName;
  label: string;
};

export const CHAT_SLASH_ALIASES: ReadonlyArray<ChatSlashAlias> = [
  { token: "/search", tool: "search_assets", label: "Search assets" },
  { token: "/add", tool: "add_holding", label: "Add holding" },
  { token: "/remove", tool: "remove_holding", label: "Remove holding" },
  { token: "/holdings", tool: "list_holdings", label: "List holdings" },
  { token: "/portfolio", tool: "get_portfolio", label: "Show portfolio" },
  { token: "/quote", tool: "get_quote", label: "Get quote" },
  { token: "/analyze", tool: "analyze_asset", label: "Analyze asset" },
  { token: "/analyze-portfolio", tool: "analyze_portfolio", label: "Analyze portfolio" },
  { token: "/news", tool: "get_news", label: "Market news" },
  { token: "/watch", tool: "add_watchlist", label: "Add to watchlist" },
  { token: "/unwatch", tool: "remove_watchlist", label: "Remove from watchlist" },
];

const SLASH_COMMANDS: ReadonlyArray<ChatCommandOption> = CHAT_SLASH_ALIASES.map((alias) => ({
  ...alias,
  description: PUBLIC_CHAT_TOOL_REGISTRY[alias.tool].description,
}));

const TOOL_MENTIONS: ReadonlyArray<ChatCommandOption> = PUBLIC_CHAT_TOOL_NAMES.map((tool) => ({
  token: `@${tool}`,
  tool,
  label: tool,
  description: PUBLIC_CHAT_TOOL_REGISTRY[tool].description,
}));

export const CHAT_COMMANDS: ReadonlyArray<ChatCommandOption> = [
  ...SLASH_COMMANDS,
  ...TOOL_MENTIONS,
];

export type ChatCommandMatch = {
  trigger: ChatCommandTrigger;
  query: string;
  options: ChatCommandOption[];
};

export function matchChatCommands(value: string): ChatCommandMatch | null {
  const candidate = value.trimStart();
  const match = /^([/@])([A-Za-z0-9_-]*)$/.exec(candidate);
  if (!match) return null;
  const trigger = match[1] as ChatCommandTrigger;
  const query = match[2].toLowerCase();
  const options = CHAT_COMMANDS
    .filter((option) => option.token.startsWith(trigger))
    .filter((option) => option.token.slice(1).toLowerCase().startsWith(query))
    .slice(0, 12);
  return { trigger, query, options };
}

export function completeChatCommand(option: ChatCommandOption): string {
  return `${option.token} `;
}

export function expandChatCommand(value: string): string {
  const trimmed = value.trim();
  const match = /^([/@][A-Za-z0-9_-]+)(?:\s+([\s\S]*))?$/.exec(trimmed);
  if (!match) return trimmed;
  const option = CHAT_COMMANDS.find((candidate) => candidate.token.toLowerCase() === match[1].toLowerCase());
  if (!option) return trimmed;
  const argumentsText = (match[2] || "").trim().slice(0, 4_000);
  const base = `Use the ${option.tool} tool to handle this request.`;
  return argumentsText ? `${base} User input: ${argumentsText}` : base;
}
