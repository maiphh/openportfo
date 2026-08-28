import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  token: "token-a" as string | null,
  profile: { userId: "alice", email: "alice@example.com", name: "Alice" },
  fetchAuthMe: vi.fn(),
  readAuthToken: vi.fn(),
  isAuthTokenStorageKey: vi.fn((key: string | null) => key === "openportfo.accessToken"),
  clearAuthToken: vi.fn(),
  sendChatMessage: vi.fn(),
  beginHostedUiLogin: vi.fn(),
  isCognitoConfigured: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  AUTH_CHANGE_EVENT: "openportfo:auth-change",
  AuthApiError: class AuthApiError extends Error {
    status: number;
    authRequired: boolean;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
      this.authRequired = status === 401 || status === 403;
    }
  },
  clearAuthToken: mocks.clearAuthToken,
  fetchAuthMe: mocks.fetchAuthMe,
  isAuthTokenStorageKey: mocks.isAuthTokenStorageKey,
  readAuthToken: mocks.readAuthToken,
}));

vi.mock("@/lib/chat", () => ({
  ChatApiError: class ChatApiError extends Error {
    status: number;
    authRequired: boolean;
    ambiguous: boolean;
    constructor(status = 502, message = "chat failed", options?: { ambiguous?: boolean }) {
      super(message);
      this.status = status;
      this.authRequired = status === 401 || status === 403;
      this.ambiguous = options?.ambiguous === true;
    }
  },
  sendChatMessage: mocks.sendChatMessage,
}));

vi.mock("@/lib/cognito", () => ({
  beginHostedUiLogin: mocks.beginHostedUiLogin,
  isCognitoConfigured: mocks.isCognitoConfigured,
}));

import ChatWidget, { clampPosition } from "@/components/chat/ChatWidget";
import { ChatApiError } from "@/lib/chat";
import { chatSessionKey } from "@/lib/chat-session";

describe("ChatWidget", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    mocks.token = "token-a";
    mocks.fetchAuthMe.mockReset().mockResolvedValue(mocks.profile);
    mocks.readAuthToken.mockReset().mockImplementation(() => mocks.token);
    mocks.clearAuthToken.mockReset().mockImplementation(() => {
      mocks.token = null;
      window.dispatchEvent(new Event("openportfo:auth-change"));
    });
    mocks.sendChatMessage.mockReset().mockResolvedValue({ content: "hello", toolCalls: [] });
    mocks.beginHostedUiLogin.mockReset().mockResolvedValue(undefined);
    mocks.isCognitoConfigured.mockReset().mockReturnValue(false);
    window.sessionStorage.clear();
    window.localStorage.clear();
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1024 });
    Object.defineProperty(window, "innerHeight", { configurable: true, value: 768 });
  });

  async function renderReady() {
    render(<ChatWidget />);
    await waitFor(() => expect(mocks.fetchAuthMe).toHaveBeenCalled());
  }

  it("separates drag from click and recovers after pointer cancellation", async () => {
    await renderReady();
    const bubble = screen.getByRole("button", { name: "Open personal assistant" });
    fireEvent.pointerDown(bubble, { button: 0, pointerId: 1, clientX: 900, clientY: 700 });
    fireEvent.pointerMove(bubble, { pointerId: 1, clientX: 940, clientY: 740 });
    fireEvent.pointerUp(bubble, { pointerId: 1, clientX: 940, clientY: 740 });
    fireEvent.click(bubble);
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.pointerDown(bubble, { button: 0, pointerId: 2, clientX: 940, clientY: 740 });
    fireEvent.pointerCancel(bubble, { pointerId: 2 });
    fireEvent.click(bubble);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("clamps the panel on narrow viewports and restores bubble focus on Escape", async () => {
    await renderReady();
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 180 });
    Object.defineProperty(window, "innerHeight", { configurable: true, value: 140 });
    fireEvent(window, new Event("resize"));
    const bubble = screen.getByRole("button", { name: "Open personal assistant" });
    fireEvent.click(bubble);
    const panel = await screen.findByRole("dialog");
    expect(Number.parseFloat(panel.style.width)).toBeLessThanOrEqual(180);
    expect(Number.parseFloat(panel.style.height)).toBeLessThanOrEqual(140);
    expect(panel.querySelector("header")).toHaveAttribute("data-layout", "stacked");
    expect(screen.getByTestId("chat-panel-actions")).toHaveAttribute("data-layout", "wrapped");
    expect(screen.getByTestId("chat-panel-actions").className).toContain("flex-wrap");
    const viewToggle = screen.getByRole("button", { name: /Standard view; switch to CLI view/ });
    expect(viewToggle).toHaveAttribute("title", "Current view: Standard. Switch to CLI view.");
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(bubble));
  });

  it("clamps launcher positions outside the 240px rail, 64px rail, and mobile insets", () => {
    expect(clampPosition({ x: 0, y: 0 }, { width: 800, height: 600 }, 240).x).toBe(240);
    expect(clampPosition({ x: 0, y: 0 }, { width: 800, height: 600 }, 64).x).toBe(64);
    expect(clampPosition({ x: 0, y: 0 }, { width: 800, height: 600 }, 0).x).toBe(12);
  });

  it("re-clamps a stored/live launcher position when the sidebar inset changes", async () => {
    window.localStorage.setItem("openportfo.chat-bubble-position.v1", JSON.stringify({ x: 20, y: 20 }));
    const { rerender } = render(<ChatWidget leftInset={240} />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Open personal assistant" }).style.transform).toContain("240px"));
    rerender(<ChatWidget leftInset={64} />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Open personal assistant" }).style.transform).toContain("64px"));
  });

  it("uses opening/closing presence, focuses the composer, and leaves non-modal Tab navigation alone", async () => {
    await renderReady();
    const bubble = screen.getByRole("button", { name: "Open personal assistant" });
    const originalRequestAnimationFrame = window.requestAnimationFrame;
    const originalCancelAnimationFrame = window.cancelAnimationFrame;
    const frames: FrameRequestCallback[] = [];
    Object.defineProperty(window, "requestAnimationFrame", {
      configurable: true,
      value: (callback: FrameRequestCallback) => {
        frames.push(callback);
        return frames.length;
      },
    });
    Object.defineProperty(window, "cancelAnimationFrame", {
      configurable: true,
      value: (frame: number) => {
        frames[frame - 1] = () => undefined;
      },
    });
    try {
      fireEvent.click(bubble);
      const panel = await screen.findByRole("dialog");
      expect(panel).toHaveAttribute("data-state", "opening");
      expect(panel).toHaveClass("chat-panel--opening");
      expect(panel).toHaveAttribute("data-motion", "hidden");
      expect(panel).not.toHaveClass("chat-panel--open");

      act(() => {
        frames.shift()?.(performance.now());
      });
      await waitFor(() => expect(panel).toHaveAttribute("data-state", "open"));
      expect(panel).toHaveClass("chat-panel--open");
      expect(panel).toHaveAttribute("data-motion", "visible");
      act(() => {
        while (frames.length) frames.shift()?.(performance.now());
      });
      await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText("Message the personal assistant")));

      const tabEvent = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key: "Tab" });
      panel.dispatchEvent(tabEvent);
      expect(tabEvent.defaultPrevented).toBe(false);

      fireEvent.keyDown(window, { key: "Escape" });
      expect(document.getElementById("personal-chat-panel")?.getAttribute("data-state")).toBe("closing");
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    } finally {
      Object.defineProperty(window, "requestAnimationFrame", { configurable: true, value: originalRequestAnimationFrame });
      Object.defineProperty(window, "cancelAnimationFrame", { configurable: true, value: originalCancelAnimationFrame });
    }
  });

  it("keeps a mounted entrance animation after marker consumption and omits it after reopen", async () => {
    await renderReady();
    const bubble = screen.getByRole("button", { name: "Open personal assistant" });
    fireEvent.click(bubble);
    await screen.findByRole("dialog");

    fireEvent.change(screen.getByLabelText("Message the personal assistant"), { target: { value: "remember this" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    const firstRow = (await screen.findByText("remember this")).closest("article");
    expect(firstRow).toHaveClass("chat-message-row--new");

    fireEvent.click(screen.getByRole("button", { name: "Close assistant" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.getElementById("personal-chat-panel")).toBeNull());

    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    await screen.findByRole("dialog");
    const reopenedRow = screen.getByText("remember this").closest("article");
    expect(reopenedRow).not.toHaveClass("chat-message-row--new");
  });

  it("anchors launcher and compact panel to visual viewport offsets and persists drag only on release", async () => {
    const originalVisualViewport = window.visualViewport;
    const visualViewport = {
      width: 320,
      height: 568,
      offsetLeft: 17,
      offsetTop: 29,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    Object.defineProperty(window, "visualViewport", { configurable: true, value: visualViewport });
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    try {
      await renderReady();
      const bubble = screen.getByRole("button", { name: "Open personal assistant" });
      expect(bubble.style.left).toBe("17px");
      expect(bubble.style.top).toBe("29px");

      fireEvent.pointerDown(bubble, { button: 0, pointerId: 8, clientX: 240, clientY: 480 });
      expect(bubble).toHaveAttribute("data-dragging", "true");
      fireEvent.pointerMove(bubble, { pointerId: 8, clientX: 260, clientY: 500 });
      expect(setItem).not.toHaveBeenCalled();
      fireEvent.pointerUp(bubble, { pointerId: 8, clientX: 260, clientY: 500 });
      expect(bubble).toHaveAttribute("data-dragging", "false");
      expect(window.localStorage.getItem("openportfo.chat-bubble-position.v1")).toBeTruthy();
      expect(setItem).toHaveBeenCalledTimes(1);

      fireEvent.click(bubble);
      fireEvent.click(bubble);
      const panel = await screen.findByRole("dialog");
      expect(screen.getByRole("button", { name: "Start a new chat" })).toHaveClass("min-w-11");
      expect(panel.style.left).toBe("25px");
      expect(panel.style.top).toBe("37px");
      expect(panel.style.width).toBe("304px");
      expect(panel.style.height).toBe("552px");

      visualViewport.width = 390;
      visualViewport.height = 844;
      fireEvent(window, new Event("resize"));
      expect(panel.style.width).toBe("374px");
      expect(panel.style.height).toBe("680px");

      visualViewport.width = 320;
      visualViewport.height = 300;
      fireEvent(window, new Event("resize"));
      expect(panel.style.height).toBe("284px");
    } finally {
      setItem.mockRestore();
      Object.defineProperty(window, "visualViewport", { configurable: true, value: originalVisualViewport });
    }
  });

  it("offers the configured Cognito CTA and otherwise points to the account menu", async () => {
    mocks.token = null;
    mocks.isCognitoConfigured.mockReturnValue(false);
    render(<ChatWidget />);
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    expect(await screen.findByText("Use your account settings to sign in.")).toBeInTheDocument();
    cleanup();

    mocks.isCognitoConfigured.mockReturnValue(true);
    render(<ChatWidget />);
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    const signIn = await screen.findByRole("button", { name: "Sign in with Cognito" });
    fireEvent.click(signIn);
    expect(mocks.beginHostedUiLogin).toHaveBeenCalledWith({ next: "/" });
  });

  it("does not retry the profile when focus sees the same token", async () => {
    await renderReady();
    const callsBeforeFocus = mocks.fetchAuthMe.mock.calls.length;
    fireEvent(window, new Event("focus"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(mocks.fetchAuthMe).toHaveBeenCalledTimes(callsBeforeFocus);
  });

  it("refreshes the profile only for the canonical auth storage event", async () => {
    await renderReady();
    const callsBefore = mocks.fetchAuthMe.mock.calls.length;
    mocks.token = "token-b";
    fireEvent(window, new StorageEvent("storage", { key: "openportfo.accessToken" }));
    await waitFor(() => expect(mocks.fetchAuthMe.mock.calls.length).toBeGreaterThan(callsBefore));
    const callsAfterCanonical = mocks.fetchAuthMe.mock.calls.length;
    mocks.token = "token-c";
    fireEvent(window, new StorageEvent("storage", { key: "openportfo.other" }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(mocks.fetchAuthMe).toHaveBeenCalledTimes(callsAfterCanonical);
  });

  it("shows New chat and clears the active private transcript", async () => {
    window.sessionStorage.setItem(chatSessionKey("alice"), JSON.stringify([
      { id: "old", role: "user", content: "old message", createdAt: 1 },
    ]));
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    expect(screen.getByText("old message")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start a new chat" }));
    expect(screen.queryByText("old message")).toBeNull();
    expect(window.sessionStorage.getItem(chatSessionKey("alice"))).toBeNull();
  });

  it("persists the CLI view choice and keeps the canonical transcript when switching views", async () => {
    window.sessionStorage.setItem(chatSessionKey("alice"), JSON.stringify([
      { id: "old", role: "user", content: "private message", createdAt: 1 },
    ]));
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    expect(screen.getByText("private message")).toBeInTheDocument();

    const modeButton = screen.getByRole("button", { name: /Standard view.*CLI view/ });
    fireEvent.click(modeButton);
    expect(await screen.findByTestId("chat-cli-view")).toBeInTheDocument();
    expect(screen.getByText("private message")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /CLI view.*Standard view/ })).toBeInTheDocument();
    expect(window.localStorage.getItem("openportfo.chat-view-mode.v1")).toBe("cli");

    fireEvent.click(screen.getByRole("button", { name: /CLI view.*Standard view/ }));
    expect(screen.queryByTestId("chat-cli-view")).toBeNull();
    expect(screen.getByText("private message")).toBeInTheDocument();
  });

  it("keeps a partial command draft and menu usable across renderer switches", async () => {
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    const standardInput = screen.getByRole("combobox", { name: "Message the personal assistant" });
    standardInput.focus();
    fireEvent.change(standardInput, { target: { value: "/quo" } });
    expect(screen.getByRole("listbox", { name: "Agent commands and tools" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Standard view.*CLI view/ }));
    const cliInput = await screen.findByRole("combobox", { name: "Prompt" });
    expect(cliInput).toHaveValue("/quo");
    expect(screen.getByRole("listbox", { name: "Agent commands and tools" })).toBeInTheDocument();
    expect(document.activeElement).toBe(cliInput);
    expect(cliInput).toHaveAttribute("aria-controls", "cli-chat-command-menu");

    fireEvent.click(screen.getByRole("button", { name: /CLI view.*Standard view/ }));
    const restoredInput = await screen.findByRole("combobox", { name: "Message the personal assistant" });
    expect(restoredInput).toHaveValue("/quo");
    expect(document.activeElement).toBe(restoredInput);
  });

  it("dispatches a CLI prompt through the existing authenticated stream flow", async () => {
    window.sessionStorage.setItem(chatSessionKey("alice"), JSON.stringify([
      { id: "old", role: "user", content: "prior question", createdAt: 1 },
    ]));
    mocks.sendChatMessage.mockImplementationOnce(async (options: { history?: unknown; message: string; onEvent?: (event: unknown) => void }) => {
      options.onEvent?.({ type: "status", status: "thinking", message: "provider details stay private" });
      options.onEvent?.({ type: "tool", activity: { name: "get_quote", label: "Checking a quote", status: "completed" } });
      options.onEvent?.({ type: "message", content: "AAPL is ready.", done: true, toolCalls: [] });
      options.onEvent?.({ type: "done", ok: true });
      return { content: "AAPL is ready.", toolCalls: [] };
    });

    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    fireEvent.click(screen.getByRole("button", { name: /Standard view.*CLI view/ }));
    const input = await screen.findByRole("combobox", { name: "Prompt" });
    fireEvent.change(input, { target: { value: "check AAPL" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => expect(mocks.sendChatMessage).toHaveBeenCalledTimes(1));
    const options = mocks.sendChatMessage.mock.calls[0][0] as { token: string; message: string; history: Array<{ role: string; content: string }>; signal: AbortSignal; clientRequestId: string };
    expect(options.token).toBe("token-a");
    expect(options.message).toBe("check AAPL");
    expect(options.history).toEqual([{ role: "user", content: "prior question" }]);
    expect(options.signal).toBeInstanceOf(AbortSignal);
    expect(options.clientRequestId).toMatch(/^request-/);
    expect(await screen.findByText("AAPL is ready.")).toBeInTheDocument();
    expect(screen.getByText("Checking a quote")).toBeInTheDocument();
    expect(screen.queryByText("provider details stay private")).toBeNull();
  });

  it("expands an allow-listed slash command into a real agent tool instruction", async () => {
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    const input = screen.getByLabelText("Message the personal assistant");
    fireEvent.change(input, { target: { value: "/quote AAPL" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => expect(mocks.sendChatMessage).toHaveBeenCalledTimes(1));
    const options = mocks.sendChatMessage.mock.calls[0][0] as { message: string };
    expect(options.message).toBe("Use the get_quote tool to handle this request. User input: AAPL");
    expect(screen.getByText("/quote AAPL")).toBeInTheDocument();
  });

  it("uses Escape to dismiss the command menu without closing the assistant", async () => {
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    const input = screen.getByLabelText("Message the personal assistant");
    fireEvent.change(input, { target: { value: "/" } });
    expect(screen.getByRole("listbox", { name: "Agent commands and tools" })).toBeInTheDocument();
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox", { name: "Agent commands and tools" })).toBeNull();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("enters full screen and uses Escape to restore the floating panel before closing", async () => {
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    const panel = await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: "Open assistant full screen" }));
    expect(panel).toHaveAttribute("data-fullscreen", "true");
    expect(panel.style.left).toBe("0px");
    expect(panel.style.top).toBe("0px");
    expect(panel.style.width).toBe("1024px");
    expect(panel.style.height).toBe("768px");

    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(panel).toHaveAttribute("data-fullscreen", "false"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open assistant full screen" })).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("keeps fullscreen renderer content left-aligned across Standard and CLI", async () => {
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    const panel = await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: "Open assistant full screen" }));

    const standardLog = screen.getByRole("log", { name: "Chat messages" });
    expect(standardLog).toHaveAttribute("data-fullscreen", "true");
    expect(standardLog.querySelector(".mx-auto")).toBeNull();
    expect(standardLog.querySelector(".text-center")).toBeNull();
    expect(standardLog.firstElementChild?.className).not.toContain("justify-center");
    expect(standardLog.querySelector('[aria-label="Suggested prompts"]')?.className).not.toContain("justify-center");
    const standardInput = screen.getByRole("combobox", { name: "Message the personal assistant" });
    fireEvent.change(standardInput, { target: { value: "/" } });
    const standardMenu = screen.getByRole("listbox", { name: "Agent commands and tools" });
    expect(standardMenu.className).not.toContain("justify-center");
    expect(standardMenu.className).not.toContain("mx-auto");

    fireEvent.click(screen.getByRole("button", { name: /Standard view.*CLI view/ }));
    const cliView = await screen.findByTestId("chat-cli-view");
    const cliLog = screen.getByRole("log", { name: "CLI chat messages" });
    expect(cliView).toHaveAttribute("data-fullscreen", "true");
    expect(cliLog.querySelector(".mx-auto")).toBeNull();
    expect(cliView.querySelector(".mx-auto")).toBeNull();
    const cliMenu = screen.getByRole("listbox", { name: "Agent commands and tools" });
    expect(cliMenu.className).not.toContain("justify-center");
    expect(cliMenu.className).not.toContain("mx-auto");
    expect(screen.getByRole("combobox", { name: "Prompt" }).closest("form")?.className).not.toContain("justify-center");
    expect(panel).toHaveAttribute("data-fullscreen", "true");
  });

  it("keeps fullscreen Standard user rows on the right edge and assistant rows on the left", async () => {
    window.sessionStorage.setItem(chatSessionKey("alice"), JSON.stringify([
      { id: "user-turn", role: "user", content: "Show my portfolio", createdAt: 1 },
      { id: "assistant-turn", role: "assistant", content: "Your portfolio is ready.", createdAt: 2 },
    ]));
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    expect(await screen.findByText("Show my portfolio")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open assistant full screen" }));

    const log = screen.getByRole("log", { name: "Chat messages" });
    const transcript = log.firstElementChild;
    expect(transcript).not.toHaveClass("mx-auto", "max-w-3xl");
    const userRow = log.querySelector('article[data-role="user"]');
    const assistantRow = log.querySelector('article[data-role="assistant"]');
    expect(userRow).toHaveClass("chat-message-row--user");
    expect(userRow).not.toHaveClass("chat-message-row--assistant");
    expect(assistantRow).toHaveClass("chat-message-row--assistant");
    expect(assistantRow).not.toHaveClass("chat-message-row--user");
  });

  it("uses the visual viewport for full screen and reopens at the floating size", async () => {
    const originalVisualViewport = window.visualViewport;
    const visualViewport = {
      width: 390,
      height: 844,
      offsetLeft: 17,
      offsetTop: 29,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    Object.defineProperty(window, "visualViewport", { configurable: true, value: visualViewport });
    try {
      await renderReady();
      const bubble = screen.getByRole("button", { name: "Open personal assistant" });
      fireEvent.click(bubble);
      const panel = await screen.findByRole("dialog");
      fireEvent.click(screen.getByRole("button", { name: "Open assistant full screen" }));
      expect(panel).toHaveAttribute("data-fullscreen", "true");
      expect(panel.style.left).toBe("17px");
      expect(panel.style.top).toBe("29px");
      expect(panel.style.width).toBe("390px");
      expect(panel.style.height).toBe("844px");
      expect(screen.queryByRole("button", { name: "Close personal assistant" })).toBeNull();

      fireEvent.click(screen.getByRole("button", { name: "Exit full screen assistant" }));
      expect(panel).toHaveAttribute("data-fullscreen", "false");
      expect(panel.style.left).toBe("25px");
      expect(panel.style.top).toBe("185px");
      expect(panel.style.width).toBe("374px");
      expect(panel.style.height).toBe("680px");

      fireEvent.click(screen.getByRole("button", { name: "Close assistant" }));
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
      await waitFor(() => expect(document.getElementById("personal-chat-panel")).toBeNull());
      fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
      const reopened = await screen.findByRole("dialog");
      expect(reopened).toHaveAttribute("data-fullscreen", "false");
      expect(reopened.style.width).toBe("374px");
    } finally {
      Object.defineProperty(window, "visualViewport", { configurable: true, value: originalVisualViewport });
    }
  });

  it("keeps full-screen geometry during the close animation", async () => {
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    const panel = await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: "Open assistant full screen" }));
    fireEvent.click(screen.getByRole("button", { name: "Close assistant" }));
    expect(panel).toHaveAttribute("data-state", "closing");
    expect(panel).toHaveAttribute("data-fullscreen", "true");
    expect(panel.style.width).toBe("1024px");
    expect(panel.style.height).toBe("768px");
    await waitFor(() => expect(document.getElementById("personal-chat-panel")).toBeNull());
  });

  it("clears the prior user's transcript when authentication is removed", async () => {
    window.sessionStorage.setItem(chatSessionKey("alice"), JSON.stringify([
      { id: "old", role: "user", content: "private message", createdAt: 1 },
    ]));
    await renderReady();
    expect(window.sessionStorage.getItem(chatSessionKey("alice"))).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    expect(await screen.findByText("private message")).toBeInTheDocument();
    mocks.token = null;
    fireEvent(window, new Event("openportfo:auth-change"));
    await waitFor(() => expect(window.sessionStorage.getItem(chatSessionKey("alice"))).toBeNull());
  });

  it("clears Alice before switching to Bob and does not restore Alice later", async () => {
    const alice = { id: "alice-old", role: "user" as const, content: "Alice private", createdAt: 1 };
    const bob = { id: "bob-old", role: "user" as const, content: "Bob private", createdAt: 2 };
    window.sessionStorage.setItem(chatSessionKey("alice"), JSON.stringify([alice]));
    window.sessionStorage.setItem(chatSessionKey("bob"), JSON.stringify([bob]));
    mocks.fetchAuthMe.mockImplementation(({ token }: { token: string }) => Promise.resolve(
      token === "token-a"
        ? { userId: "alice", email: "alice@example.com", name: "Alice" }
        : { userId: "bob", email: "bob@example.com", name: "Bob" },
    ));
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    expect(screen.getByText("Alice private")).toBeInTheDocument();

    mocks.token = "token-b";
    fireEvent(window, new Event("openportfo:auth-change"));
    await waitFor(() => expect(screen.getByText("Bob private")).toBeInTheDocument());
    expect(window.sessionStorage.getItem(chatSessionKey("alice"))).toBeNull();

    mocks.token = "token-a";
    fireEvent(window, new Event("openportfo:auth-change"));
    await waitFor(() => expect(screen.queryByText("Alice private")).toBeNull());
    expect(window.sessionStorage.getItem(chatSessionKey("alice"))).toBeNull();
  });

  it("distinguishes a profile network failure from a signed-out state", async () => {
    mocks.fetchAuthMe.mockReset().mockRejectedValueOnce(new Error("offline"));
    render(<ChatWidget />);
    await waitFor(() => expect(mocks.fetchAuthMe).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to verify your session");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("keeps completed tool activity visible when the provider fails afterward", async () => {
    mocks.sendChatMessage.mockImplementationOnce(async (options: { onEvent?: (event: unknown) => void }) => {
      options.onEvent?.({
        type: "tool",
        activity: { name: "add_holding", label: "Updating holdings", status: "completed" },
      });
      throw new ChatApiError(502, "provider failed", { ambiguous: true });
    });
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    fireEvent.change(screen.getByLabelText("Message the personal assistant"), { target: { value: "add BTC" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText("Updating holdings")).toBeInTheDocument();
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("may have completed");
    expect(alert).toHaveTextContent("Verify your holdings or watchlist before trying again.");
    expect(alert).toHaveTextContent("No automatic retry was made");
    expect(screen.getAllByRole("alert")).toHaveLength(1);
    expect(alert.textContent?.match(/Verify your holdings or watchlist before trying again\./g)).toHaveLength(1);
    expect(screen.queryByRole("note", { name: "Verify the completed change" })).toBeNull();
    expect(alert).toHaveClass("chat-ambiguous-alert");
  });

  it("renders a streaming thinking status once inside the pending assistant row", async () => {
    let resolveTurn: (() => void) | undefined;
    mocks.sendChatMessage.mockImplementationOnce(async (options: { onEvent?: (event: unknown) => void }) => {
      options.onEvent?.({ type: "status", status: "thinking", message: "provider internals must stay hidden" });
      await new Promise<void>((resolve) => { resolveTurn = resolve; });
      return { content: "done", toolCalls: [] };
    });
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    fireEvent.change(screen.getByLabelText("Message the personal assistant"), { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText("Thinking about your request")).toBeInTheDocument();
    expect(screen.getAllByText("Thinking about your request")).toHaveLength(1);
    resolveTurn?.();
  });

  it("keeps Escape close behavior while aborting an active CLI request", async () => {
    let resolveTurn: ((value: { content: string; toolCalls: [] }) => void) | undefined;
    mocks.sendChatMessage.mockImplementationOnce(() => new Promise((resolve) => {
      resolveTurn = resolve;
    }));
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    fireEvent.click(screen.getByRole("button", { name: /Standard view.*CLI view/ }));
    const input = await screen.findByRole("combobox", { name: "Prompt" });
    fireEvent.change(input, { target: { value: "check BTC" } });
    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() => expect(mocks.sendChatMessage).toHaveBeenCalledTimes(1));
    const signal = (mocks.sendChatMessage.mock.calls[0][0] as { signal: AbortSignal }).signal;
    expect(signal.aborted).toBe(false);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(signal.aborted).toBe(true);
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    resolveTurn?.({ content: "cancelled", toolCalls: [] });
  });

  it("preserves ambiguous mutation semantics when a CLI stream aborts", async () => {
    mocks.sendChatMessage.mockImplementationOnce((options: { signal?: AbortSignal; onEvent?: (event: unknown) => void }) => {
      options.onEvent?.({
        type: "tool",
        activity: { name: "add_holding", label: "Updating holdings", status: "completed" },
      });
      return new Promise((_, reject) => {
        options.signal?.addEventListener("abort", () => {
          reject(new ChatApiError(502, "stream interrupted", { ambiguous: true }));
        }, { once: true });
      });
    });
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    fireEvent.click(screen.getByRole("button", { name: /Standard view.*CLI view/ }));
    const input = await screen.findByRole("combobox", { name: "Prompt" });
    fireEvent.change(input, { target: { value: "add BTC" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(await screen.findByText("Updating holdings")).toBeInTheDocument();
    const signal = (mocks.sendChatMessage.mock.calls[0][0] as { signal: AbortSignal }).signal;

    fireEvent.keyDown(window, { key: "Escape" });
    expect(signal.aborted).toBe(true);
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText("A requested change may have completed.")).toBeInTheDocument();
    expect(screen.getByText("Updating holdings")).toBeInTheDocument();
    expect(screen.getAllByText(/Verify your holdings or watchlist before trying again\./)).toHaveLength(1);
  });

  it("keeps the standard view's Escape close behavior without aborting its request", async () => {
    let resolveTurn: ((value: { content: string; toolCalls: [] }) => void) | undefined;
    mocks.sendChatMessage.mockImplementationOnce(() => new Promise((resolve) => {
      resolveTurn = resolve;
    }));
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    const input = await screen.findByLabelText("Message the personal assistant");
    fireEvent.change(input, { target: { value: "hello" } });
    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() => expect(mocks.sendChatMessage).toHaveBeenCalledTimes(1));
    const signal = (mocks.sendChatMessage.mock.calls[0][0] as { signal: AbortSignal }).signal;
    fireEvent.keyDown(window, { key: "Escape" });
    expect(signal.aborted).toBe(false);
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    resolveTurn?.({ content: "done", toolCalls: [] });
  });

  it("honors reduced motion while still completing presence cleanup", async () => {
    const originalMatchMedia = window.matchMedia;
    const media = { matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() };
    Object.defineProperty(window, "matchMedia", { configurable: true, value: vi.fn(() => media) });
    try {
      await renderReady();
      fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
      const panel = await screen.findByRole("dialog");
      expect(panel).toHaveAttribute("data-reduced-motion", "true");
      fireEvent.keyDown(window, { key: "Escape" });
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    } finally {
      Object.defineProperty(window, "matchMedia", { configurable: true, value: originalMatchMedia });
    }
  });

  it("disables New chat while a write turn is active", async () => {
    let resolveTurn: ((value: { content: string; toolCalls: [] }) => void) | undefined;
    mocks.sendChatMessage.mockImplementationOnce(() => new Promise((resolve) => {
      resolveTurn = resolve;
    }));
    await renderReady();
    fireEvent.click(screen.getByRole("button", { name: "Open personal assistant" }));
    fireEvent.change(screen.getByLabelText("Message the personal assistant"), { target: { value: "add BTC" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    const newChat = await screen.findByRole("button", { name: "Start a new chat" });
    await waitFor(() => expect(newChat).toBeDisabled());
    fireEvent.click(newChat);
    expect(screen.getByText("add BTC")).toBeInTheDocument();
    resolveTurn?.({ content: "done", toolCalls: [] });
    await waitFor(() => expect(newChat).not.toBeDisabled());
  });
});
