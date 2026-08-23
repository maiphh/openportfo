import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SidebarNav from "@/components/sidebar/SidebarNav";

const pathname = vi.fn(() => "/");

vi.mock("next/navigation", () => ({ usePathname: () => pathname() }));
vi.mock("next/link", () => ({
  default({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
    return <a href={href} {...props}>{children}</a>;
  },
}));

describe("SidebarNav", () => {
  beforeEach(() => pathname.mockReturnValue("/"));
  afterEach(cleanup);

  it("renders translated market, portfolio, watchlist, and search controls", () => {
    const onSearch = vi.fn();
    render(<SidebarNav collapsed={false} onSearch={onSearch} />);
    expect(screen.getByRole("button", { name: "Market" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Portfolio" })).toHaveAttribute("href", "/portfolio");
    expect(screen.getByRole("link", { name: "Watchlist" })).toHaveAttribute("href", "/watchlist");
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(onSearch).toHaveBeenCalledTimes(1);
  });

  it("expands and collapses the market group", () => {
    render(<SidebarNav collapsed={false} onSearch={vi.fn()} />);
    const market = screen.getByRole("button", { name: "Market" });
    expect(market).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Stock" })).toBeInTheDocument();
    fireEvent.click(market);
    expect(market).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link", { name: "Stock" })).not.toBeInTheDocument();
  });

  it("flattens market links and retains labels in the icon rail", () => {
    render(<SidebarNav collapsed onSearch={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Market" })).not.toBeInTheDocument();
    const stock = screen.getByRole("link", { name: "Stock" });
    expect(stock).toHaveAttribute("title", "Stock");
    expect(screen.getByRole("link", { name: "Crypto" })).toHaveAttribute("title", "Crypto");
    expect(screen.getByRole("link", { name: "Portfolio" })).toHaveAttribute("title", "Portfolio");
  });

  it("marks portfolio active from the current pathname", () => {
    pathname.mockReturnValue("/portfolio/");
    render(<SidebarNav collapsed={false} onSearch={vi.fn()} />);
    expect(screen.getByRole("link", { name: "Portfolio" })).toHaveClass("text-gray-100");
  });
});

