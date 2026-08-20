"use client";

import { FormEvent, PointerEvent as ReactPointerEvent, useCallback, useEffect, useRef, useState } from "react";
import { LoaderCircle, MessageCircle, Plus, Send, X } from "lucide-react";
import {
  AUTH_CHANGE_EVENT,
  AuthApiError,
  clearAuthToken,
  fetchAuthMe,
  readAuthToken,
  type AuthProfile,
} from "@/lib/auth";
import {
  ChatApiError,
  sendChatMessage,
  type ChatStreamEvent,
  type ChatToolActivity,
} from "@/lib/chat";
import {
  clearChatSession,
  loadChatSession,
  saveChatSession,
  type ChatSessionMessage,
} from "@/lib/chat-session";
import SafeMarkdown from "@/components/chat/SafeMarkdown";

type UiMessage = ChatSessionMessage & { activities?: ChatToolActivity[]; streaming?: boolean };
type Position = { x: number; y: number };
type Viewport = { width: number; height: number };

const POSITION_KEY = "openportfo.chat-bubble-position.v1";
const BUBBLE_SIZE = 56;
const VIEWPORT_MARGIN = 12;
const DRAG_THRESHOLD = 6;

function makeId(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return `${prefix}-${crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function clampPosition(position: Position, viewport: Viewport): Position {
  const marginX = viewport.width < BUBBLE_SIZE + VIEWPORT_MARGIN * 2 ? 0 : VIEWPORT_MARGIN;
  const marginY = viewport.height < BUBBLE_SIZE + VIEWPORT_MARGIN * 2 ? 0 : VIEWPORT_MARGIN;
  const maxX = Math.max(marginX, viewport.width - BUBBLE_SIZE - marginX);
  const maxY = Math.max(marginY, viewport.height - BUBBLE_SIZE - marginY);
  return {
    x: Math.min(maxX, Math.max(marginX, Math.round(position.x))),
    y: Math.min(maxY, Math.max(marginY, Math.round(position.y))),
  };
}

function defaultPosition(viewport: Viewport): Position {
  return clampPosition(
    { x: viewport.width - BUBBLE_SIZE - 24, y: viewport.height - BUBBLE_SIZE - 30 },
    viewport,
  );
}

function readBubblePosition(viewport: Viewport): Position | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(POSITION_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<Position>;
    if (!Number.isFinite(value.x) || !Number.isFinite(value.y)) return null;
    return clampPosition({ x: Number(value.x), y: Number(value.y) }, viewport);
  } catch {
    return null;
  }
}

function persistBubblePosition(position: Position): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(POSITION_KEY, JSON.stringify(position));
  } catch {
    // Private mode/quota errors do not affect dragging.
  }
}

function persistedMessages(messages: UiMessage[]): ChatSessionMessage[] {
  return messages.map(({ id, role, content, createdAt }) => ({ id, role, content, createdAt }));
}

function displayError(error: unknown): string {
  if (error instanceof ChatApiError) {
    if (error.authRequired) return "Your session expired. Sign in again to continue.";
    if (error.ambiguous) return "A requested change may have completed. Verify it before retrying; no automatic retry was made.";
    if (error.status === 429) return "The assistant is busy. Please try again shortly.";
    return error.message || "The assistant could not complete that request.";
  }
  return "The assistant could not complete that request.";
}

export default function ChatWidget() {
  const [viewport, setViewport] = useState<Viewport>({ width: 0, height: 0 });
  const [position, setPosition] = useState<Position>({ x: 20, y: 20 });
  const [positionReady, setPositionReady] = useState(false);
  const [open, setOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileRetry, setProfileRetry] = useState(0);
  const [sessionUserId, setSessionUserId] = useState<string | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [statusText, setStatusText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const authGeneration = useRef(0);
  const activeSessionUser = useRef<string | null>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    origin: Position;
    moved: boolean;
  } | null>(null);
  const suppressClick = useRef(false);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const bubbleRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const updateViewport = () => {
      const next = { width: window.innerWidth, height: window.innerHeight };
      setViewport(next);
      setPosition((current) => clampPosition(current, next));
    };
    updateViewport();
    const stored = readBubblePosition({ width: window.innerWidth, height: window.innerHeight });
    setPosition(stored || defaultPosition({ width: window.innerWidth, height: window.innerHeight }));
    setPositionReady(true);
    window.addEventListener("resize", updateViewport);
    return () => window.removeEventListener("resize", updateViewport);
  }, []);

  useEffect(() => {
    if (positionReady && viewport.width > 0) persistBubblePosition(clampPosition(position, viewport));
  }, [position, positionReady, viewport]);

  const syncToken = useCallback(() => {
    const nextToken = readAuthToken();
    // Focus/storage notifications are synchronization signals, not retries.
    // Keeping the same token stable prevents an in-flight profile request from
    // being restarted every time the window regains focus.
    setToken((current) => current === nextToken ? current : nextToken);
  }, []);

  const retryProfile = useCallback(() => {
    setProfileError(null);
    setProfileRetry((current) => current + 1);
  }, []);

  useEffect(() => {
    syncToken();
    const onStorage = (event: StorageEvent) => {
      if (event.key === "artryx.accessToken") syncToken();
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener(AUTH_CHANGE_EVENT, syncToken);
    window.addEventListener("focus", syncToken);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener(AUTH_CHANGE_EVENT, syncToken);
      window.removeEventListener("focus", syncToken);
    };
  }, [syncToken]);

  useEffect(() => {
    const generation = ++authGeneration.current;
    abortRef.current?.abort();
    setSending(false);
    setPendingId(null);
    setStatusText(null);
    setError(null);
    setProfileError(null);
    setSessionReady(false);
    setSessionUserId(null);
    setMessages([]);
    if (!token) {
      if (activeSessionUser.current) clearChatSession(activeSessionUser.current);
      activeSessionUser.current = null;
      setProfile(null);
      setAuthLoading(false);
      return;
    }
    setProfile(null);
    setAuthLoading(true);
    const controller = new AbortController();
    void fetchAuthMe({ token, signal: controller.signal })
      .then((nextProfile) => {
        if (controller.signal.aborted || generation !== authGeneration.current) return;
        if (activeSessionUser.current && activeSessionUser.current !== nextProfile.userId) {
          // A successful identity change must not leave the previous user's
          // private transcript available for a later return to that account.
          clearChatSession(activeSessionUser.current);
        }
        setProfile(nextProfile);
        activeSessionUser.current = nextProfile.userId;
        setSessionUserId(nextProfile.userId);
        setMessages(loadChatSession(nextProfile.userId));
        setSessionReady(true);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted || generation !== authGeneration.current) return;
        if (cause instanceof AuthApiError && cause.authRequired) {
          if (activeSessionUser.current) clearChatSession(activeSessionUser.current);
          activeSessionUser.current = null;
          clearAuthToken();
          setToken(null);
          setProfileError(null);
        } else {
          setProfileError("Unable to verify your session. Check your connection and retry.");
        }
        setProfile(null);
        setSessionReady(false);
      })
      .finally(() => {
        if (!controller.signal.aborted && generation === authGeneration.current) setAuthLoading(false);
      });
    return () => controller.abort();
  }, [profileRetry, token]);

  useEffect(() => {
    if (sessionReady && sessionUserId) saveChatSession(sessionUserId, persistedMessages(messages));
  }, [messages, sessionReady, sessionUserId]);

  const restoreBubbleFocus = useCallback(() => {
    const restore = () => bubbleRef.current?.focus();
    if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
      window.requestAnimationFrame(restore);
    } else {
      restore();
    }
  }, []);

  const closePanel = useCallback(() => {
    setOpen(false);
    restoreBubbleFocus();
  }, [restoreBubbleFocus]);

  useEffect(() => {
    if (!open) return;
    panelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closePanel();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [closePanel, open]);

  const updatePending = useCallback((id: string, update: (message: UiMessage) => UiMessage) => {
    setMessages((current) => current.map((message) => message.id === id ? update(message) : message));
  }, []);

  const handleStreamEvent = useCallback((id: string, event: ChatStreamEvent) => {
    if (event.type === "status") {
      setStatusText(event.message);
    } else if (event.type === "tool") {
      updatePending(id, (message) => {
        const activities = [...(message.activities || [])];
        const previousIndex = activities.findIndex((item) => item.name === event.activity.name);
        if (previousIndex >= 0) activities[previousIndex] = event.activity;
        else activities.push(event.activity);
        return { ...message, activities };
      });
    } else if (event.type === "message") {
      updatePending(id, (message) => ({
        ...message,
        content: event.content,
        streaming: !event.done,
        ...(event.toolCalls ? { activities: event.toolCalls } : {}),
      }));
    } else if (event.type === "done") {
      setStatusText(null);
    }
  }, [updatePending]);

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;
    if (!token || !profile || !sessionUserId) {
      setError("Sign in to use your personal assistant.");
      setOpen(true);
      return;
    }
    const requestUserId = sessionUserId;
    const generation = authGeneration.current;
    const assistantId = makeId("assistant");
    const userMessage: UiMessage = { id: makeId("user"), role: "user", content: text.slice(0, 8_000), createdAt: Date.now() };
    const assistantMessage: UiMessage = { id: assistantId, role: "assistant", content: "", createdAt: Date.now(), streaming: true };
    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((current) => [...current, userMessage, assistantMessage]);
    setDraft("");
    setError(null);
    setStatusText("Starting chat");
    setSending(true);
    setPendingId(assistantId);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await sendChatMessage({
        token,
        message: text,
        history,
        signal: controller.signal,
        clientRequestId: makeId("request"),
        onEvent: (nextEvent) => {
          if (generation === authGeneration.current && requestUserId === sessionUserId) handleStreamEvent(assistantId, nextEvent);
        },
      });
      if (generation === authGeneration.current && requestUserId === sessionUserId) {
        updatePending(assistantId, (message) => ({ ...message, streaming: false }));
      }
    } catch (cause: unknown) {
      if (controller.signal.aborted) return;
      if (generation === authGeneration.current && requestUserId === sessionUserId) {
        if (cause instanceof ChatApiError && cause.authRequired) {
          if (activeSessionUser.current) clearChatSession(activeSessionUser.current);
          activeSessionUser.current = null;
          clearAuthToken();
          setToken(null);
        }
        setError(displayError(cause));
        // Keep the assistant activity timeline on failure. A completed write
        // must remain visible when the provider fails after the tool ran; the
        // user can verify state and choose a new request explicitly.
        updatePending(assistantId, (message) => ({
          ...message,
          content: displayError(cause),
          streaming: false,
        }));
      }
    } finally {
      if (generation === authGeneration.current && requestUserId === sessionUserId) {
        setSending(false);
        setPendingId(null);
        setStatusText(null);
      }
      if (abortRef.current === controller) abortRef.current = null;
    }
  };

  const onBubblePointerDown = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0) return;
    if (typeof event.currentTarget.setPointerCapture === "function") {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origin: position,
      moved: false,
    };
  };

  const onBubblePointerMove = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    drag.moved = true;
    setPosition(clampPosition({ x: drag.origin.x + dx, y: drag.origin.y + dy }, viewport));
  };

  const onBubblePointerUp = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (drag.moved) suppressClick.current = true;
    dragRef.current = null;
  };

  const onBubblePointerCancel = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (dragRef.current?.pointerId === event.pointerId) dragRef.current = null;
    suppressClick.current = false;
  };

  const startNewChat = () => {
    if (sending) return;
    abortRef.current?.abort();
    setMessages([]);
    if (sessionUserId) clearChatSession(sessionUserId);
    setDraft("");
    setError(null);
    setStatusText(null);
    setSending(false);
    setPendingId(null);
  };

  const panelWidth = viewport.width ? Math.max(1, Math.min(420, viewport.width - 24)) : 360;
  const panelHeight = viewport.height ? Math.max(1, Math.min(680, viewport.height - 96)) : 560;
  const layoutMarginX = viewport.width < 48 ? 1 : VIEWPORT_MARGIN;
  const layoutMarginY = viewport.height < 48 ? 1 : VIEWPORT_MARGIN;
  const panelMaxLeft = Math.max(layoutMarginX, viewport.width - panelWidth - layoutMarginX);
  const panelMaxTop = Math.max(layoutMarginY, viewport.height - panelHeight - layoutMarginY);
  const panelLeft = viewport.width ? Math.min(Math.max(layoutMarginX, position.x < viewport.width / 2 ? position.x : position.x + BUBBLE_SIZE - panelWidth), panelMaxLeft) : 12;
  const panelTop = viewport.height ? Math.min(Math.max(layoutMarginY, position.y < viewport.height / 2 ? position.y + BUBBLE_SIZE + 12 : position.y - panelHeight - 12), panelMaxTop) : 12;
  const pending = pendingId ? messages.find((message) => message.id === pendingId) : null;

  return (
    <>
      {open ? (
        <section
          ref={panelRef}
          tabIndex={-1}
          role="dialog"
          aria-modal="false"
          aria-labelledby="personal-chat-title"
          className="fixed z-[70] flex flex-col overflow-hidden rounded-2xl border border-gray-700 bg-gray-800 shadow-2xl shadow-black/50 outline-none"
          style={{ left: panelLeft, top: panelTop, width: panelWidth, height: panelHeight }}
        >
          <header className="flex items-center justify-between border-b border-gray-700 px-4 py-3">
            <div>
              <h2 id="personal-chat-title" className="font-semibold text-gray-100">Personal assistant</h2>
              <p className="text-xs text-gray-500">Private portfolio help with safe activity updates</p>
            </div>
            <div className="flex items-center gap-1">
              <button type="button" onClick={startNewChat} disabled={sending} aria-label="Start a new chat" className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-gray-400 hover:bg-gray-700 hover:text-gray-100 disabled:cursor-not-allowed disabled:opacity-40">
                <Plus className="size-3.5" /> New chat
              </button>
              <button type="button" onClick={closePanel} aria-label="Close assistant" className="rounded-md p-1.5 text-gray-400 hover:bg-gray-700 hover:text-gray-100">
                <X className="size-4" />
              </button>
            </div>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3" aria-live="polite">
            {profileError ? (
              <div className="rounded-xl border border-amber-900/80 bg-amber-950/30 p-4 text-sm text-amber-200" role="alert">
                <p>{profileError}</p>
                <button type="button" onClick={retryProfile} className="mt-3 rounded-md border border-amber-700 px-2.5 py-1.5 text-xs hover:bg-amber-900/40">Retry</button>
              </div>
            ) : !token || !profile ? (
              <div className="rounded-xl border border-gray-700 bg-gray-900/60 p-4 text-sm text-gray-400">
                {authLoading ? "Checking your sign-in…" : "Sign in to start a personal chat. Your conversation stays scoped to your account in this browser."}
              </div>
            ) : messages.length === 0 ? (
              <div className="rounded-xl border border-gray-700 bg-gray-900/60 p-4 text-sm text-gray-400">
                Ask about a quote, your portfolio, holdings, watchlist, or recent market news.
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((message) => (
                  <div key={message.id} className={message.role === "user" ? "ml-7 rounded-2xl rounded-br-sm bg-teal-950/70 px-3 py-2 text-sm text-teal-50" : "mr-3 rounded-2xl rounded-bl-sm border border-gray-700 bg-gray-900/70 px-3 py-2 text-sm text-gray-300"}>
                    {message.role === "assistant" ? <SafeMarkdown content={message.content || (message.streaming ? "" : "No response.")} /> : <p className="whitespace-pre-wrap break-words">{message.content}</p>}
                    {message.activities?.length ? (
                      <div className="mt-2 flex flex-wrap gap-1.5 border-t border-gray-700/70 pt-2" aria-label="Assistant activity">
                        {message.activities.map((activity, index) => (
                          <span key={`${activity.name}-${index}`} className="inline-flex items-center gap-1 rounded-full bg-gray-800 px-2 py-1 text-[11px] text-gray-400">
                            {activity.status === "started" ? <LoaderCircle className="size-3 animate-spin" /> : <span aria-hidden>{activity.status === "failed" ? "!" : "✓"}</span>}
                            {activity.label}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
            {statusText && pending ? <p className="mt-2 text-xs text-gray-500" role="status">{statusText}</p> : null}
            {error ? <p className="mt-3 rounded-lg border border-red-900/80 bg-red-950/30 px-3 py-2 text-xs text-red-300" role="alert">{error}</p> : null}
          </div>
          <form onSubmit={submit} className="border-t border-gray-700 p-3">
            <label htmlFor="personal-chat-input" className="sr-only">Message the personal assistant</label>
            <div className="flex items-end gap-2 rounded-xl border border-gray-600 bg-gray-900 px-2 py-2 focus-within:border-teal-500">
              <textarea
                id="personal-chat-input"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void submit();
                  }
                }}
                rows={2}
                maxLength={8_000}
                disabled={sending || !profile}
                placeholder={profile ? "Ask your assistant…" : "Sign in to chat"}
                className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-1 py-1 text-sm text-gray-100 outline-none placeholder:text-gray-600 disabled:cursor-not-allowed"
              />
              <button type="submit" disabled={sending || !draft.trim() || !profile} aria-label="Send message" className="rounded-lg bg-teal-500 p-2 text-teal-950 transition hover:bg-teal-400 disabled:cursor-not-allowed disabled:opacity-40">
                {sending ? <LoaderCircle className="size-4 animate-spin" /> : <Send className="size-4" />}
              </button>
            </div>
            <p className="mt-1 px-1 text-[10px] text-gray-600">Enter to send · Shift+Enter for a new line</p>
          </form>
        </section>
      ) : null}
      <button
        ref={bubbleRef}
        type="button"
        aria-label={open ? "Close personal assistant" : "Open personal assistant"}
        aria-expanded={open}
        onClick={() => {
          if (suppressClick.current) {
            suppressClick.current = false;
            return;
          }
          if (open) closePanel();
          else setOpen(true);
        }}
        onPointerDown={onBubblePointerDown}
        onPointerMove={onBubblePointerMove}
        onPointerUp={onBubblePointerUp}
        onPointerCancel={onBubblePointerCancel}
        className="fixed z-[71] flex size-14 touch-none items-center justify-center rounded-full border border-teal-300/40 bg-teal-500 text-teal-950 shadow-lg shadow-teal-950/50 transition hover:scale-105 hover:bg-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-300 focus:ring-offset-2 focus:ring-offset-gray-900"
        style={{ left: position.x, top: position.y, visibility: positionReady ? "visible" : "hidden" }}
      >
        {open ? <X className="size-6" /> : <MessageCircle className="size-6" />}
      </button>
    </>
  );
}
