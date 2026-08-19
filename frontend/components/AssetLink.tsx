"use client";

import Link from "next/link";
import type { CSSProperties, MouseEventHandler, ReactNode } from "react";
import { assetDetailHref, type AssetKind } from "@/lib/asset";
import { cn } from "@/lib/utils";

/** Shared click-through to `/crypto/[id]` or `/stock/[id]`. */
export default function AssetLink({
  assetType,
  id,
  className,
  children,
  onClick,
  onMouseEnter,
  onMouseLeave,
  title,
  style,
}: {
  assetType: AssetKind | string;
  /** Symbol or provider slug (e.g. BTC / bitcoin / VNM). */
  id: string;
  className?: string;
  children: ReactNode;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
  onMouseEnter?: MouseEventHandler<HTMLAnchorElement>;
  onMouseLeave?: MouseEventHandler<HTMLAnchorElement>;
  title?: string;
  style?: CSSProperties;
}) {
  const href = assetDetailHref(assetType, id);
  return (
    <Link
      href={href}
      className={cn("transition-colors hover:text-teal-400", className)}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      title={title}
      style={style}
    >
      {children}
    </Link>
  );
}
