"use client";

import { MessageCircle, X } from "lucide-react";

type ChatLauncherProps = {
  open: boolean;
  ready: boolean;
  reducedMotion: boolean;
  hidden?: boolean;
  viewportOffset: { x: number; y: number };
  dragging: boolean;
  position: { x: number; y: number };
  onClick: () => void;
  onPointerDown: (event: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerMove: (event: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerUp: (event: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerCancel: (event: React.PointerEvent<HTMLButtonElement>) => void;
  buttonRef: React.RefObject<HTMLButtonElement | null>;
};

export default function ChatLauncher({ open, ready, reducedMotion, hidden = false, viewportOffset, dragging, position, onClick, onPointerDown, onPointerMove, onPointerUp, onPointerCancel, buttonRef }: ChatLauncherProps) {
  return (
    <button
      ref={buttonRef}
      type="button"
      aria-label={open ? "Close personal assistant" : "Open personal assistant"}
      aria-expanded={open}
      aria-controls="personal-chat-panel"
      aria-hidden={hidden ? "true" : undefined}
      tabIndex={hidden ? -1 : undefined}
      inert={hidden}
      onClick={onClick}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
      className="chat-launcher fixed left-0 top-0 z-[71] inline-flex size-14 touch-none items-center justify-center rounded-full border border-teal-200/50 bg-teal-400 text-teal-950 shadow-xl shadow-teal-950/45 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:ring-offset-2 focus:ring-offset-gray-900"
      data-open={open ? "true" : "false"}
      data-reduced-motion={reducedMotion ? "true" : "false"}
      data-dragging={dragging ? "true" : "false"}
      style={{
        left: viewportOffset.x,
        top: viewportOffset.y,
        transform: `translate3d(${position.x}px, ${position.y}px, 0)`,
        visibility: ready && !hidden ? "visible" : "hidden",
        pointerEvents: hidden ? "none" : undefined,
      }}
    >
      <span className="sr-only">{open ? "Close personal assistant" : "Open personal assistant"}</span>
      {open ? <X className="size-6" aria-hidden="true" /> : <MessageCircle className="size-6" aria-hidden="true" />}
    </button>
  );
}
