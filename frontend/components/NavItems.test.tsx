import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import NavItems from "@/components/NavItems";

const pathname = vi.fn(() => "/");

vi.mock("next/navigation", () => ({
  usePathname: () => pathname(),
}));

vi.mock("next/link", () => ({
  default({
    href,
    children,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  },
}));

function openMarketFlyout() {
  const market = screen.getByRole("link", { name: "Market" });
  const host = market.closest("li");
  expect(host).not.toBeNull();
  fireEvent.pointerEnter(host!);
  return host!;
}

describe("NavItems", () => {
  beforeEach(() => {
    pathname.mockReturnValue("/");
  });

  afterEach(() => {
    cleanup();
  });

  it("renders a Market item instead of Dashboard or a Markets stub", () => {
    render(<NavItems />);

    expect(screen.getByRole("link", { name: "Market" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Markets" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });

  it("reveals Stock and Crypto destinations on hover", () => {
    render(<NavItems />);

    openMarketFlyout();

    expect(screen.getByRole("link", { name: "Stock" })).toHaveAttribute("href", "/markets/stock");
    expect(screen.getByRole("link", { name: "Crypto" })).toHaveAttribute("href", "/markets/crypto");
  });

  it("marks Market active on the stock path", () => {
    pathname.mockReturnValue("/markets/stock");
    render(<NavItems />);

    expect(screen.getByRole("link", { name: "Market" })).toHaveClass("text-gray-100");
  });

  it("marks Market active on the crypto path", () => {
    pathname.mockReturnValue("/markets/crypto");
    render(<NavItems />);

    expect(screen.getByRole("link", { name: "Market" })).toHaveClass("text-gray-100");
  });
});
