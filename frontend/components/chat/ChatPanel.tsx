"use client";

import { RefObject, useState } from "react";
import { LoaderCircle, Maximize2, Minimize2, Plus, RotateCcw, ShieldCheck, X } from "lucide-react";
import type { AuthProfile } from "@/lib/auth";
import { beginHostedUiLogin, isCognitoConfigured } from "@/lib/cognito";
import ChatComposer from "@/components/chat/ChatComposer";
import ChatRenderer from "@/components/chat/ChatRenderer";
import type { ChatUiMessage } from "@/components/chat/ChatMessageRow";
import type { ChatViewMode } from "@/lib/chat-view";

type ChatPanelProps = {
  mounted: boolean;
  phase: "opening" | "open" | "closing";
  mobile: boolean;
  reducedMotion: boolean;
  panelRef: RefObject<HTMLDivElement | null>;
  style: React.CSSProperties;
  profile: AuthProfile | null;
  token: string | null;
  authLoading: boolean;
  profileError: string | null;
  messages: ChatUiMessage[];
  draft: string;
  statusText: string | null;
  error: string | null;
  sending: boolean;
  pending: boolean;
  pendingId: string | null;
  viewMode: ChatViewMode;
  fullscreen: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onRetry: () => void;
  onDraftChange: (value: string) => void;
  onSubmit: () => void | Promise<void>;
  onSuggestion: (value: string) => void;
  onMessageEntered: (id: string) => void;
  onComposerReady: (focus: () => void) => void;
  onViewModeChange: (mode: ChatViewMode) => void;
  onFullscreenChange: (fullscreen: boolean) => void;
};

function StateCard({ children, title, tone = "neutral", action }: { children: React.ReactNode; title?: string; tone?: "neutral" | "warning" | "error"; action?: React.ReactNode }) {
  const toneClass = tone === "warning"
    ? "border-amber-400/20 bg-amber-400/[0.06] text-amber-100"
    : tone === "error"
      ? "border-red-400/20 bg-red-400/[0.06] text-red-400 dark:text-red-100"
      : "border-gray-700 bg-gray-900/45 text-gray-400";
  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      {title ? <h3 className="text-sm font-semibold text-gray-100">{title}</h3> : null}
      <div className={title ? "mt-1.5 text-sm leading-6" : "text-sm leading-6"}>{children}</div>
      {action}
    </div>
  );
}

export default function ChatPanel({ mounted, phase, mobile, reducedMotion, panelRef, style, profile, token, authLoading, profileError, messages, draft, statusText, error, sending, pending, pendingId, viewMode, fullscreen, onClose, onNewChat, onRetry, onDraftChange, onSubmit, onSuggestion, onMessageEntered, onComposerReady, onViewModeChange, onFullscreenChange }: ChatPanelProps) {
  const [loginError, setLoginError] = useState<string | null>(null);
  if (!mounted) return null;
  const signedIn = Boolean(token && profile);
  const cognitoConfigured = isCognitoConfigured();
  const active = phase !== "closing";
  const handleSignIn = () => {
    if (!cognitoConfigured) return;
    setLoginError(null);
    void beginHostedUiLogin({ next: typeof window !== "undefined" ? window.location.pathname : "/" })
      .catch((cause: unknown) => setLoginError(cause instanceof Error ? cause.message : "Unable to start sign-in."));
  };
  const nextViewMode = viewMode === "standard" ? "cli" : "standard";
  const currentViewLabel = viewMode === "standard" ? "Standard" : "CLI";
  const nextViewLabel = nextViewMode === "standard" ? "Standard" : "CLI";
  return (
    <section
      id="personal-chat-panel"
      ref={panelRef}
      tabIndex={active ? -1 : undefined}
      role={active ? "dialog" : undefined}
      aria-hidden={active ? undefined : "true"}
      aria-modal="false"
      inert={!active}
      aria-labelledby="personal-chat-title"
      aria-describedby="personal-chat-description"
      data-state={phase}
      data-mobile={mobile ? "true" : "false"}
      data-reduced-motion={reducedMotion ? "true" : "false"}
      data-motion={phase === "open" ? "visible" : "hidden"}
      data-fullscreen={fullscreen ? "true" : "false"}
      className={`chat-panel chat-panel--${phase} fixed z-[50] flex flex-col overflow-hidden border border-gray-600/90 bg-gray-800/95 outline-none backdrop-blur-xl ${fullscreen ? "chat-panel--fullscreen rounded-none" : mobile ? "chat-panel--mobile rounded-2xl" : "rounded-2xl"}`}
      style={style}
    >
      <header
        data-layout={mobile ? "stacked" : "inline"}
        className={`flex shrink-0 border-b border-gray-700/80 bg-gray-800/90 px-4 py-3.5 ${mobile ? "flex-col gap-2" : "items-start justify-between"}`}
      >
        <div className={`min-w-0 ${mobile ? "w-full pr-0" : "pr-3"}`}>
          <div className="flex items-center gap-2">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-teal-400/10 text-teal-400" aria-hidden="true">
              <ShieldCheck className="size-4" />
            </span>
            <h2 id="personal-chat-title" className="min-w-0 flex-1 truncate text-sm font-semibold text-gray-100">Personal assistant</h2>
          </div>
          <p id="personal-chat-description" className="mt-1 pl-9 text-[11px] leading-4 text-gray-500">Private portfolio help with safe activity updates</p>
        </div>
        <div
          data-testid="chat-panel-actions"
          data-layout={mobile ? "wrapped" : "inline"}
          className={`flex shrink-0 items-center ${mobile ? "w-full flex-wrap justify-end gap-0" : "gap-1"}`}
        >
          <button
            type="button"
            aria-label={`${currentViewLabel} view; switch to ${nextViewLabel} view`}
            title={`Current view: ${currentViewLabel}. Switch to ${nextViewLabel} view.`}
            onClick={() => onViewModeChange(nextViewMode)}
            className={`segment-item min-h-9 min-w-9 ${mobile ? "mr-0 px-1" : "mr-1 px-2 sm:px-2.5"}`}
          >
            <span className="sm:hidden">{viewMode === "standard" ? "Std" : "CLI"}</span>
            <span className="hidden sm:inline">{currentViewLabel}</span>
          </button>
          <button
            type="button"
            onClick={() => onFullscreenChange(!fullscreen)}
            aria-label={fullscreen ? "Exit full screen assistant" : "Open assistant full screen"}
            title={fullscreen ? "Exit full screen" : "Full screen"}
            className="inline-flex size-11 items-center justify-center rounded-xl text-gray-400 transition-colors hover:bg-gray-700 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-400/70"
          >
            {fullscreen ? <Minimize2 className="size-4" aria-hidden="true" /> : <Maximize2 className="size-4" aria-hidden="true" />}
          </button>
          <button
            type="button"
            onClick={onNewChat}
            disabled={sending}
            aria-label="Start a new chat"
            className="inline-flex min-h-11 min-w-11 items-center gap-1.5 rounded-xl px-2.5 text-xs text-gray-400 transition-colors hover:bg-gray-700 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-400/70 disabled:cursor-not-allowed disabled:opacity-35"
          >
            <Plus className="size-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">New chat</span>
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close assistant"
            className="inline-flex size-11 items-center justify-center rounded-xl text-gray-400 transition-colors hover:bg-gray-700 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-400/70"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      </header>

      {profileError ? (
        <div className="min-h-0 flex-1 overflow-y-auto p-4" role="region" aria-label="Session error">
          <StateCard
            title="We couldn't verify your session"
            tone="warning"
            action={(
              <button type="button" onClick={onRetry} className="mt-3 inline-flex min-h-11 items-center gap-1.5 rounded-xl border border-amber-300/30 px-3 text-xs font-medium text-amber-100 transition-colors hover:bg-amber-400/10 focus:outline-none focus:ring-2 focus:ring-amber-300/70">
                <RotateCcw className="size-3.5 motion-reduce:animate-none" aria-hidden="true" /> Retry
              </button>
            )}
          >
            <p role="alert">{profileError}</p>
            <p className="mt-2 text-xs text-amber-200/70">Your conversation remains private. Try again when your connection is back.</p>
          </StateCard>
        </div>
      ) : authLoading ? (
        <div className="flex min-h-0 flex-1 items-center justify-center p-6" role="status" aria-label="Checking your sign-in">
          <div className="flex items-center gap-2 text-sm text-gray-500"><LoaderCircle className="size-4 animate-spin text-teal-400" aria-hidden="true" /> Checking your sign-in…</div>
        </div>
      ) : !signedIn ? (
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <StateCard title="Sign in to start a personal chat">
            <p>Your conversation stays scoped to your account in this browser.</p>
            <p className="mt-2 text-xs text-gray-500">Once signed in, I can help you explore portfolio data, quotes, holdings, and market news.</p>
            {cognitoConfigured ? (
              <button type="button" onClick={handleSignIn} className="mt-4 inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-400 px-4 text-xs font-semibold text-teal-950 transition-colors hover:bg-teal-300 focus:outline-none focus:ring-2 focus:ring-teal-200/80">Sign in with Cognito</button>
            ) : (
              <p className="mt-4 rounded-xl border border-gray-700 bg-gray-800/70 px-3 py-2.5 text-xs text-gray-400">Use your account settings to sign in.</p>
            )}
            {loginError ? <p className="mt-3 text-xs text-red-400 dark:text-red-200" role="alert">{loginError}</p> : null}
          </StateCard>
        </div>
      ) : (
        <ChatRenderer
          mode={viewMode}
          messages={messages}
          draft={draft}
          statusText={statusText}
          error={error}
          sending={sending}
          pending={pending}
          pendingId={pendingId}
          reducedMotion={reducedMotion}
          fullscreen={fullscreen}
          signedIn={signedIn}
          onDraftChange={onDraftChange}
          onSubmit={onSubmit}
          onSuggestion={onSuggestion}
          onMessageEntered={onMessageEntered}
          onComposerReady={onComposerReady}
        />
      )}

      {!signedIn || profileError || authLoading ? (
        <ChatComposer
          value={draft}
          onChange={onDraftChange}
          onSubmit={onSubmit}
          disabled={Boolean(profileError || authLoading)}
          signedIn={signedIn}
          sending={sending}
          fullscreen={fullscreen}
          onReady={onComposerReady}
        />
      ) : null}
    </section>
  );
}

export { StateCard };
