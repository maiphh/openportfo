"use client";

import {
  FormEvent,
  PointerEvent as ReactPointerEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import {
  AUTH_CHANGE_EVENT,
  AuthApiError,
  clearAuthToken,
  fetchAuthMe,
  isAuthTokenStorageKey,
  readAuthToken,
  type AuthProfile,
} from "@/lib/auth";
import {
  ChatApiError,
  sendChatMessage,
  type ChatStreamEvent,
} from "@/lib/chat";
import {
  clearChatSession,
  loadChatSession,
  saveChatSession,
} from "@/lib/chat-session";
import ChatLauncher from "@/components/chat/ChatLauncher";
import ChatPanel from "@/components/chat/ChatPanel";
import type { ChatUiMessage } from "@/components/chat/ChatMessageRow";

export type Position = { x: number; y: number };
export type Viewport = { width: number; height: number; offsetLeft: number; offsetTop: number };

export const POSITION_KEY = "openportfo.chat-bubble-position.v1";
export const BUBBLE_SIZE = 56;
export const VIEWPORT_MARGIN = 12;
export const DRAG_THRESHOLD = 6;

const MOBILE_BREAKPOINT = 640;
const PANEL_GAP = 12;
const PANEL_MARGIN = 12;
const PANEL_MOBILE_MARGIN = 8;
const PANEL_DESKTOP_WIDTH = 420;
const PANEL_MAX_HEIGHT = 680;
const PANEL_CLOSE_MS = 220;

type PanelPhase = "closed" | "opening" | "open" | "closing";

const PUBLIC_STATUS_MESSAGES: Readonly<Record<string, string>> = {
  thinking: "Thinking about your request",
  answering: "Writing a response",
};

function makeId(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return `${prefix}-${crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function clampPosition(
  position: Position,
  viewport: Pick<Viewport, "width" | "height">,
  leftInset = 0,
): Position {
  const marginX = viewport.width < BUBBLE_SIZE + VIEWPORT_MARGIN * 2 ? 0 : VIEWPORT_MARGIN;
  const marginY = viewport.height < BUBBLE_SIZE + VIEWPORT_MARGIN * 2 ? 0 : VIEWPORT_MARGIN;
  const minX = Math.max(marginX, Math.round(leftInset));
  const maxX = Math.max(minX, viewport.width - BUBBLE_SIZE - marginX);
  const maxY = Math.max(marginY, viewport.height - BUBBLE_SIZE - marginY);
  return {
    x: Math.min(maxX, Math.max(minX, Math.round(position.x))),
    y: Math.min(maxY, Math.max(marginY, Math.round(position.y))),
  };
}

export function defaultPosition(viewport: Pick<Viewport, "width" | "height">): Position {
  return clampPosition(
    { x: viewport.width - BUBBLE_SIZE - 24, y: viewport.height - BUBBLE_SIZE - 30 },
    viewport,
  );
}

function readBubblePosition(viewport: Pick<Viewport, "width" | "height">, leftInset = 0): Position | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(POSITION_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<Position>;
    if (!Number.isFinite(value.x) || !Number.isFinite(value.y)) return null;
    return clampPosition({ x: Number(value.x), y: Number(value.y) }, viewport, leftInset);
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

function persistedMessages(messages: ChatUiMessage[]) {
  return messages.map(({ id, role, content, createdAt }) => ({ id, role, content, createdAt }));
}

export function publicStatus(event: ChatStreamEvent): string | null {
  if (event.type !== "status") return null;
  // The API intentionally has a tiny public status vocabulary. Do not render
  // event.message directly: it could contain provider/internal metadata.
  return PUBLIC_STATUS_MESSAGES[event.status] || "Working on your request";
}

export function displayError(error: unknown): string {
  if (error instanceof ChatApiError) {
    if (error.authRequired) return "Your session expired. Sign in again to continue.";
    if (error.ambiguous) return "A requested change may have completed.";
    if (error.status === 429) return "The assistant is busy. Please try again shortly.";
    return error.message || "The assistant could not complete that request.";
  }
  return "The assistant could not complete that request.";
}

function readViewport(): Viewport {
  if (typeof window === "undefined") return { width: 0, height: 0, offsetLeft: 0, offsetTop: 0 };
  const visual = window.visualViewport;
  return {
    width: Math.round(visual?.width || window.innerWidth),
    height: Math.round(visual?.height || window.innerHeight),
    offsetLeft: Math.round(visual?.offsetLeft || 0),
    offsetTop: Math.round(visual?.offsetTop || 0),
  };
}

function scheduleFrame(callback: FrameRequestCallback): number {
  if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
    return window.requestAnimationFrame(callback);
  }
  return typeof window !== "undefined" ? window.setTimeout(() => callback(Date.now()), 0) : 0;
}

function cancelFrame(frame: number): void {
  if (!frame || typeof window === "undefined") return;
  if (typeof window.cancelAnimationFrame === "function") window.cancelAnimationFrame(frame);
  else window.clearTimeout(frame);
}

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!media) return;
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, []);
  return reduced;
}

export default function ChatWidget({ leftInset = 0 }: { leftInset?: number } = {}) {
  const [viewport, setViewport] = useState<Viewport>({ width: 0, height: 0, offsetLeft: 0, offsetTop: 0 });
  const [position, setPosition] = useState<Position>({ x: 20, y: 20 });
  const positionRef = useRef<Position>({ x: 20, y: 20 });
  const [positionReady, setPositionReady] = useState(false);
  const [open, setOpen] = useState(false);
  const [panelMounted, setPanelMounted] = useState(false);
  const [panelPhase, setPanelPhase] = useState<PanelPhase>("closed");
  const [launcherHidden, setLauncherHidden] = useState(false);
  const [dragging, setDragging] = useState(false);
  const panelCloseTimer = useRef<number | null>(null);
  const panelOpenFrame = useRef<number | null>(null);
  const reducedMotion = useReducedMotion();
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileRetry, setProfileRetry] = useState(0);
  const [sessionUserId, setSessionUserId] = useState<string | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
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
    lastX: number;
    lastY: number;
    moved: boolean;
    frame: number | null;
  } | null>(null);
  const suppressClick = useRef(false);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const bubbleRef = useRef<HTMLButtonElement | null>(null);
  const composerFocusRef = useRef<(() => void) | null>(null);
  const isMobile = viewport.width > 0 && viewport.width < MOBILE_BREAKPOINT;

  useEffect(() => {
    const updateViewport = () => {
      const next = readViewport();
      setViewport(next);
      const clamped = clampPosition(positionRef.current, next, leftInset);
      positionRef.current = clamped;
      setPosition(clamped);
    };
    const initial = readViewport();
    const stored = readBubblePosition(initial, leftInset);
    const initialPosition = stored || clampPosition(defaultPosition(initial), initial, leftInset);
    positionRef.current = initialPosition;
    setViewport(initial);
    setPosition(initialPosition);
    setPositionReady(true);
    window.addEventListener("resize", updateViewport);
    window.visualViewport?.addEventListener("resize", updateViewport);
    window.visualViewport?.addEventListener("scroll", updateViewport);
    return () => {
      window.removeEventListener("resize", updateViewport);
      window.visualViewport?.removeEventListener("resize", updateViewport);
      window.visualViewport?.removeEventListener("scroll", updateViewport);
    };
  }, [leftInset]);

  useEffect(() => {
    if (!viewport.width) return;
    const clamped = clampPosition(positionRef.current, viewport, leftInset);
    positionRef.current = clamped;
    setPosition(clamped);
  }, [leftInset, viewport]);

  const syncToken = useCallback(() => {
    const nextToken = readAuthToken();
    // Focus/storage notifications are synchronization signals, not retries.
    setToken((current) => current === nextToken ? current : nextToken);
  }, []);

  const retryProfile = useCallback(() => {
    setProfileError(null);
    setProfileRetry((current) => current + 1);
  }, []);

  useEffect(() => {
    syncToken();
    const onStorage = (event: StorageEvent) => {
      if (isAuthTokenStorageKey(event.key)) syncToken();
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
        if (activeSessionUser.current && activeSessionUser.current !== nextProfile.userId) clearChatSession(activeSessionUser.current);
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
    if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") window.requestAnimationFrame(restore);
    else restore();
  }, []);

  const closePanel = useCallback(() => {
    if (panelOpenFrame.current !== null) {
      cancelFrame(panelOpenFrame.current);
      panelOpenFrame.current = null;
    }
    setOpen(false);
    setPanelPhase("closing");
    // Compact mode removes the launcher from the tab order. Restore it before
    // scheduling focus so keyboard users never lose their focus target.
    setLauncherHidden(false);
    restoreBubbleFocus();
    if (panelCloseTimer.current !== null) window.clearTimeout(panelCloseTimer.current);
    panelCloseTimer.current = window.setTimeout(() => {
      setPanelMounted(false);
      setPanelPhase("closed");
      panelCloseTimer.current = null;
    }, reducedMotion ? 0 : PANEL_CLOSE_MS);
  }, [reducedMotion, restoreBubbleFocus]);

  const openPanel = useCallback(() => {
    if (panelCloseTimer.current !== null) {
      window.clearTimeout(panelCloseTimer.current);
      panelCloseTimer.current = null;
    }
    setPanelMounted(true);
    setOpen(true);
    setPanelPhase("opening");
    setLauncherHidden(isMobile);
    panelOpenFrame.current = scheduleFrame(() => {
      panelOpenFrame.current = null;
      setPanelPhase("open");
    });
  }, [isMobile]);

  useEffect(() => {
    if (!open) return;
    const frame = scheduleFrame(() => {
      if (token && profile && !authLoading && !profileError) composerFocusRef.current?.();
      else panelRef.current?.focus();
    });
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closePanel();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      cancelFrame(frame);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [authLoading, closePanel, open, profile, profileError, token]);

  useEffect(() => {
    setLauncherHidden(open && isMobile);
  }, [isMobile, open]);

  useEffect(() => () => {
    abortRef.current?.abort();
    if (panelCloseTimer.current !== null) window.clearTimeout(panelCloseTimer.current);
    if (panelOpenFrame.current !== null) cancelFrame(panelOpenFrame.current);
  }, []);

  const updatePending = useCallback((id: string, update: (message: ChatUiMessage) => ChatUiMessage) => {
    setMessages((current) => current.map((message) => message.id === id ? update(message) : message));
  }, []);

  const handleStreamEvent = useCallback((id: string, event: ChatStreamEvent) => {
    if (event.type === "status") {
      setStatusText(publicStatus(event));
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
      openPanel();
      return;
    }
    const requestUserId = sessionUserId;
    const generation = authGeneration.current;
    const assistantId = makeId("assistant");
    const userMessage: ChatUiMessage = { id: makeId("user"), role: "user", content: text.slice(0, 8_000), createdAt: Date.now(), isNew: true };
    const assistantMessage: ChatUiMessage = { id: assistantId, role: "assistant", content: "", createdAt: Date.now(), streaming: true, isNew: true };
    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((current) => [...current, userMessage, assistantMessage]);
    setDraft("");
    setError(null);
    setStatusText("Thinking about your request");
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
      if (generation === authGeneration.current && requestUserId === sessionUserId) updatePending(assistantId, (message) => ({ ...message, streaming: false }));
    } catch (cause: unknown) {
      if (controller.signal.aborted) return;
      if (generation === authGeneration.current && requestUserId === sessionUserId) {
        if (cause instanceof ChatApiError && cause.authRequired) {
          if (activeSessionUser.current) clearChatSession(activeSessionUser.current);
          activeSessionUser.current = null;
          clearAuthToken();
          setToken(null);
        }
        // Render a turn failure exactly once in its assistant row so the
        // activity timeline remains attached to the attempted turn.
        setError(null);
        updatePending(assistantId, (message) => ({
          ...message,
          content: displayError(cause),
          streaming: false,
          failure: { ...(cause instanceof ChatApiError && cause.ambiguous ? { ambiguous: true } : {}) },
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

  const onBubblePointerDown = useCallback((event: ReactPointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0) return;
    setDragging(true);
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture is unavailable in some test/webview environments.
    }
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origin: positionRef.current,
      lastX: event.clientX,
      lastY: event.clientY,
      moved: false,
      frame: null,
    };
  }, []);

  const onBubblePointerMove = useCallback((event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    drag.moved = true;
    drag.lastX = event.clientX;
    drag.lastY = event.clientY;
    if (drag.frame !== null) return;
    drag.frame = scheduleFrame(() => {
      const active = dragRef.current;
      if (!active) return;
      active.frame = null;
      const next = clampPosition({ x: active.origin.x + active.lastX - active.startX, y: active.origin.y + active.lastY - active.startY }, viewport, leftInset);
      positionRef.current = next;
      setPosition(next);
    });
  }, [leftInset, viewport]);

  const finishDrag = useCallback((event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (drag.frame !== null) {
      cancelFrame(drag.frame);
      drag.frame = null;
    }
    if (drag.moved) {
      const finalPosition = clampPosition({ x: drag.origin.x + event.clientX - drag.startX, y: drag.origin.y + event.clientY - drag.startY }, viewport, leftInset);
      positionRef.current = finalPosition;
      setPosition(finalPosition);
      persistBubblePosition(finalPosition);
      suppressClick.current = true;
    }
    dragRef.current = null;
    setDragging(false);
  }, [leftInset, viewport]);

  const onBubblePointerCancel = useCallback((event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (drag.frame !== null) cancelFrame(drag.frame);
    positionRef.current = drag.origin;
    setPosition(drag.origin);
    dragRef.current = null;
    suppressClick.current = false;
    setDragging(false);
  }, []);

  const startNewChat = useCallback(() => {
    if (sending) return;
    abortRef.current?.abort();
    setMessages([]);
    if (sessionUserId) clearChatSession(sessionUserId);
    setDraft("");
    setError(null);
    setStatusText(null);
    setSending(false);
    setPendingId(null);
  }, [sending, sessionUserId]);

  const registerComposer = useCallback((focus: () => void) => {
    composerFocusRef.current = focus;
  }, []);

  const markMessageEntered = useCallback((id: string) => {
    setMessages((current) => {
      const message = current.find((item) => item.id === id);
      if (!message?.isNew) return current;
      return current.map((item) => item.id === id ? { ...item, isNew: false } : item);
    });
  }, []);

  const chooseSuggestion = useCallback((value: string) => {
    setDraft(value);
    scheduleFrame(() => document.getElementById("personal-chat-input")?.focus());
  }, []);

  const availableWidth = viewport.width - (isMobile ? 0 : leftInset);
  const panelWidth = viewport.width
    ? Math.max(1, isMobile ? viewport.width - PANEL_MOBILE_MARGIN * 2 : Math.min(PANEL_DESKTOP_WIDTH, availableWidth - PANEL_MARGIN * 2))
    : 360;
  const panelHeight = viewport.height
    ? Math.max(1, isMobile ? Math.min(PANEL_MAX_HEIGHT, viewport.height - PANEL_MOBILE_MARGIN * 2) : Math.min(PANEL_MAX_HEIGHT, viewport.height - 96))
    : 560;
  const layoutMarginX = viewport.width < 48 ? 1 : PANEL_MARGIN;
  const layoutMarginY = viewport.height < 48 ? 1 : PANEL_MARGIN;
  const viewportMinLeft = viewport.offsetLeft + (isMobile ? 0 : leftInset) + layoutMarginX;
  const viewportMinTop = viewport.offsetTop + layoutMarginY;
  const panelMaxLeft = Math.max(viewportMinLeft, viewport.offsetLeft + viewport.width - panelWidth - layoutMarginX);
  const panelMaxTop = Math.max(viewportMinTop, viewport.offsetTop + viewport.height - panelHeight - layoutMarginY);
  const desktopPanelLeft = viewport.width
    ? Math.min(Math.max(viewportMinLeft, viewport.offsetLeft + (position.x < viewport.width / 2 ? position.x : position.x + BUBBLE_SIZE - panelWidth)), panelMaxLeft)
    : 12;
  const desktopPanelTop = viewport.height
    ? Math.min(Math.max(viewportMinTop, viewport.offsetTop + (position.y < viewport.height / 2 ? position.y + BUBBLE_SIZE + PANEL_GAP : position.y - panelHeight - PANEL_GAP)), panelMaxTop)
    : 12;
  const panelStyle: CSSProperties = isMobile
    ? {
        left: viewport.offsetLeft + PANEL_MOBILE_MARGIN,
        top: viewport.offsetTop + Math.max(PANEL_MOBILE_MARGIN, viewport.height - panelHeight - PANEL_MOBILE_MARGIN),
        width: panelWidth,
        height: panelHeight,
      }
    : { left: desktopPanelLeft, top: desktopPanelTop, width: panelWidth, height: panelHeight };
  const pending = pendingId ? messages.find((message) => message.id === pendingId) : null;

  return (
    <>
      <ChatPanel
        mounted={panelMounted}
        phase={panelPhase === "closed" ? "closing" : panelPhase}
        mobile={isMobile}
        reducedMotion={reducedMotion}
        panelRef={panelRef}
        style={panelStyle}
        profile={profile}
        token={token}
        authLoading={authLoading}
        profileError={profileError}
        messages={messages}
        draft={draft}
        statusText={statusText}
        error={error}
        sending={sending}
        pending={Boolean(pending)}
        pendingId={pendingId}
        onClose={closePanel}
        onNewChat={startNewChat}
        onRetry={retryProfile}
        onDraftChange={setDraft}
        onSubmit={submit}
        onSuggestion={chooseSuggestion}
        onMessageEntered={markMessageEntered}
        onComposerReady={registerComposer}
      />
      <ChatLauncher
        open={open}
        ready={positionReady}
        reducedMotion={reducedMotion}
        hidden={launcherHidden}
        viewportOffset={{ x: viewport.offsetLeft, y: viewport.offsetTop }}
        dragging={dragging}
        position={position}
        buttonRef={bubbleRef}
        onClick={() => {
          if (suppressClick.current) {
            suppressClick.current = false;
            return;
          }
          if (open) closePanel();
          else openPanel();
        }}
        onPointerDown={onBubblePointerDown}
        onPointerMove={onBubblePointerMove}
        onPointerUp={finishDrag}
        onPointerCancel={onBubblePointerCancel}
      />
    </>
  );
}
