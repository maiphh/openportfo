"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { NAV_ITEMS } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const MARKET_ACTIVE = new Set(["/", "/markets", "/markets/stock", "/markets/crypto"]);

function normalizePath(pathname: string) {
  if (!pathname || pathname === "/") return "/";
  return pathname.replace(/\/+$/, "") || "/";
}

export default function NavItems({
  onSearch,
  className,
}: {
  onSearch?: () => void;
  className?: string;
}) {
  const pathname = normalizePath(usePathname() ?? "/");
  const [marketOpen, setMarketOpen] = useState(false);

  return (
    <ul className={cn("flex flex-col gap-3 p-2 font-medium sm:flex-row sm:gap-10", className)}>
      {NAV_ITEMS.map((item) => {
        if (item.href === "/search") {
          return (
            <li key={item.href}>
              <button type="button" onClick={onSearch} className="search-text">
                {item.label}
              </button>
            </li>
          );
        }

        const children = "children" in item ? item.children : undefined;
        if (!children) return null;

        const active = MARKET_ACTIVE.has(pathname);
        return (
          <li
            key={item.href}
            className="group relative"
            onPointerEnter={() => setMarketOpen(true)}
            onPointerLeave={() => setMarketOpen(false)}
          >
            <Link
              href={item.href}
              aria-haspopup="true"
              aria-expanded={marketOpen}
              className={cn("transition-colors hover:text-teal-400", active ? "text-gray-100" : "text-gray-500")}
            >
              {item.label}
            </Link>
            <ul
              className={cn(
                "absolute left-0 top-full z-50 min-w-[9.5rem] overflow-hidden rounded-md border border-gray-600 bg-gray-800 py-1 shadow-lg",
                "invisible opacity-0 transition-opacity",
                "group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100",
                marketOpen && "visible opacity-100",
              )}
            >
              {children.map((child) => {
                const childActive = pathname === normalizePath(child.href);
                return (
                  <li key={child.href}>
                    <Link
                      href={child.href}
                      className={cn(
                        "block px-3 py-2 text-sm transition-colors hover:bg-gray-700 hover:text-teal-400",
                        childActive ? "text-gray-100" : "text-gray-500",
                      )}
                    >
                      {child.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </li>
        );
      })}
    </ul>
  );
}
