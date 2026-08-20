import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatMessageList from "@/components/chat/ChatMessageList";

const message = { id: "one", role: "assistant" as const, content: "Hello", createdAt: 1 };

describe("ChatMessageList", () => {
  afterEach(cleanup);

  it("exposes a live log and offers jump-to-latest after the reader scrolls away", () => {
    render(<ChatMessageList messages={[message]} statusText={null} pending={false} />);
    const log = screen.getByRole("log", { name: "Chat messages" });
    Object.defineProperties(log, {
      scrollHeight: { configurable: true, value: 1000 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, writable: true, value: 0 },
    });

    fireEvent.scroll(log);
    expect(screen.getByRole("button", { name: "Jump to latest" })).toBeInTheDocument();
  });

  it("renders prompt suggestions for an empty conversation", () => {
    render(<ChatMessageList messages={[]} statusText={null} pending={false} empty onSuggestion={() => undefined} />);
    expect(screen.getByRole("heading", { name: "What can I help with?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show my portfolio" })).toBeInTheDocument();
  });

  it("renders a pending public status once and leaves restored rows unanimated", () => {
    render(
      <ChatMessageList
        messages={[
          { id: "restored", role: "assistant", content: "Saved answer", createdAt: 1 },
          { id: "pending", role: "assistant", content: "", createdAt: 2, streaming: true, isNew: true },
        ]}
        statusText="Thinking about your request"
        pending
        pendingId="pending"
      />,
    );
    expect(screen.getAllByText("Thinking about your request")).toHaveLength(1);
    expect(screen.getByText("Saved answer").closest("article")).not.toHaveClass("chat-message-row--new");
    expect(screen.getByText("Thinking about your request").closest("article")).toHaveClass("chat-message-row--new");
  });

  it("uses instant scrolling when reduced motion is requested", () => {
    render(<ChatMessageList messages={[message]} statusText={null} pending={false} reducedMotion />);
    const log = screen.getByRole("log", { name: "Chat messages" });
    const scrollTo = vi.fn();
    Object.defineProperties(log, {
      scrollHeight: { configurable: true, value: 1000 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, writable: true, value: 0 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    fireEvent.scroll(log);
    fireEvent.click(screen.getByRole("button", { name: "Jump to latest" }));
    expect(scrollTo).toHaveBeenCalledWith({ top: 1000, behavior: "auto" });
  });
});
