import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  token: "token-a" as string | null,
  profile: { userId: "alice", email: "alice@example.com", name: "Alice" },
  fetchAuthMe: vi.fn(),
  readAuthToken: vi.fn(),
  clearAuthToken: vi.fn(),
  sendChatMessage: vi.fn(),
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

import ChatWidget from "@/components/chat/ChatWidget";
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
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(bubble));
  });

  it("does not retry the profile when focus sees the same token", async () => {
    await renderReady();
    const callsBeforeFocus = mocks.fetchAuthMe.mock.calls.length;
    fireEvent(window, new Event("focus"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(mocks.fetchAuthMe).toHaveBeenCalledTimes(callsBeforeFocus);
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

  it("clears the prior user's transcript when authentication is removed", async () => {
    window.sessionStorage.setItem(chatSessionKey("alice"), JSON.stringify([
      { id: "old", role: "user", content: "private message", createdAt: 1 },
    ]));
    await renderReady();
    expect(window.sessionStorage.getItem(chatSessionKey("alice"))).toBeTruthy();
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
    expect(screen.getByRole("alert")).toHaveTextContent("may have completed");
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
