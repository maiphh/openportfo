import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AppShell from "@/components/AppShell";
import Providers from "@/components/Providers";

const pathname = vi.fn(() => "/portfolio");
vi.mock("next/navigation", () => ({ usePathname: () => pathname() }));
vi.mock("next/link", () => ({
  default({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
    return <a href={href} {...props}>{children}</a>;
  },
}));
vi.mock("@/components/chat/ChatWidget", () => ({ default: ({ leftInset }: { leftInset?: number }) => <div data-testid="chat-widget" data-left-inset={leftInset} /> }));

type MockMediaQueryList = Omit<MediaQueryList, "matches" | "addEventListener"> & {
  matches: boolean;
  addEventListener: ReturnType<typeof vi.fn>;
};

function matchMedia(matches = false): MockMediaQueryList {
  return {
    matches,
    media: "(min-width: 640px)",
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  } as unknown as MockMediaQueryList;
}

let activeMedia = matchMedia(true);

function renderShell() {
  return render(<Providers><AppShell><p>content</p></AppShell></Providers>);
}

describe("AppShell", () => {
  beforeEach(() => {
    pathname.mockReturnValue("/portfolio");
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
    document.body.style.overflow = "";
    activeMedia = matchMedia(true);
    Object.defineProperty(window, "matchMedia", { configurable: true, value: () => activeMedia });
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.localStorage.clear();
    document.body.style.overflow = "";
  });

  it("hydrates a persisted collapsed sidebar and computes the rail chat inset", async () => {
    window.localStorage.setItem("openportfo.sidebar.collapsed", "1");
    renderShell();
    await waitFor(() => expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument());
    expect(screen.getByTestId("chat-widget")).toHaveAttribute("data-left-inset", "64");
  });

  it("uses the expanded 240px chat inset by default and 0px on mobile", async () => {
    renderShell();
    await waitFor(() => expect(screen.getByTestId("chat-widget")).toHaveAttribute("data-left-inset", "240"));

    cleanup();
    activeMedia = matchMedia(false);
    Object.defineProperty(window, "matchMedia", { configurable: true, value: () => activeMedia });
    renderShell();
    await waitFor(() => expect(screen.getByTestId("chat-widget")).toHaveAttribute("data-left-inset", "0"));
  });

  it("persists collapse changes only through the toggle handler", async () => {
    renderShell();
    const toggle = await screen.findByRole("button", { name: "Collapse sidebar" });
    fireEvent.click(toggle);
    expect(window.localStorage.getItem("openportfo.sidebar.collapsed")).toBe("1");
    fireEvent.click(await screen.findByRole("button", { name: "Expand sidebar" }));
    expect(window.localStorage.getItem("openportfo.sidebar.collapsed")).toBe("0");
  });

  it("opens search from Cmd/Ctrl+K and closes shell overlays mutually", async () => {
    renderShell();
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(await screen.findByRole("dialog", { name: "Search" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Search" })).not.toBeInTheDocument();
  });

  it("opens settings from the avatar control", async () => {
    renderShell();
    fireEvent.click((await screen.findAllByRole("button", { name: "Settings" }))[0]!);
    expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument();
  });

  it("keeps focus and body lock through Settings to Search, then returns to the avatar", async () => {
    renderShell();
    const avatar = (await screen.findAllByRole("button", { name: "Settings" }))[0]!;
    avatar.focus();
    fireEvent.click(avatar);
    const settings = await screen.findByRole("dialog", { name: "Settings" });
    const settingsControl = within(settings).getByRole("button", { name: "Close" });
    settingsControl.focus();
    expect(document.activeElement).toBe(settingsControl);
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const search = await screen.findByRole("dialog", { name: "Search" });
    expect(screen.queryByRole("dialog", { name: "Settings" })).not.toBeInTheDocument();
    expect(within(search).getAllByRole("textbox")[0]).toHaveFocus();
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Search" })).not.toBeInTheDocument());
    expect(document.activeElement).toBe(avatar);
    expect(document.body.style.overflow).toBe("");
  });

  it("suppresses Search restoration when Settings replaces it", async () => {
    renderShell();
    const avatar = (await screen.findAllByRole("button", { name: "Settings" }))[0]!;
    avatar.focus();
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const search = await screen.findByRole("dialog", { name: "Search" });
    expect(within(search).getAllByRole("textbox")[0]).toHaveFocus();

    // Exercise the symmetric successor path directly; in a real browser the
    // underlying trigger is reached by the owning shell transition.
    fireEvent.click(avatar);
    const settings = await screen.findByRole("dialog", { name: "Settings" });
    expect(screen.queryByRole("dialog", { name: "Search" })).not.toBeInTheDocument();
    expect(within(settings).getByRole("button", { name: "Close" })).toHaveFocus();
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.click(within(settings).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Settings" })).not.toBeInTheDocument());
    expect(document.activeElement).toBe(avatar);
    expect(document.body.style.overflow).toBe("");
  });

  it("does not steal initial focus and returns focus after a standalone drawer close", async () => {
    const sentinel = document.createElement("button");
    sentinel.textContent = "Sentinel";
    document.body.appendChild(sentinel);
    sentinel.focus();
    renderShell();
    await waitFor(() => expect(document.activeElement).toBe(sentinel));

    const menu = await screen.findByRole("button", { name: "Open navigation menu" });
    fireEvent.click(menu);
    const drawer = await screen.findByRole("dialog", { name: "Navigation menu" });
    within(drawer).getByRole("button", { name: "Close navigation" }).focus();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Navigation menu" })).not.toBeInTheDocument());
    expect(document.activeElement).toBe(menu);
    sentinel.remove();
  });

  it("keeps successor overlay focus when drawer opens Search or Settings", async () => {
    renderShell();
    const menu = await screen.findByRole("button", { name: "Open navigation menu" });
    fireEvent.click(menu);
    const drawer = await screen.findByRole("dialog", { name: "Navigation menu" });
    fireEvent.click(within(drawer).getByRole("button", { name: "Search" }));
    const search = await screen.findByRole("dialog", { name: "Search" });
    expect(document.activeElement).toBe(within(search).getAllByRole("textbox")[0]);
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Search" })).not.toBeInTheDocument());
    expect(document.activeElement).toBe(menu);

    fireEvent.click(menu);
    const secondDrawer = await screen.findByRole("dialog", { name: "Navigation menu" });
    fireEvent.click(within(secondDrawer).getByRole("button", { name: "Settings" }));
    const settings = await screen.findByRole("dialog", { name: "Settings" });
    expect(document.activeElement).toBe(within(settings).getByRole("button", { name: "Close" }));
    fireEvent.click(within(settings).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Settings" })).not.toBeInTheDocument());
    expect(document.activeElement).toBe(menu);
  });

  it("closes the drawer from links, backdrop, path changes, and sm+ media changes", async () => {
    const view = renderShell();
    const menu = await screen.findByRole("button", { name: "Open navigation menu" });
    fireEvent.click(menu);
    const drawer = await screen.findByRole("dialog", { name: "Navigation menu" });
    fireEvent.click(within(drawer).getByRole("link", { name: "Stock" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Navigation menu" })).not.toBeInTheDocument());

    fireEvent.click(menu);
    await screen.findByRole("dialog", { name: "Navigation menu" });
    fireEvent.click(screen.getAllByRole("button", { name: "Close navigation" })[0]!);
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Navigation menu" })).not.toBeInTheDocument());

    fireEvent.click(menu);
    await screen.findByRole("dialog", { name: "Navigation menu" });
    pathname.mockReturnValue("/watchlist");
    view.rerender(<Providers><AppShell><p>content</p></AppShell></Providers>);
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Navigation menu" })).not.toBeInTheDocument());

    fireEvent.click(menu);
    await screen.findByRole("dialog", { name: "Navigation menu" });
    activeMedia.matches = true;
    activeMedia.addEventListener.mock.calls.forEach((call: unknown[]) => {
      const handler = call[1];
      if (typeof handler === "function") (handler as () => void)();
    });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Navigation menu" })).not.toBeInTheDocument());
  });

  it("restores exact body overflow on final close and unmount cleanup", async () => {
    document.body.style.overflow = "clip";
    const { unmount } = renderShell();
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    await screen.findByRole("dialog", { name: "Search" });
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(document.body.style.overflow).toBe("clip"));

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    await screen.findByRole("dialog", { name: "Search" });
    unmount();
    expect(document.body.style.overflow).toBe("clip");
    document.body.style.overflow = "";
  });

  it("exposes the mobile hamburger contract and drawer close behavior", async () => {
    Object.defineProperty(window, "matchMedia", { configurable: true, value: () => matchMedia(false) });
    renderShell();
    const menu = await screen.findByRole("button", { name: "Open navigation menu" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(menu).toHaveAttribute("aria-controls", "mobile-sidebar-drawer");
    fireEvent.click(menu);
    expect(screen.getByRole("dialog", { name: "Navigation menu" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Navigation menu" })).not.toBeInTheDocument());
  });
});
