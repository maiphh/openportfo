import { describe, expect, it, vi } from "vitest";
import { parseSseFrame, sendChatMessage } from "@/lib/chat";

describe("chat transport", () => {
  it("parses SSE frames without treating data text as markup", () => {
    expect(parseSseFrame("event: status\ndata: {\"status\":\"thinking\"}\n")).toEqual({
      event: "status",
      data: { status: "thinking" },
    });
    expect(parseSseFrame(": keep-alive\n\n")).toBeNull();
  });

  it("accepts only safe activity metadata from the stream", async () => {
    const response = new Response(
      [
        "event: status\ndata: {\"status\":\"thinking\",\"message\":\"Working\"}\n\n",
        "event: tool\ndata: {\"name\":\"add_holding\",\"status\":\"started\",\"arguments\":{\"token\":\"hidden\"}}\n\n",
        "event: message\ndata: {\"content\":\"**Done**\",\"done\":true,\"toolCalls\":[{\"name\":\"add_holding\",\"status\":\"completed\",\"result\":{\"userId\":\"hidden\"}}]}\n\n",
        "event: done\ndata: {\"ok\":true}\n\n",
      ].join(""),
      { status: 200, headers: { "Content-Type": "text/event-stream" } },
    );
    const onEvent = vi.fn();
    const result = await sendChatMessage({ token: "secret", message: "hello", fetchImpl: vi.fn(async () => response), onEvent });
    expect(result.content).toBe("**Done**");
    expect(result.toolCalls).toEqual([{ name: "add_holding", label: "Updating holdings", status: "completed" }]);
    expect(JSON.stringify(onEvent.mock.calls)).not.toContain("token");
    expect(JSON.stringify(onEvent.mock.calls)).not.toContain("userId");
  });

  it("ignores heartbeats and sends a bounded idempotency key", async () => {
    const fetchImpl = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      expect(JSON.parse(String(init?.body))).toMatchObject({ clientRequestId: "request-123" });
      return new Response(
        "event: heartbeat\ndata: {\"at\":1}\n\n" +
        "event: message\ndata: {\"content\":\"hello\",\"done\":true}\n\n" +
        "event: done\ndata: {\"ok\":true}\n\n",
        { status: 200 },
      );
    });
    const onEvent = vi.fn();
    await sendChatMessage({
      token: "secret",
      message: "hello",
      clientRequestId: "request-123",
      fetchImpl,
      onEvent,
    });
    expect(onEvent.mock.calls.some(([event]) => event.type === "heartbeat")).toBe(false);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it("preserves ambiguity on a completed-write failure event", async () => {
    const response = new Response(
      "event: tool\ndata: {\"name\":\"add_holding\",\"status\":\"completed\"}\n\n" +
      "event: error\ndata: {\"status\":502,\"message\":\"A requested change may have completed.\",\"ambiguous\":true}\n\n",
      { status: 200 },
    );
    await expect(sendChatMessage({ token: "secret", message: "add", fetchImpl: vi.fn(async () => response) }))
      .rejects.toMatchObject({ status: 502, ambiguous: true });
  });

  it("turns a network loss after a completed write into an ambiguity error", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode(
          "event: tool\ndata: {\"name\":\"add_holding\",\"status\":\"completed\"}\n\n",
        ));
        setTimeout(() => controller.error(new Error("connection lost")), 0);
      },
    });
    const response = new Response(body, { status: 200 });
    await expect(sendChatMessage({ token: "secret", message: "add", fetchImpl: vi.fn(async () => response) }))
      .rejects.toMatchObject({ status: 502, ambiguous: true });
  });

  it("handles JSON and SSE delimiters split across response chunks", async () => {
    const chunks = [
      "event: message\ndata: {\"content\":\"he",
      "llo\",\"done\":true}\n\n: heartbeat\n\n",
      "event: done\ndata: {\"ok\":true}\n\n",
    ];
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
        controller.close();
      },
    });
    const response = new Response(body, { status: 200 });
    await expect(sendChatMessage({ token: "secret", message: "hello", fetchImpl: vi.fn(async () => response) }))
      .resolves.toMatchObject({ content: "hello" });
  });

  it("falls back to the compatibility JSON endpoint", async () => {
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(new Response("", { status: 404 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ reply: "hello", toolCalls: [{ name: "get_quote", status: "completed", arguments: { secret: true } }] }), { status: 200 }));
    const result = await sendChatMessage({ token: "secret", message: "hello", fetchImpl, onEvent: vi.fn() });
    expect(result.content).toBe("hello");
    expect(result.toolCalls).toEqual([{ name: "get_quote", label: "Checking a quote", status: "completed" }]);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });
});
