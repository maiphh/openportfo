import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Sidebar from "@/components/sidebar/Sidebar";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));
vi.mock("next/link", () => ({
  default({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
    return <a href={href} {...props}>{children}</a>;
  },
}));

const auth = {
  hydrated: true,
  token: null,
  profile: null,
  loading: false,
  error: null,
  cognitoConfigured: false,
  refresh: vi.fn(),
  reloadProfile: vi.fn(async () => null),
  replaceProfile: vi.fn(),
  signIn: vi.fn(async () => undefined),
  signOut: vi.fn(),
};

describe("Sidebar", () => {
  afterEach(cleanup);

  it("renders the expanded brand/nav and exposes the controlled toggle", () => {
    const onToggle = vi.fn();
    render(<Sidebar collapsed={false} auth={auth} onToggleCollapsed={onToggle} onSearch={vi.fn()} onOpenSettings={vi.fn()} />);
    expect(screen.getByText("OpenPortfo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Collapse sidebar" })).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("renders an icon rail with accessible settings/avatar control", () => {
    const onSettings = vi.fn();
    render(<Sidebar collapsed auth={auth} onToggleCollapsed={vi.fn()} onSearch={vi.fn()} onOpenSettings={onSettings} />);
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(onSettings).toHaveBeenCalledTimes(1);
  });
});
