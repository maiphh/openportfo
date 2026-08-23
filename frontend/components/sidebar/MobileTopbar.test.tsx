import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MobileTopbar from "@/components/sidebar/MobileTopbar";

describe("MobileTopbar", () => {
  afterEach(cleanup);

  it("exposes the hamburger contract and routes avatar activation to settings", () => {
    const onMenu = vi.fn();
    const onSettings = vi.fn();
    render(
      <MobileTopbar
        menuOpen={false}
        profile={{ userId: "sub-1", email: "ada@example.com", name: "Ada" }}
        onMenu={onMenu}
        onOpenSettings={onSettings}
      />,
    );
    const menu = screen.getByRole("button", { name: "Open navigation menu" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(menu).toHaveAttribute("aria-controls", "mobile-sidebar-drawer");
    fireEvent.click(menu);
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(onMenu).toHaveBeenCalledTimes(1);
    expect(onSettings).toHaveBeenCalledTimes(1);
  });
});
