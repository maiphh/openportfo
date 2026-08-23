"use client";

import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import SearchDialog from "@/components/SearchDialog";
import UserSettingsModal from "@/components/UserSettingsModal";
import ChatWidget from "@/components/chat/ChatWidget";
import Sidebar from "@/components/sidebar/Sidebar";
import SidebarNav from "@/components/sidebar/SidebarNav";
import SidebarUserChip from "@/components/sidebar/SidebarUserChip";
import MobileTopbar from "@/components/sidebar/MobileTopbar";
import { SIDEBAR_COLLAPSED_STORAGE_KEY } from "@/components/sidebar/Sidebar";
import { useAuthProfile } from "@/lib/use-auth-profile";

function focusableElements(root: HTMLElement | null): HTMLElement[] {
  if (!root) return [];
  return Array.from(
    root.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const auth = useAuthProfile();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [desktop, setDesktop] = useState(false);
  const drawerCloseRef = useRef<HTMLButtonElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const drawerWasOpenRef = useRef(false);
  const focusMenuAfterDrawerCloseRef = useRef(false);
  const searchReturnFocusRef = useRef<HTMLElement | null>(null);
  const settingsReturnFocusRef = useRef<HTMLElement | null>(null);
  const [restoreSearchFocus, setRestoreSearchFocus] = useState(true);
  const [restoreSettingsFocus, setRestoreSettingsFocus] = useState(true);
  const previousPathRef = useRef(pathname);
  const previousOverflowRef = useRef<string | null>(null);

  useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === "1");
    } catch {
      // Default expanded state remains safe when storage is unavailable.
    }
  }, []);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, next ? "1" : "0");
      } catch {
        // State remains useful for this session even when persistence fails.
      }
      return next;
    });
  }, []);

  const closeDrawer = useCallback(() => {
    focusMenuAfterDrawerCloseRef.current = true;
    setDrawerOpen(false);
  }, []);

  const captureOverlayOpener = useCallback((target: { current: HTMLElement | null }) => {
    const active = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    target.current = active && drawerRef.current?.contains(active) ? menuButtonRef.current : active;
  }, []);

  const openSearch = useCallback(() => {
    if (searchOpen) return;
    if (settingsOpen) {
      // Search replaces Settings. Keep the original avatar opener, not the
      // Settings control that is about to be disconnected.
      searchReturnFocusRef.current = settingsReturnFocusRef.current ?? menuButtonRef.current;
      setRestoreSettingsFocus(false);
    } else {
      captureOverlayOpener(searchReturnFocusRef);
    }
    setRestoreSearchFocus(true);
    focusMenuAfterDrawerCloseRef.current = false;
    setDrawerOpen(false);
    setSettingsOpen(false);
    setSearchOpen(true);
  }, [captureOverlayOpener, searchOpen, settingsOpen]);

  const openSettings = useCallback(() => {
    if (settingsOpen) return;
    if (searchOpen) {
      // Symmetric successor path: Settings inherits Search's original opener.
      settingsReturnFocusRef.current = searchReturnFocusRef.current ?? menuButtonRef.current;
      setRestoreSearchFocus(false);
    } else {
      captureOverlayOpener(settingsReturnFocusRef);
    }
    setRestoreSettingsFocus(true);
    focusMenuAfterDrawerCloseRef.current = false;
    setDrawerOpen(false);
    setSearchOpen(false);
    setSettingsOpen(true);
  }, [captureOverlayOpener, searchOpen, settingsOpen]);

  const closeSearch = useCallback(() => {
    setRestoreSearchFocus(true);
    setSearchOpen(false);
  }, []);

  const closeSettings = useCallback(() => {
    setRestoreSettingsFocus(true);
    setSettingsOpen(false);
  }, []);

  const toggleDrawer = useCallback(() => {
    if (searchOpen) setRestoreSearchFocus(false);
    if (settingsOpen) setRestoreSettingsFocus(false);
    setSearchOpen(false);
    setSettingsOpen(false);
    setDrawerOpen((value) => {
      focusMenuAfterDrawerCloseRef.current = value;
      return !value;
    });
  }, [searchOpen, settingsOpen]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openSearch();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openSearch]);

  useEffect(() => {
    if (previousPathRef.current === pathname) return;
    previousPathRef.current = pathname;
    focusMenuAfterDrawerCloseRef.current = false;
    setDrawerOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") {
      setDesktop(window.innerWidth >= 640);
      return;
    }
    const query = window.matchMedia("(min-width: 640px)");
    const update = () => {
      const nextDesktop = query.matches;
      setDesktop(nextDesktop);
      if (nextDesktop) {
        focusMenuAfterDrawerCloseRef.current = false;
        setDrawerOpen(false);
      }
    };
    update();
    query.addEventListener?.("change", update);
    return () => query.removeEventListener?.("change", update);
  }, []);

  const overlayOpen = drawerOpen || searchOpen || settingsOpen;
  useEffect(() => {
    if (overlayOpen) {
      if (previousOverflowRef.current === null) previousOverflowRef.current = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        if (previousOverflowRef.current !== null) {
          document.body.style.overflow = previousOverflowRef.current;
          previousOverflowRef.current = null;
        }
      };
    }
    if (previousOverflowRef.current !== null) {
      document.body.style.overflow = previousOverflowRef.current;
      previousOverflowRef.current = null;
    }
    return undefined;
  }, [overlayOpen]);

  useEffect(() => {
    const wasOpen = drawerWasOpenRef.current;
    if (!drawerOpen) {
      if (wasOpen && focusMenuAfterDrawerCloseRef.current && !searchOpen && !settingsOpen) {
        menuButtonRef.current?.focus();
      }
      drawerWasOpenRef.current = false;
      focusMenuAfterDrawerCloseRef.current = false;
      return;
    }
    drawerWasOpenRef.current = true;
    drawerCloseRef.current?.focus();
  }, [drawerOpen, searchOpen, settingsOpen]);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDrawer();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusableElements(drawerRef.current);
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [closeDrawer, drawerOpen]);

  return (
    <>
      <Sidebar
        collapsed={collapsed}
        auth={auth}
        onToggleCollapsed={toggleCollapsed}
        onSearch={openSearch}
        onOpenSettings={openSettings}
      />
      <MobileTopbar
        menuOpen={drawerOpen}
        menuButtonRef={menuButtonRef}
        profile={auth.profile}
        onMenu={toggleDrawer}
        onOpenSettings={openSettings}
      />

      {drawerOpen ? (
        <>
          <button type="button" className="fixed inset-0 z-[60] bg-black/60 sm:hidden" aria-label="Close navigation" onClick={closeDrawer} />
          <div
            ref={drawerRef}
            id="mobile-sidebar-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            className="fixed inset-y-0 left-0 z-[61] flex w-64 max-w-[85vw] flex-col border-r border-gray-600 bg-gray-800 shadow-2xl sm:hidden"
          >
            <div className="flex h-14 items-center justify-between border-b border-gray-700 px-3">
              <span className="text-sm font-semibold text-gray-100">OpenPortfo</span>
              <button ref={drawerCloseRef} type="button" className="rounded-md p-2 text-gray-400 hover:bg-gray-700 hover:text-gray-100" aria-label="Close navigation" onClick={closeDrawer}>×</button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-4">
              <SidebarNav collapsed={false} onSearch={openSearch} onNavigate={closeDrawer} />
            </div>
            <div className="border-t border-gray-700 px-3 py-3">
              <SidebarUserChip collapsed={false} auth={auth} onOpenSettings={openSettings} />
            </div>
          </div>
        </>
      ) : null}

      <div className={`min-h-screen transition-[padding] duration-200 ${collapsed ? "sm:pl-16" : "sm:pl-60"}`}>
        <main className="container min-h-screen py-10 text-gray-400">{children}</main>
      </div>

      <SearchDialog
        open={searchOpen}
        returnFocusRef={searchReturnFocusRef}
        restoreFocusOnClose={restoreSearchFocus}
        onClose={closeSearch}
      />
      <UserSettingsModal
        open={settingsOpen}
        auth={auth}
        returnFocusRef={settingsReturnFocusRef}
        restoreFocusOnClose={restoreSettingsFocus}
        onClose={closeSettings}
      />
      <ChatWidget leftInset={desktop ? (collapsed ? 64 : 240) : 0} />
    </>
  );
}
