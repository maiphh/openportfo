import { apiBase } from "@/lib/api";
import { bearerHeader } from "@/lib/auth";
import type { ChatSessionMessage } from "@/lib/chat-session";
import {
  isMutatingPublicChatTool,
  isPublicChatTool,
  publicChatToolLabel,
} from "@/lib/chat-tools";

export {
  PUBLIC_CHAT_TOOL_LABELS,
  PUBLIC_CHAT_TOOL_NAMES,
  PUBLIC_CHAT_TOOL_REGISTRY,
  isMutatingPublicChatTool,
  isPublicChatTool,
  publicChatToolDescription,
  publicChatToolLabel,
} from "@/lib/chat-tools";

export type ChatToolActivity = {
  name: string;
  label: string;
  status: "started" | "completed" | "failed";
};

export type ChatStreamEvent =
  | { type: "status"; status: string; message: string }
  | { type: "tool"; activity: ChatToolActivity }
  | { type: "message"; content: string; done: boolean; toolCalls?: ChatToolActivity[] }
  | { type: "done"; ok: boolean }
  | { type: "error"; message: string; status?: number; ambiguous?: boolean };

export type ChatResponse = {
  content: string;
  toolCalls: ChatToolActivity[];
};

export class ChatApiError extends Error {
  status: number;
  authRequired: boolean;
  ambiguous: boolean;

  constructor(status: number, message: string, options?: { ambiguous?: boolean }) {
    super(message || `Chat request failed (${status})`);
    this.name = "ChatApiError";
    this.status = status;
    this.authRequired = status === 401 || status === 403;
    this.ambiguous = options?.ambiguous === true;
  }
}

type FetchLike = typeof fetch;

export type SendChatOptions = {
  token: string;
  message: string;
  history?: readonly Pick<ChatSessionMessage, "role" | "content">[];
  model?: string | null;
  signal?: AbortSignal;
  fetchImpl?: FetchLike;
  clientRequestId?: string;
  onEvent?: (event: ChatStreamEvent) => void;
};

function safeTool(value: unknown): ChatToolActivity {
  const candidate = value && typeof value === "object" ? value as Record<string, unknown> : {};
  const name = isPublicChatTool(candidate.name) ? candidate.name : "assistant_action";
  const label = publicChatToolLabel(name);
  const status = candidate.status === "started" || candidate.status === "failed"
    ? candidate.status
    : "completed";
  return { name, label, status };
}

function safeMessage(value: unknown): string {
  if (typeof value !== "string") return "Unable to complete the chat request.";
  return value.slice(0, 8_000);
}

function safeEvent(eventName: string, value: unknown): ChatStreamEvent | null {
  const payload = value && typeof value === "object" ? value as Record<string, unknown> : {};
  if (eventName === "status") {
    const status = typeof payload.status === "string" ? payload.status : "working";
    return {
      type: "status",
      status: status.slice(0, 40),
      message: safeMessage(payload.message || "Working on your request"),
    };
  }
  if (eventName === "tool") {
    return { type: "tool", activity: safeTool(payload) };
  }
  if (eventName === "message") {
    const calls = Array.isArray(payload.toolCalls)
      ? payload.toolCalls.map(safeTool)
      : undefined;
    return {
      type: "message",
      content: safeMessage(payload.content),
      done: payload.done !== false,
      ...(calls ? { toolCalls: calls } : {}),
    };
  }
  if (eventName === "done") {
    return { type: "done", ok: payload.ok !== false };
  }
  if (eventName === "error") {
    const rawStatus = payload.status;
    const parsedStatus = typeof rawStatus === "number" && Number.isFinite(rawStatus) ? rawStatus : undefined;
    return {
      type: "error",
      message: safeMessage(payload.message),
      ...(parsedStatus === undefined ? {} : { status: parsedStatus }),
      ...(payload.ambiguous === true ? { ambiguous: true } : {}),
    };
  }
  // Heartbeats keep idle connections alive but are not user-facing activity.
  if (eventName === "heartbeat") return null;
  return null;
}

export function parseSseFrame(frame: string): { event: string; data: unknown } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    const value = separator === -1 ? "" : line.slice(separator + 1).replace(/^ /, "");
    if (field === "event") event = value.trim();
    if (field === "data") dataLines.push(value);
  }
  if (!dataLines.length) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) as unknown };
  } catch {
    return null;
  }
}

async function consumeSse(
  response: Response,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<ChatResponse> {
  if (!response.body) throw new ChatApiError(502, "The chat stream was empty.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let content = "";
  let toolCalls: ChatToolActivity[] = [];
  let mutationActivitySeen = false;

  const consumeFrame = (frame: string) => {
    const parsed = parseSseFrame(frame);
    if (!parsed) return;
    const event = safeEvent(parsed.event, parsed.data);
    if (!event) return;
    if (event.type === "message") {
      content = event.content;
      toolCalls = event.toolCalls || toolCalls;
      if (toolCalls.some((activity) => isMutatingPublicChatTool(activity.name) && activity.status !== "failed")) {
        mutationActivitySeen = true;
      }
    } else if (event.type === "tool") {
      if (isMutatingPublicChatTool(event.activity.name) && event.activity.status !== "failed") {
        mutationActivitySeen = true;
      }
    }
    onEvent(event);
    if (event.type === "error") {
      throw new ChatApiError(event.status || 502, event.message, { ambiguous: event.ambiguous });
    }
  };

  try {
    while (true) {
      const chunk = await reader.read();
      buffer += decoder.decode(chunk.value || new Uint8Array(), { stream: !chunk.done });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() || "";
      for (const frame of frames) consumeFrame(frame);
      if (chunk.done) break;
    }
    if (buffer.trim()) consumeFrame(buffer);
  } catch (cause: unknown) {
    if (mutationActivitySeen && !(cause instanceof ChatApiError && cause.ambiguous)) {
      throw new ChatApiError(
        502,
        "A requested change may have completed; verify it before retrying.",
        { ambiguous: true },
      );
    }
    throw cause;
  }
  if (!content) throw new ChatApiError(502, "The chat did not return a response.");
  return { content, toolCalls };
}

function requestBody(options: SendChatOptions): Record<string, unknown> {
  const history = (options.history || [])
    .filter((item) => item.role === "user" || item.role === "assistant")
    .map((item) => ({ role: item.role, content: item.content.slice(0, 4_000) }))
    .slice(-32);
  const requestId = options.clientRequestId?.trim();
  return {
    message: options.message.slice(0, 8_000),
    history,
    ...(options.model?.trim() ? { model: options.model.trim().slice(0, 200) } : {}),
    ...(requestId && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$/.test(requestId)
      ? { clientRequestId: requestId }
      : {}),
  };
}

async function readError(response: Response): Promise<{ message: string; ambiguous: boolean }> {
  try {
    const body = await response.json() as { detail?: unknown; ambiguous?: unknown };
    return {
      message: typeof body.detail === "string" ? body.detail.slice(0, 240) : "Chat request failed.",
      ambiguous: body.ambiguous === true || response.headers.get("X-Chat-Ambiguous") === "true",
    };
  } catch {
    return {
      message: "Chat request failed.",
      ambiguous: response.headers.get("X-Chat-Ambiguous") === "true",
    };
  }
}

/** Send a chat turn through SSE, falling back to the legacy JSON endpoint. */
export async function sendChatMessage(options: SendChatOptions): Promise<ChatResponse> {
  const fetchImpl = options.fetchImpl || fetch;
  const headers = {
    Accept: "text/event-stream",
    "Content-Type": "application/json",
    ...bearerHeader(options.token),
  };
  const body = JSON.stringify(requestBody(options));
  let response = await fetchImpl(`${apiBase()}/api/chat/stream`, {
    method: "POST",
    headers,
    body,
    signal: options.signal,
    cache: "no-store",
  });

  // Older deployments retain POST /api/chat; keep the widget usable during a
  // rolling deploy while the new route is introduced.
  if (response.status === 404 || response.status === 405) {
    response = await fetchImpl(`${apiBase()}/api/chat`, {
      method: "POST",
      headers: { ...headers, Accept: "application/json" },
      body,
      signal: options.signal,
      cache: "no-store",
    });
    if (!response.ok) {
      const failure = await readError(response);
      throw new ChatApiError(response.status, failure.message, { ambiguous: failure.ambiguous });
    }
    const legacy = await response.json() as Record<string, unknown>;
    const content = safeMessage(legacy.reply);
    if (!content) throw new ChatApiError(502, "The chat did not return a response.");
    const event: ChatStreamEvent = {
      type: "message",
      content,
      done: true,
      toolCalls: Array.isArray(legacy.toolCalls) ? legacy.toolCalls.map(safeTool) : [],
    };
    options.onEvent?.(event);
    options.onEvent?.({ type: "done", ok: true });
    return { content, toolCalls: event.toolCalls || [] };
  }
  if (!response.ok) {
    const failure = await readError(response);
    throw new ChatApiError(response.status, failure.message, { ambiguous: failure.ambiguous });
  }
  return consumeSse(response, (event) => options.onEvent?.(event));
}
