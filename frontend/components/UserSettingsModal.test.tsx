import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RefObject } from "react";
import UserSettingsModal from "@/components/UserSettingsModal";
import { CurrencyProvider } from "@/components/currency/CurrencyProvider";
import { LanguageProvider } from "@/components/LanguageProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import type { AuthProfileController } from "@/lib/use-auth-profile";

vi.mock("next/navigation", () => ({ usePathname: () => "/portfolio" }));

const auth: AuthProfileController = {
  hydrated: true,
  token: null,
  profile: null,
  loading: false,
  error: null,
  cognitoConfigured: false,
  refresh: vi.fn(),
  signIn: vi.fn(async () => undefined),
  signOut: vi.fn(),
};

function modalTree(open: boolean, onClose: () => void, returnFocusRef?: RefObject<HTMLElement | null>) {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <CurrencyProvider>
          <UserSettingsModal open={open} auth={auth} onClose={onClose} returnFocusRef={returnFocusRef} />
        </CurrencyProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}

function renderModal(open = true, onClose = vi.fn(), returnFocusRef?: RefObject<HTMLElement | null>) {
  return render(modalTree(open, onClose, returnFocusRef));
}

describe("UserSettingsModal", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ base: "USD", rates: {}, status: "missing" }) })));
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("renders account, appearance, language, and currency sections", () => {
    renderModal();
    expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
    expect(screen.getByRole("radiogroup", { name: "Appearance" })).toBeInTheDocument();
    expect(screen.getByRole("radiogroup", { name: "Language" })).toBeInTheDocument();
    expect(screen.getByRole("radiogroup", { name: "Display currency" })).toBeInTheDocument();
  });

  it("applies theme, language, and currency immediately", () => {
    renderModal();
    fireEvent.click(screen.getByRole("radio", { name: "Light" }));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(window.localStorage.getItem("openportfo.theme")).toBe("light");
    fireEvent.click(screen.getByRole("radio", { name: "Tiếng Việt" }));
    expect(document.documentElement.lang).toBe("vi");
    expect(window.localStorage.getItem("openportfo.language")).toBe("vi");
    fireEvent.click(screen.getByRole("radio", { name: "USD" }));
    expect(window.localStorage.getItem("openportfo.displayCurrency")).toBe("USD");
  });

  it("closes on Escape and backdrop click", () => {
    const onClose = vi.fn();
    renderModal(true, onClose);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("dialog").parentElement!);
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("handles Escape from the focused close control exactly once and restores its opener", () => {
    const opener = document.createElement("button");
    opener.textContent = "Open settings";
    document.body.appendChild(opener);
    opener.focus();
    const onClose = vi.fn();
    const returnFocusRef = { current: opener } as RefObject<HTMLElement | null>;
    const view = renderModal(false, onClose, returnFocusRef);
    view.rerender(modalTree(true, onClose, returnFocusRef));
    const close = screen.getByRole("button", { name: "Close" });
    fireEvent.keyDown(close, { key: "Escape", bubbles: true });
    expect(onClose).toHaveBeenCalledTimes(1);

    view.rerender(modalTree(false, onClose, returnFocusRef));
    expect(document.activeElement).toBe(opener);
    opener.remove();
  });

  it("opens the real FX rates dialog without closing settings", () => {
    renderModal();
    fireEvent.click(screen.getByRole("button", { name: /View FX rates/i }));
    expect(screen.getByRole("dialog", { name: /Exchange rates/i })).toBeInTheDocument();
    expect(document.getElementById("user-settings-title")?.closest('[role="dialog"]')).toHaveAttribute("aria-hidden", "true");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: /Exchange rates/i })).not.toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument();
  });

  it("makes settings inert and traps FX focus across two Escape presses", () => {
    const onClose = vi.fn();
    renderModal(true, onClose);
    const settings = screen.getByRole("dialog", { name: "Settings" });
    fireEvent.click(screen.getByRole("button", { name: /View FX rates/i }));
    const fx = screen.getByRole("dialog", { name: /Exchange rates/i });
    expect(settings).toHaveAttribute("inert");
    expect(settings).toHaveAttribute("aria-hidden", "true");
    const focusTargets = Array.from(fx.querySelectorAll<HTMLElement>('button:not([disabled]), [tabindex="0"]'));
    const first = focusTargets[0]!;
    const last = focusTargets[focusTargets.length - 1]!;
    first.focus();
    expect(document.activeElement).toBe(first);
    last.focus();
    fireEvent.keyDown(last, { key: "Tab", bubbles: true });
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(first, { key: "Tab", shiftKey: true, bubbles: true });
    expect(document.activeElement).toBe(last);

    fireEvent.keyDown(last, { key: "Escape", bubbles: true });
    expect(screen.queryByRole("dialog", { name: /Exchange rates/i })).not.toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
