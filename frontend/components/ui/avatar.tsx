"use client";

import * as React from "react";
import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cn } from "@/lib/utils";

function Avatar({ className, ...props }: React.ComponentProps<typeof AvatarPrimitive.Root>) {
  return (
    <AvatarPrimitive.Root
      data-slot="avatar"
      className={cn("relative flex size-8 shrink-0 overflow-hidden rounded-full", className)}
      {...props}
    />
  );
}

/** A plain img keeps DiceBear usable under static export and makes load-error
 * fallback deterministic in jsdom as well as in the browser. */
function AvatarImage({ className, ...props }: React.ComponentProps<"img">) {
  // DiceBear is an external static-export asset; next/image is intentionally
  // not used here (see the sprint architecture handoff).
  // eslint-disable-next-line @next/next/no-img-element
  return <img data-slot="avatar-image" className={cn("aspect-square size-full", className)} {...props} alt={props.alt ?? ""} />;
}

function AvatarFallback({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="avatar-fallback"
      className={cn("flex size-full items-center justify-center rounded-full bg-muted", className)}
      {...props}
    />
  );
}

export { Avatar, AvatarImage, AvatarFallback };
