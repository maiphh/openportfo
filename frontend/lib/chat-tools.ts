/**
 * Từ điển công cụ công khai duy nhất dùng chung cho transport, renderer và
 * menu lệnh. Module này phải thuần: không import auth, API hoặc React.
 */
type PublicChatToolDefinitionShape = {
  label: string;
  description: string;
  mutates: boolean;
};

export const PUBLIC_CHAT_TOOL_REGISTRY = {
  search_assets: {
    label: "Searching assets",
    description: "Search supported stocks and crypto assets",
    mutates: false,
  },
  add_holding: {
    label: "Updating holdings",
    description: "Add or increase a portfolio holding",
    mutates: true,
  },
  remove_holding: {
    label: "Updating holdings",
    description: "Remove or reduce a portfolio holding",
    mutates: true,
  },
  list_holdings: {
    label: "Reading holdings",
    description: "List current portfolio holdings",
    mutates: false,
  },
  get_portfolio: {
    label: "Reading portfolio",
    description: "Show the current portfolio summary",
    mutates: false,
  },
  get_quote: {
    label: "Checking a quote",
    description: "Look up a live asset quote",
    mutates: false,
  },
  analyze_asset: {
    label: "Analyzing an asset",
    description: "Analyze a stock or crypto asset",
    mutates: false,
  },
  analyze_portfolio: {
    label: "Analyzing portfolio",
    description: "Analyze portfolio allocation and performance",
    mutates: false,
  },
  get_news: {
    label: "Reading market news",
    description: "Find recent market news",
    mutates: false,
  },
  add_watchlist: {
    label: "Updating watchlist",
    description: "Add an asset to the watchlist",
    mutates: true,
  },
  remove_watchlist: {
    label: "Updating watchlist",
    description: "Remove an asset from the watchlist",
    mutates: true,
  },
} as const satisfies Record<string, PublicChatToolDefinitionShape>;

export type PublicChatToolName = keyof typeof PUBLIC_CHAT_TOOL_REGISTRY;
export type PublicChatToolDefinition = (typeof PUBLIC_CHAT_TOOL_REGISTRY)[PublicChatToolName];

export const PUBLIC_CHAT_TOOL_NAMES: ReadonlyArray<PublicChatToolName> = Object.freeze(
  Object.keys(PUBLIC_CHAT_TOOL_REGISTRY) as PublicChatToolName[],
);

// Suy ra map tương thích từ định nghĩa chuẩn để không tạo thêm nguồn dữ liệu.
export const PUBLIC_CHAT_TOOL_LABELS: Readonly<Record<PublicChatToolName, string>> = Object.freeze(
  Object.fromEntries(
    PUBLIC_CHAT_TOOL_NAMES.map((name) => [name, PUBLIC_CHAT_TOOL_REGISTRY[name].label]),
  ) as Record<PublicChatToolName, string>,
);

export function isPublicChatTool(value: unknown): value is PublicChatToolName {
  return typeof value === "string"
    && Object.prototype.hasOwnProperty.call(PUBLIC_CHAT_TOOL_REGISTRY, value);
}

export function publicChatToolLabel(value: unknown): string {
  return isPublicChatTool(value) ? PUBLIC_CHAT_TOOL_REGISTRY[value].label : "Assistant action";
}

export function publicChatToolDescription(value: unknown): string | null {
  return isPublicChatTool(value) ? PUBLIC_CHAT_TOOL_REGISTRY[value].description : null;
}

export function isMutatingPublicChatTool(value: unknown): boolean {
  return isPublicChatTool(value) && PUBLIC_CHAT_TOOL_REGISTRY[value].mutates;
}
