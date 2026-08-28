import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatRenderer, { CHAT_RENDERERS } from "@/components/chat/ChatRenderer";
import type { ChatViewMode } from "@/lib/chat-view";

function Harness({ mode, onSubmit = vi.fn() }: { mode: ChatViewMode; onSubmit?: () => void }) {
  const [draft, setDraft] = useState("");
  return (
    <ChatRenderer
      mode={mode}
      messages={[]}
      draft={draft}
      statusText={null}
      error={null}
      sending={false}
      pending={false}
      pendingId={null}
      reducedMotion={false}
      fullscreen={false}
      signedIn
      onDraftChange={setDraft}
      onSubmit={onSubmit}
      onSuggestion={setDraft}
      onMessageEntered={vi.fn()}
      onComposerReady={vi.fn()}
    />
  );
}

describe("ChatRenderer", () => {
  afterEach(cleanup);

  it("registers each presentation behind the normalized renderer contract", () => {
    expect(Object.keys(CHAT_RENDERERS)).toEqual(["standard", "cli"]);
  });

  it.each([
    ["standard", "Message the personal assistant"],
    ["cli", "Prompt"],
  ] as const)("offers slash commands in %s mode without submitting the partial token", (mode, inputName) => {
    const onSubmit = vi.fn();
    render(<Harness mode={mode} onSubmit={onSubmit} />);
    const input = screen.getByRole("combobox", { name: inputName });
    fireEvent.change(input, { target: { value: "/quo" } });
    expect(screen.getByRole("option", { name: /\/quote/i })).toBeInTheDocument();
    fireEvent.keyDown(input, { key: "Enter" });
    expect(input).toHaveValue("/quote ");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("offers exact allow-listed tools with @ and supports keyboard selection", () => {
    render(<Harness mode="cli" />);
    const input = screen.getByRole("combobox", { name: "Prompt" });
    fireEvent.change(input, { target: { value: "@get_q" } });
    expect(screen.getByRole("option", { name: /@get_quote/i })).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-controls", "cli-chat-command-menu");
    expect(input).toHaveAttribute("aria-activedescendant", "chat-command-cli-0");
    fireEvent.keyDown(input, { key: "Tab" });
    expect(input).toHaveValue("@get_quote ");
  });

  it("selects a command with the mouse without submitting or moving focus", () => {
    const onSubmit = vi.fn();
    render(<Harness mode="standard" onSubmit={onSubmit} />);
    const input = screen.getByRole("combobox", { name: "Message the personal assistant" });
    input.focus();
    fireEvent.change(input, { target: { value: "/quo" } });
    const option = screen.getByRole("option", { name: /\/quote/i });
    fireEvent.mouseDown(option);
    fireEvent.click(option);
    expect(input).toHaveValue("/quote ");
    expect(document.activeElement).toBe(input);
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("keeps the active command visible while navigating the listbox", () => {
    render(<Harness mode="standard" />);
    const input = screen.getByRole("combobox", { name: "Message the personal assistant" });
    input.focus();
    fireEvent.change(input, { target: { value: "/" } });
    const menu = screen.getByRole("listbox", { name: "Agent commands and tools" });
    const options = screen.getAllByRole("option");
    Object.defineProperties(menu, {
      clientHeight: { configurable: true, value: 40 },
      scrollHeight: { configurable: true, value: options.length * 32 },
      scrollTop: { configurable: true, writable: true, value: 0 },
    });
    const scrollSpies = options.map((option, index) => {
      const scrollIntoView = vi.fn();
      Object.defineProperties(option, {
        offsetTop: { configurable: true, value: index * 32 },
        offsetHeight: { configurable: true, value: 32 },
      });
      Object.defineProperty(option, "scrollIntoView", { configurable: true, value: scrollIntoView });
      return scrollIntoView;
    });

    for (let index = 0; index < 6; index += 1) {
      fireEvent.keyDown(input, { key: "ArrowDown" });
    }
    expect(input).toHaveAttribute("aria-activedescendant", "chat-command-standard-6");
    expect(options[6]).toHaveAttribute("aria-selected", "true");
    expect(scrollSpies[6]).toHaveBeenCalledWith({ block: "nearest" });

    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(input).toHaveAttribute("aria-activedescendant", "chat-command-standard-5");
    expect(options[5]).toHaveAttribute("aria-selected", "true");
    expect(scrollSpies[5]).toHaveBeenCalledWith({ block: "nearest" });
    expect(document.activeElement).toBe(input);
  });

  it("keeps Shift+Enter and IME Enter out of command completion in Standard mode", () => {
    const onSubmit = vi.fn();
    render(<Harness mode="standard" onSubmit={onSubmit} />);
    const input = screen.getByRole("combobox", { name: "Message the personal assistant" });
    fireEvent.change(input, { target: { value: "/quo" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
    expect(input).toHaveValue("/quo");
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    fireEvent.compositionStart(input);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(input).toHaveValue("/quo");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
