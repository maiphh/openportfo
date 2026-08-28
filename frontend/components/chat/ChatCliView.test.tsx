import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatCliView from "@/components/chat/ChatCliView";

function props() {
  return {
    messages: [],
    draft: "",
    statusText: null,
    error: null,
    sending: false,
    pending: false,
    pendingId: null,
    reducedMotion: false,
    fullscreen: false,
    signedIn: true,
    onDraftChange: vi.fn(),
    onSubmit: vi.fn(),
    onSuggestion: vi.fn(),
    onMessageEntered: vi.fn(),
    onComposerReady: vi.fn(),
    commandMenu: {
      open: false,
      options: [],
      activeIndex: 0,
      setActiveIndex: vi.fn(),
      select: vi.fn(),
      onKeyDown: vi.fn(() => false),
    },
  };
}

describe("ChatCliView", () => {
  afterEach(cleanup);

  it("uses the Brainless Codex primitives for the live transcript and composer", () => {
    const onDraftChange = vi.fn();
    const onSubmit = vi.fn();
    render(
      <ChatCliView
        {...props()}
        draft="hello"
        onDraftChange={onDraftChange}
        onSubmit={onSubmit}
        messages={[
          { id: "user", role: "user", content: "Show my portfolio", createdAt: 1 },
          {
            id: "assistant",
            role: "assistant",
            content: "Your **portfolio** is ready.",
            createdAt: 2,
            activities: [
              { name: "get_portfolio", label: "Reading portfolio", status: "completed" },
              { name: "get_quote", label: "Checking a quote", status: "started" },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText("OpenPortfo Agent CLI")).toBeInTheDocument();
    expect(screen.queryByText("OpenAI Codex")).toBeNull();
    expect(screen.queryByText("/model")).toBeNull();
    expect(screen.queryByText("~/portfolio")).toBeNull();
    expect(screen.getByText("Show my portfolio")).toBeInTheDocument();
    expect(screen.getByText("Your")).toBeInTheDocument();
    expect(screen.getByText("Reading portfolio")).toBeInTheDocument();
    expect(screen.getByText("Checking a quote")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Prompt" })).toHaveValue("hello");
    const cliMessages = screen.getAllByTestId("cli-message");
    expect(cliMessages[0]).toHaveAttribute("data-role", "user");
    expect(cliMessages[0]).toHaveAttribute("data-message-tone", "user");
    expect(cliMessages[0]).toHaveClass("border", "bg-[#252525]");
    expect(cliMessages[0].querySelector('[aria-hidden="true"]')).toHaveTextContent("\u203a");
    expect(cliMessages[1]).toHaveAttribute("data-role", "assistant");
    expect(cliMessages[1]).toHaveAttribute("data-message-tone", "assistant");
    expect(cliMessages[1]).not.toHaveClass("bg-[#252525]");

    const input = screen.getByRole("combobox", { name: "Prompt" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("renders working, failure, and safe tool states", () => {
    render(
      <ChatCliView
        {...props()}
        pending
        statusText="Writing a response"
        error="The assistant could not complete that request."
        messages={[
          {
            id: "failed",
            role: "assistant",
            content: "The request was not completed.",
            createdAt: 1,
            failure: { ambiguous: true },
            activities: [
              { name: "internal_provider_detail", label: "provider secret", status: "failed" },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Writing a response");
    const alerts = screen.getAllByRole("alert");
    expect(alerts).toHaveLength(2);
    expect(alerts.some((alert) => alert.textContent?.includes("The request was not completed."))).toBe(true);
    expect(alerts.some((alert) => alert.textContent?.includes("Verify your holdings or watchlist before trying again."))).toBe(true);
    expect(screen.getByText("Assistant action")).toBeInTheDocument();
    expect(screen.queryByText("provider secret")).toBeNull();
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("submits the controlled form without a second dispatch from Enter", () => {
    const onSubmit = vi.fn();
    render(<ChatCliView {...props()} onSubmit={onSubmit} draft="question" />);
    const input = screen.getByRole("combobox", { name: "Prompt" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledTimes(1);
    fireEvent.submit(screen.getByRole("form", { name: "CLI message composer" }));
    expect(onSubmit).toHaveBeenCalledTimes(2);
  });

  it("keeps a reader's scroll position and exposes jump-to-latest", () => {
    const first = { id: "one", role: "assistant" as const, content: "first", createdAt: 1 };
    const second = { id: "two", role: "assistant" as const, content: "second", createdAt: 2 };
    const viewProps = props();
    const { rerender } = render(<ChatCliView {...viewProps} messages={[first]} />);
    const log = screen.getByRole("log", { name: "CLI chat messages" });
    const scrollTo = vi.fn();
    Object.defineProperties(log, {
      scrollHeight: { configurable: true, value: 1_000 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, writable: true, value: 100 },
      scrollTo: { configurable: true, value: scrollTo },
    });

    fireEvent.scroll(log);
    expect(screen.getByRole("button", { name: "Jump to latest" })).toBeInTheDocument();
    rerender(<ChatCliView {...viewProps} messages={[first, second]} />);
    expect(log.scrollTop).toBe(100);

    fireEvent.click(screen.getByRole("button", { name: "Jump to latest" }));
    expect(scrollTo).toHaveBeenCalledWith({ top: 1_000, behavior: "smooth" });
    expect(screen.queryByRole("button", { name: "Jump to latest" })).toBeNull();
  });
});
